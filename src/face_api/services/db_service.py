"""
Servicio de base de datos para face-api.
Operaciones sobre persons y face_embeddings en PostgreSQL.
"""

import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Any
import os
from uuid import uuid4

logger = logging.getLogger(__name__)


class FaceDatabaseService:

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://detections_user:secure_pwd_local@localhost:5432/detections_db"
        )

    def get_connection(self):
        try:
            conn = psycopg2.connect(self.db_url)
            return conn
        except Exception as e:
            logger.error("Error al conectar a la base de datos: %s", e)
            raise

    def get_person(self, person_id: str) -> Optional[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT person_id::TEXT, name FROM persons WHERE person_id = %s",
                (person_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error("Error obteniendo persona: %s", e)
            return None

    def save_embedding(self, person_id: str, embedding: list[float],
                       confidence: float, image_url: str) -> Optional[str]:
        try:
            embedding_id = str(uuid4())
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO face_embeddings (embedding_id, person_id, embedding, confidence, image_url)
                VALUES (%s, %s, %s::vector, %s, %s)
                """,
                (embedding_id, person_id, embedding, confidence, image_url)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return embedding_id
        except Exception as e:
            logger.error("Error guardando embedding: %s", e)
            return None

    def search_similar(self, embedding: list[float], threshold: float,
                       limit: int = 5) -> list[dict]:
        try:
            conn = self.get_connection()
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
                ORDER BY distance ASC
                LIMIT %s
                """,
                (embedding, limit)
            )
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            logger.info("Busqueda facial: %d resultados (threshold=%.2f)", len(results), threshold)
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("Error en búsqueda facial: %s", e)
            return []

    def get_all_embeddings(self) -> list[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT fe.embedding_id::TEXT,
                       p.person_id::TEXT,
                       p.name,
                       fe.embedding::TEXT,
                       fe.confidence,
                       fe.image_url
                FROM face_embeddings fe
                JOIN persons p ON p.person_id = fe.person_id
                ORDER BY p.name ASC
                """
            )
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("Error obteniendo embeddings: %s", e)
            return []


face_db = FaceDatabaseService()
