"""
Rutas para autenticacion biométrica facial como segundo factor (2FA).

Flujo:
1. Usuario se loguea con Keycloak (password) -> obtiene access_token
2. Frontend verifica si el usuario tiene una persona vinculada con embeddings faciales
   (GET /api/persons/me -> has_faces)
3. Si tiene rostros registrados, frontend muestra pantalla de verificacion facial
4. Usuario se toma una foto, frontend la envia a POST /api/auth/verify-face
5. Backend genera embedding de la foto, lo compara contra los embeddings almacenados
   de la persona vinculada al token. Si la distancia es menor al threshold, verifica.
"""

import os
import json
import base64
import io
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from ..services.db_service import db_service
from ..services.auth import verify_token
from ..schemas.face import FaceEmbedUploadRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


class FaceVerifyRequest(BaseModel):
    image_base64: str = Field(..., description="Imagen facial en base64 (con o sin prefijo data:)")
    threshold: float = Field(0.8, ge=0.0, le=1.0, description="Umbral minimo de confianza (0.0 - 1.0)")


class FaceVerifyResponse(BaseModel):
    verified: bool = Field(..., description="True si el rostro coincide con la persona vinculada al token")
    confidence: float = Field(0.0, description="Confianza de la coincidencia (0.0 - 1.0)")
    person_id: Optional[str] = Field(None, description="ID de la persona verificada")
    nombre: Optional[str] = Field(None, description="Nombre de la persona verificada")
    apellido: Optional[str] = Field(None, description="Apellido de la persona verificada")


@router.post("/verify-face", response_model=FaceVerifyResponse)
async def verify_face(request: FaceVerifyRequest, auth_data: dict = Depends(verify_token)):
    """
    Verifica que la imagen facial pertenece a la persona vinculada al token.

    POST /api/auth/verify-face

    Args:
        request: Imagen facial + threshold de confianza
        auth_data: Token JWT (extrae keycloak_user_id para buscar la persona)

    Retorna:
        FaceVerifyResponse con verified=True/False, confianza y datos de la persona

    Proceso:
        1. Busca la persona vinculada al keycloak_user_id del token
        2. Envia la imagen al inference-server para generar embedding
        3. Compara el embedding generado contra los almacenados de esa persona
        4. Si la distancia es menor al threshold, la verificacion es exitosa
    """
    # 1. Obtener la persona vinculada al token
    keycloak_user_id = auth_data.get("sub")
    if not keycloak_user_id:
        raise HTTPException(status_code=400, detail="Token invalido: sin sub")

    person = db_service.get_person_by_keycloak_id(keycloak_user_id)
    if not person:
        raise HTTPException(
            status_code=404,
            detail="No hay persona vinculada a este usuario. Registrese primero."
        )

    # 2. Verificar que la persona tenga embeddings faciales almacenados
    if not person.get("has_faces", False):
        return FaceVerifyResponse(
            verified=False,
            confidence=0.0,
            person_id=person.get("person_id"),
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )

    # 3. Enviar la imagen al inference-server para generar embedding
    inference_url = os.getenv("INFERENCE_SERVER_URL", "http://localhost:8001")
    image_bytes = base64.b64decode(request.image_base64.split(",")[-1])

    try:
        import requests as http_requests

        resp = http_requests.post(
            f"{inference_url}/face/embed",
            files={"image": ("face.jpg", io.BytesIO(image_bytes), "image/jpeg")},
            timeout=120
        )
        result = resp.json()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo conectar con el inference-server para generar el embedding: {str(e)}"
        )

    if result.get("error") or resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="No se detecto un rostro en la imagen o hubo un error en DeepFace"
        )

    # 4. Comparar el embedding generado contra los almacenados de la persona
    # El inference-server devuelve el embedding en result["embedding"]
    new_embedding = result.get("embedding", result.get("embeddings", [None])[0])
    if not new_embedding:
        raise HTTPException(
            status_code=502,
            detail="El inference-server no devolvio un embedding valido"
        )

    # Buscar el embedding mas cercano usando distancia coseno via pgvector
    person_id = person["person_id"]
    conn = db_service.get_connection()
    try:
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Convertir embedding a formato vector para pgvector
        embedding_str = "[" + ",".join(str(v) for v in new_embedding) + "]"

        cursor.execute(
            """
            SELECT fe.embedding_id::TEXT,
                   fe.embedding <=> %s::vector AS distance
            FROM face_embeddings fe
            WHERE fe.person_id = %s
            ORDER BY distance ASC
            LIMIT 1
            """,
            (embedding_str, person_id),
        )
        row = cursor.fetchone()
        cursor.close()
    finally:
        conn.close()

    if not row:
        # La persona tiene has_faces=true pero no se encontraron embeddings (inconsistencia)
        return FaceVerifyResponse(
            verified=False,
            confidence=0.0,
            person_id=person_id,
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )

    # Calcular confianza: a menor distancia coseno, mayor confianza
    distance = row["distance"]
    confidence = max(0.0, 1.0 - distance)

    if confidence >= request.threshold:
        return FaceVerifyResponse(
            verified=True,
            confidence=round(confidence, 4),
            person_id=person_id,
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )
    else:
        return FaceVerifyResponse(
            verified=False,
            confidence=round(confidence, 4),
            person_id=person_id,
            nombre=person.get("nombre"),
            apellido=person.get("apellido"),
        )
