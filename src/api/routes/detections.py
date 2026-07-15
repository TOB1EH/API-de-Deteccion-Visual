"""
Rutas para la gestión de detecciones.

Incluye la funcion _run_inference() que permite a la API actuar como
orquestador: si el cliente no envia detecciones pre-calculadas, la API
las solicita internamente al inference-server.
"""

import os
import json
import base64
import io
import logging
import requests
from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime, timezone
from ..schemas.detection import DetectionRequest, DetectionResponse, BboxSchema, SingleDetectionRequest
from ..services.db_service import db_service
from ..services.seaweedfs_client import seaweedfs_client
from ..services.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/detections",
    tags=["detections"],
    responses={404: {"description": "Not found"}},
)

# ==============================================================================
# FUNCION AUXILIAR: Llamar al inference-server para calcular detecciones
# ==============================================================================

def _run_inference(image_base64: str, model_id: str, confidence: float) -> list:
    """
    Envia la imagen al inference-server (YOLO) y devuelve las detecciones
    en el formato esperado por el resto del flujo (SingleDetectionRequest).

    La URL del inference-server se configura via variable de entorno
    INFERENCE_SERVER_URL (default: http://localhost:8001).

    Args:
        image_base64: Imagen en base64
        model_id: Nombre del modelo YOLO (ej: "yolo11n.pt")
        confidence: Umbral de confianza (0.0 - 1.0)

    Returns:
        List[dict]: Lista de detecciones compatibles con SingleDetectionRequest

    Raises:
        HTTPException: Si no se puede conectar o el inference-server devuelve error
    """
    inference_url = os.getenv("INFERENCE_SERVER_URL", "http://localhost:8001")

    # Decodificar base64 a bytes
    image_bytes = base64.b64decode(image_base64.split(",")[-1])

    # Enviar al inference-server via requests (multipart automático)
    try:
        resp = requests.post(
            f"{inference_url}/infer",
            files={"image": ("image.jpg", io.BytesIO(image_bytes), "image/jpeg")},
            data={"model_name": model_id, "confidence": confidence},
            timeout=120
        )
        resp.raise_for_status()
        infer_result = resp.json()
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail=f"No se puede conectar al inference server en {inference_url}: {e}"
        )
    except requests.exceptions.HTTPError as e:
        error_body = e.response.text if e.response is not None else str(e)
        raise HTTPException(
            status_code=502,
            detail=f"Inference server error ({e.response.status_code}): {error_body}"
        )

    if infer_result["info"]["error"]:
        raise HTTPException(
            status_code=502,
            detail=f"Error en inferencia: {infer_result['info']['errormsg']}"
        )

    # Transformar al formato esperado por el resto del flujo
    detections = []
    for d in infer_result["results"]:
        detections.append({
            "class_name": d["classname"],
            "class_id": d["classnumber"],
            "confidence": round(d["conf"] / 100.0, 4),
            "bbox": {
                "x_min": int(d["bbox_object"]["x_min"]),
                "y_min": int(d["bbox_object"]["y_min"]),
                "x_max": int(d["bbox_object"]["x_max"]),
                "y_max": int(d["bbox_object"]["y_max"]),
            }
        })

    logger.info("Inferencia completada: %d objeto(s) detectado(s)", len(detections))
    return detections


@router.post("", response_model=DetectionResponse,
             dependencies=[Depends(require_role(["admin", "operator"]))])
async def process_detections(request: DetectionRequest):
    """
    Procesa detecciones recibidas desde el cliente.

    POST /api/detections

    Flujo:
    1. Recibe imagen base64 + detecciones del cliente
    2. Sube imagen a SeaweedFS
    3. Guarda metadatos en PostgreSQL (frames)
    4. Guarda detecciones en PostgreSQL (detections)
    5. Retorna frame_id

    Args:
        request: DetectionRequest (validado por Pydantic)

    Retorna:
        DetectionResponse con frame_id, image_url, etc.
    """
    try:
        # Generar IDs únicos
        frame_id = str(uuid4())
        # timestamp en formato ISO 8601 UTC (ej: 2024-06-01T12:00:00Z)
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # ===== PASO 0 (opcional): Ejecutar inferencia si no vienen detecciones pre-calculadas =====
        if not request.detections:
            logger.info("[%s] Sin detecciones pre-calculadas. Ejecutando inferencia via inference-server...", frame_id)
            inferred_detections = _run_inference(
                image_base64=request.image_base64,
                model_id=request.model_id,
                confidence=request.confidence or 0.25
            )
            # Reemplazar request.detections con las detecciones inferidas
            request.detections = [
                SingleDetectionRequest(**det) for det in inferred_detections
            ]
            logger.info("[%s] Inferencia completada: %d deteccion(es)", frame_id, len(request.detections))

        # ===== PASO 1: Subir imagen a SeaweedFS =====
        logger.info("[%s] Subiendo imagen a SeaweedFS...", frame_id)
        image_url = seaweedfs_client.upload_image(request.image_base64, frame_id)

        if not image_url:
            raise ValueError("No se pudo subir la imagen a SeaweedFS")

        logger.info("[%s] Imagen guardada en: %s", frame_id, image_url)

        # ===== PASO 2: Guardar frame en PostgreSQL =====
        logger.info("[%s] Guardando frame en PostgreSQL...", frame_id)
        frame_saved = db_service.save_frame(
            frame_id=frame_id,
            model_id=request.model_id,
            latitude=request.latitude,
            longitude=request.longitude,
            image_url=image_url,
            detections_count=len(request.detections),
            camera_id=request.metadata.camera_id if request.metadata else None,
            source=request.metadata.source if request.metadata else None
        )

        if not frame_saved:
            raise ValueError("No se pudo guardar el frame en la BD")

        logger.info("[%s] Frame guardado en BD", frame_id)

        # ===== PASO 3: Guardar detecciones en PostgreSQL =====
        logger.info("[%s] Guardando %d detecciones...", frame_id, len(request.detections))

        # Convertir detecciones a formato de BD
        detections_data = []
        for det in request.detections:
            detections_data.append({
                'class_name': det.class_name,
                'class_id': det.class_id,
                'confidence': det.confidence,
                'bbox': det.bbox.model_dump()  # Convertir Pydantic model a dict
            })

        # Guardar batch, donde batch es una lista de detecciones asociadas al frame_id
        detections_saved = db_service.save_detections_batch(frame_id, detections_data)
        logger.info("[%s] %d detecciones guardadas", frame_id, detections_saved)

        # ===== PASO 4: Retornar respuesta exitosa =====
        return DetectionResponse(
            frame_id=frame_id,
            image_url=image_url,
            detections_count=detections_saved,
            status="processed",
            message=f"Se procesaron {detections_saved} detecciones",
            timestamp=timestamp
        )

    except Exception as e:
        logger.exception("Error en process_detections")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando detecciones: {str(e)}"
        )

@router.get("/{frame_id}")
async def get_detections(frame_id: str):
    """
    Obtiene las detecciones de un frame específico.

    GET /api/detections/{frame_id}

    Args:
        frame_id: ID único del frame

    Retorna:
        Lista de detecciones del frame
    """
    try:
        # Obtener detecciones desde la BD usando el frame_id
        detections = db_service.get_frame_detections(frame_id)
        if not detections:
            raise HTTPException(
                status_code=404,
                detail=f"Frame {frame_id} no encontrado"
            )

        # Retornar detecciones
        return {
            "frame_id": frame_id,
            "detections_count": len(detections),
            "detections": detections
        }

    except Exception as e:
        logger.exception("Error obteniendo detecciones")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )
