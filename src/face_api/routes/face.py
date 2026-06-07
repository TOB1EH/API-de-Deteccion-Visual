"""
Rutas para S5.2 (generar embeddings) y S5.3 (reconocimiento facial).
"""

import logging
from fastapi import APIRouter, HTTPException
from uuid import uuid4
from ..schemas.face import (
    EmbeddingRequest, EmbeddingResponse,
    RecognitionRequest, RecognitionResponse, RecognitionMatch
)
from ..services.db_service import face_db
from ..services.face_service import face_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["face-recognition"],
    responses={404: {"description": "Not found"}},
)


@router.post("/persons/{person_id}/embeddings", response_model=EmbeddingResponse)
async def generate_embedding(person_id: str, request: EmbeddingRequest):
    """
    S5.2 - Genera embedding facial para una persona.

    POST /api/persons/{person_id}/embeddings

    Args:
        person_id: ID de la persona existente
        request: EmbeddingRequest con image_url y confidence opcional

    Retorna:
        EmbeddingResponse con embedding_id, confidence, status
    """
    try:
        person = face_db.get_person(person_id)
        if not person:
            raise HTTPException(
                status_code=404,
                detail=f"Persona {person_id} no encontrada"
            )

        result = face_service.generate_embedding(request.image_url)
        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        embedding = result["embedding"]
        confidence = request.confidence or result["confidence"]

        embedding_id = face_db.save_embedding(
            person_id=person_id,
            embedding=embedding,
            confidence=confidence,
            image_url=request.image_url
        )

        if not embedding_id:
            raise HTTPException(
                status_code=500,
                detail="Error al guardar el embedding en la base de datos"
            )

        return EmbeddingResponse(
            person_id=person_id,
            embedding_id=embedding_id,
            confidence=confidence,
            image_url=request.image_url,
            status="generated",
            message=f"Embedding generado exitosamente para {person['name']}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generando embedding")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.post("/face-recognition", response_model=RecognitionResponse)
async def recognize_face(request: RecognitionRequest):
    """
    S5.3 - Reconoce un rostro en una imagen comparando contra embeddings almacenados.

    POST /api/face-recognition

    Args:
        request: RecognitionRequest con image_url y threshold (default 0.8)

    Retorna:
        RecognitionResponse con matches, recognized, threshold
    """
    try:
        result = face_service.generate_embedding(request.image_url)
        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        query_embedding = result["embedding"]

        similar = face_db.search_similar(
            embedding=query_embedding,
            threshold=request.threshold,
            limit=5
        )

        if not similar:
            return RecognitionResponse(
                recognized=False,
                matches=[],
                threshold=request.threshold,
                image_url=request.image_url
            )

        matches = []
        for match in similar:
            distance = match["distance"]
            confidence = max(0.0, 1.0 - distance)
            if confidence >= request.threshold:
                matches.append(RecognitionMatch(
                    person_id=match["person_id"],
                    name=match["name"],
                    distance=distance,
                    confidence=confidence
                ))

        return RecognitionResponse(
            recognized=len(matches) > 0,
            matches=matches,
            threshold=request.threshold,
            image_url=request.image_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error en reconocimiento facial")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
