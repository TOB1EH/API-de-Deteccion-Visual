"""
Rutas para la gestión de detecciones.
"""

from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from ..schemas.detection import DetectionRequest, DetectionResponse
from ..services.db_service import db_service
from ..services.seaweedfs_client import seaweedfs_client

router = APIRouter(
    prefix="/detections",
    tags=["detections"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=DetectionResponse)
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
        timestamp = datetime.utcnow().isoformat() + "Z"

        # ===== PASO 1: Subir imagen a SeaweedFS =====
        print(f"[{frame_id}] Subiendo imagen a SeaweedFS...")
        image_url = seaweedfs_client.upload_image(request.image_base64, frame_id)

        if not image_url:
            raise ValueError("No se pudo subir la imagen a SeaweedFS")

        print(f"[{frame_id}] Imagen guardada en: {image_url}")

        # ===== PASO 2: Guardar frame en PostgreSQL =====
        print(f"[{frame_id}] Guardando frame en PostgreSQL...")
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

        print(f"[{frame_id}] Frame guardado en BD")

        # ===== PASO 3: Guardar detecciones en PostgreSQL =====
        print(f"[{frame_id}] Guardando {len(request.detections)} detecciones...")

        # Convertir detecciones a formato de BD
        detections_data = []
        for det in request.detections:
            detections_data.append({
                'class_name': det.class_name,
                'class_id': det.class_id,
                'confidence': det.confidence,
                'bbox': det.bbox.model_dump()  # Convertir Pydantic model a dict
            })

        # Guardar batch
        detections_saved = db_service.save_detections_batch(frame_id, detections_data)
        print(f"[{frame_id}] {detections_saved} detecciones guardadas")

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
        print(f"Error en process_detections: {e}")
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
        detections = db_service.get_frame_detections(frame_id)

        if not detections:
            raise HTTPException(
                status_code=404,
                detail=f"Frame {frame_id} no encontrado"
            )

        return {
            "frame_id": frame_id,
            "detections_count": len(detections),
            "detections": detections
        }

    except Exception as e:
        print(f"Error obteniendo detecciones: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )
