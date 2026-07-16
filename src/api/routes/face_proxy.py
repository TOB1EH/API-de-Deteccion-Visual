import json
import logging
import base64
import os
from uuid import uuid4
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor


def _embedding_to_str(embedding: list[float]) -> str:
    return "[" + ",".join(str(v) for v in embedding) + "]"

from ..schemas.face import (
    FaceEmbedRequest, FaceEmbedResponse,
    FaceRecognizeRequest, FaceRecognizeResponse,
    FaceEmbedUploadRequest, FaceEmbedUploadResponse,
)
from ..services.db_service import db_service
from ..services.seaweedfs_client import seaweedfs_client
from ..services.db_service import DatabaseService
from ..services.auth import require_role
from ..services.image_utils import validate_image, get_format_and_mime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["faces"],
    responses={404: {"description": "Not found"}},
)


@router.post("/persons/{person_id}/face-embed", response_model=FaceEmbedUploadResponse, status_code=201,
             dependencies=[Depends(require_role(["admin"]))])
async def create_face_embedding_orchestrated(person_id: str, request: FaceEmbedUploadRequest):
    """
    Orquestador de embedding facial: recibe la imagen, la envia al inference-server
    (DeepFace) para calcular el embedding, y persiste el resultado en BD + SeaweedFS.
    NOTA: El inference-server intenta persistir internamente pero necesita autenticacion.
    Por ahora el flujo completo solo funciona via CLI (setup_cliente.py faces embed).
    """
    inference_url = os.getenv("INFERENCE_SERVER_URL", "http://localhost:8001")
    image_bytes = base64.b64decode(request.image_base64.split(",")[-1])

    # Validar que sea una imagen valida antes de enviar a DeepFace
    if not validate_image(image_bytes):
        raise HTTPException(
            status_code=400,
            detail="La imagen enviada no es un archivo de imagen valido (JPEG, PNG, WebP, BMP, GIF)."
        )

    # Detectar formato real para declarar Content-Type correcto al inference-server
    _, mime_type = get_format_and_mime(image_bytes)

    import requests as http_requests
    import io

    # Verificar persona
    conn = db_service.get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT person_id::TEXT, name FROM persons WHERE person_id = %s",
            (person_id,),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Persona {person_id} no encontrada")
        cursor.close()
    finally:
        conn.close()

    # Enviar al inference-server
    resp = http_requests.post(
        f"{inference_url}/face/embed",
        data={"person_id": person_id},
        files={"image": ("face." + mime_type.split("/")[-1], io.BytesIO(image_bytes), mime_type)},
        timeout=120
    )

    try:
        result = resp.json()
    except Exception:
        result = {}

    # Si el inference-server rechazo la imagen (sin rostro detectable)
    if result.get("error") or resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="No se detecto un rostro en la imagen o hubo un error en DeepFace. "
                   "Usa el CLI: `python3 client/setup_cliente.py faces embed ...`"
        )

    # Subir imagen a SeaweedFS como respaldo
    image_url = seaweedfs_client.upload_image(
        request.image_base64, f"face_{person_id}_{uuid4()}", mime_type=mime_type
    )

    return FaceEmbedUploadResponse(
        person_id=person_id,
        valid_embeddings=1 if image_url else 0,
        embedding_id="",
        image_url=image_url or "",
    )


@router.post("/persons/{person_id}/embeddings", response_model=FaceEmbedResponse, status_code=201,
             dependencies=[Depends(require_role(["admin"]))])
async def create_face_embedding(person_id: str, request: FaceEmbedRequest):
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            "SELECT person_id::TEXT, name FROM persons WHERE person_id = %s",
            (person_id,),
        )
        person = cursor.fetchone()
        if not person:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Persona {person_id} no encontrada")

        image_b64 = request.image_base64
        raw_bytes = base64.b64decode(image_b64.split(",")[-1])
        if not validate_image(raw_bytes):
            raise HTTPException(
                status_code=400,
                detail="La imagen enviada no es un archivo de imagen valido (JPEG, PNG, WebP, BMP, GIF)."
            )
        _, img_mime = get_format_and_mime(raw_bytes)
        image_url = seaweedfs_client.upload_image(
            image_b64, f"face_{person_id}_{uuid4()}", mime_type=img_mime
        )

        embedding_id = str(uuid4())
        cursor.execute(
            """
            INSERT INTO face_embeddings (embedding_id, person_id, embedding, confidence, image_url)
            VALUES (%s, %s, %s::vector, %s, %s)
            """,
            (embedding_id, person_id, _embedding_to_str(request.embedding), request.confidence, image_url or ""),
        )
        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Embedding %s persistido para persona %s", embedding_id, person_id)
        return FaceEmbedResponse(
            person_id=person_id,
            processed_images=1,
            valid_embeddings=1,
            rejected_images=0,
            embedding_id=embedding_id,
            image_url=image_url or "",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando embedding facial")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/face-recognition", response_model=FaceRecognizeResponse,
             dependencies=[Depends(require_role(["admin"]))])
async def recognize_face(request: FaceRecognizeRequest):
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT fe.embedding_id::TEXT,
                   p.person_id::TEXT,
                   p.name,
                   fe.confidence,
                   fe.embedding <=> %s::vector AS distance
            FROM face_embeddings fe
            JOIN persons p ON p.person_id = fe.person_id
            WHERE fe.embedding <=> %s::vector < %s
            ORDER BY distance ASC
            LIMIT 1
            """,
            (_embedding_to_str(request.embedding), _embedding_to_str(request.embedding), 2.0 - request.threshold),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return FaceRecognizeResponse()

        distance = row["distance"]
        conf = max(0.0, 1.0 - distance)
        if conf < request.threshold:
            return FaceRecognizeResponse()

        name_parts = DatabaseService._name_to_parts(row["name"])
        return FaceRecognizeResponse(
            person_id=row["person_id"],
            nombre=name_parts["nombre"],
            apellido=name_parts["apellido"],
            confidence=round(conf, 4),
        )

    except Exception as e:
        logger.exception("Error en reconocimiento facial")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
