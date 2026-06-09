import json
import logging
import base64
from uuid import uuid4
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor

from ..schemas.face import (
    FaceEmbedRequest, FaceEmbedResponse,
    FaceRecognizeRequest, FaceRecognizeResponse, FaceMatchResult,
)
from ..services.db_service import db_service
from ..services.seaweedfs_client import seaweedfs_client

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/faces",
    tags=["faces"],
    responses={404: {"description": "Not found"}},
)


@router.post("/embeddings", response_model=FaceEmbedResponse, status_code=201)
async def create_face_embedding(request: FaceEmbedRequest):
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            "SELECT person_id::TEXT, name FROM persons WHERE person_id = %s",
            (request.person_id,),
        )
        person = cursor.fetchone()
        if not person:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Persona {request.person_id} no encontrada")

        image_b64 = request.image_base64
        image_url = seaweedfs_client.upload_image(
            image_b64, f"face_{request.person_id}_{uuid4()}"
        )

        embedding_id = str(uuid4())
        cursor.execute(
            """
            INSERT INTO face_embeddings (embedding_id, person_id, embedding, confidence, image_url)
            VALUES (%s, %s, %s::vector, %s, %s)
            """,
            (embedding_id, request.person_id, request.embedding, request.confidence, image_url or ""),
        )
        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Embedding %s persistido para persona %s", embedding_id, request.person_id)
        return FaceEmbedResponse(
            embedding_id=embedding_id,
            person_id=request.person_id,
            name=person["name"],
            confidence=request.confidence,
            image_url=image_url or "",
            status="generated",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando embedding facial")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/recognize", response_model=FaceRecognizeResponse)
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
            LIMIT 5
            """,
            (request.embedding, request.embedding, 2.0 - request.threshold),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        matches = []
        for row in rows:
            distance = row["distance"]
            conf = max(0.0, 1.0 - distance)
            if conf >= request.threshold:
                matches.append(FaceMatchResult(
                    person_id=row["person_id"],
                    name=row["name"],
                    distance=distance,
                    confidence=round(conf, 4),
                ))

        return FaceRecognizeResponse(
            recognized=len(matches) > 0,
            matches=matches,
            threshold=request.threshold,
        )

    except Exception as e:
        logger.exception("Error en reconocimiento facial")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
