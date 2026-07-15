"""
Servicio para manejar la conexión con PostgreSQL. Capa intermedia entre
las rutas y la base de datos, es decir, abstrae la lógica de la BD de las rutas
"""

import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional
import os
from uuid import uuid4

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Servicio para interactuar con la base de datos PostgreSQL.
    """

    def __init__(self):
        """
        Inicializa conexión a BD
        """
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://detections_user:bfts2026.@localhost:5432/detections_db"
        )

    def get_connection(self):
        """
        Retorna una conexión a PostgreSQL
        """
        try:
            conn = psycopg2.connect(self.db_url)
            return conn
        except Exception as e:
            logger.error("Error al conectar a la base de datos: %s", e)
            raise

    def save_frame(self, frame_id: str, model_id: str, latitude: float,
                   longitude: float, image_url: str, detections_count: int,
                   camera_id: Optional[str] = None, source: Optional[str] = None) -> bool:
        """
        Guarda un frame en la tabla frames de la base de datos

        Args:
            frame_id (str): ID unico del fotograma procesado
            model_id (str): ID del modelo utilizado para la detección
            latitude (float): Latitud de la ubicación donde se tomó la imagen
            longitude (float): Longitud de la ubicación donde se tomó la imagen
            image_url (str): URL publica para descargar la imagen procesada
            detections_count (int): Número total de detecciones procesadas
            camera_id (Optional[str]): ID de la cámara que capturó la imagen
            source (Optional[str]): Fuente de la imagen

        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = """
            INSERT INTO frames (
                frame_id,
                model_id,
                latitude,
                longitude,
                image_url,
                detections_count,
                camera_id,
                source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                frame_id,
                model_id,
                latitude,
                longitude,
                image_url,
                detections_count,
                camera_id,
                source
            )) # Ejecutar la consulta con los parámetros

            # Confirmar la transacción y cerrar la conexión
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error al guardar el frame en la base de datos: %s", e)
            return False

    def save_detection(self, detection_id: str, frame_id: str, class_name: str, class_id: int,
                       confidence: float, bbox_x_min: int, bbox_y_min: int, bbox_x_max: int,
                       bbox_y_max: int) -> bool:
        """
        Guarda una detección individual en la tabla detections de la base de datos

        Args:
            detection_id (str): ID unico de la detección
            frame_id (str): ID del fotograma al que pertenece la detección
            class_name (str): Nombre de la clase detectada
            class_id (int): ID de la clase detectada
            confidence (float): Confianza de la detección (0.0 - 1.0)
            bbox_x_min (int): Coordenada x mínima del bounding box
            bbox_y_min (int): Coordenada y mínima del bounding box
            bbox_x_max (int): Coordenada x máxima del bounding box
            bbox_y_max (int): Coordenada y máxima del bounding box

        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        try:
            conn = self.get_connection() # Obtener conexión a la base de datos
            cursor = conn.cursor() # Crear un cursor para ejecutar consultas

            query = """
            INSERT INTO detections (
                detection_id,
                frame_id,
                class_name,
                class_id,
                confidence,
                bbox_x_min,
                bbox_y_min,
                bbox_x_max,
                bbox_y_max,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            cursor.execute(query, (
                detection_id, frame_id, class_name, class_id, confidence,
                bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max
            ))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error("Error guardando detección: %s", e)
            return False

    def save_detections_batch(self, frame_id: str, detections_data: List[Dict]) -> int:
        """
        Guarda múltiples detecciones en batch (lote) para un frame.

        Args:
            frame_id (str): ID del frame al que pertenecen las detecciones
            detections_data (List[Dict]): Lista de diccionarios con datos de detecciones
                Cada elemento debe tener: class_name, class_id, confidence, bbox

        Returns:
            int: Número de detecciones guardadas exitosamente
        """
        saved_count = 0
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            for detection in detections_data:
                try:
                    detection_id = str(uuid4())
                    bbox = detection['bbox']

                    query = """
                    INSERT INTO detections (
                        detection_id,
                        frame_id,
                        class_name,
                        class_id,
                        confidence,
                        bbox_x_min,
                        bbox_y_min,
                        bbox_x_max,
                        bbox_y_max,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """

                    cursor.execute(query, (
                        detection_id,
                        frame_id,
                        detection['class_name'],
                        detection['class_id'],
                        detection['confidence'],
                        bbox['x_min'],
                        bbox['y_min'],
                        bbox['x_max'],
                        bbox['y_max']
                    ))

                    saved_count += 1

                except Exception as e:
                    logger.error("Error guardando detección individual: %s", e)
                    continue

            conn.commit()
            cursor.close()
            conn.close()

            return saved_count

        except Exception as e:
            logger.error("Error en save_detections_batch: %s", e)
            return saved_count

    def get_frames_by_location(self, latitude: float, longitude: float,
                               radius_km: float = 1.0) -> List[Dict]:
        """
        Busca frames dentro de un radio geográfico

        Args:
            latitude, longitude: Centro de búsqueda
            radius_km: Radio en km

        Returns:
            Lista de frames encontrados
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Usar función de distancia de PostgreSQL
            query = """
            SELECT frame_id, model_id, latitude, longitude, image_url, 
                   detections_count, created_at
            FROM frames
            WHERE earth_distance(
                ll_to_earth(%s, %s),
                ll_to_earth(latitude, longitude)
            ) < %s * 1000
            ORDER BY created_at DESC
            LIMIT 100
            """

            cursor.execute(query, (latitude, longitude, radius_km))
            results = cursor.fetchall()

            cursor.close()
            conn.close()
            return results

        except Exception as e:
            logger.error("Error buscando frames: %s", e)
            return []

    def get_frame_by_id(self, frame_id: str) -> Optional[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            query = "SELECT * FROM frames WHERE frame_id = %s"
            cursor.execute(query, (frame_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return dict(result) if result else None
        except Exception as e:
            logger.error("Error obteniendo frame: %s", e)
            return None

    def search_frames(self, filters: Dict, limit: int = 50, offset: int = 0) -> List[Dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            conditions = []
            params = []

            if "lat_min" in filters and "lat_max" in filters:
                conditions.append("latitude BETWEEN %s AND %s")
                params.extend([filters["lat_min"], filters["lat_max"]])
            if "lon_min" in filters and "lon_max" in filters:
                conditions.append("longitude BETWEEN %s AND %s")
                params.extend([filters["lon_min"], filters["lon_max"]])
            # Case-insensitive: LOWER() en BD y filtro en minusculas para
            # que "Ball", "ball", "BALL" matcheen (ver Tarea 0.4)
            if "classes" in filters:
                lower_classes = [c.lower() for c in filters["classes"]]
                placeholders = ",".join(["%s"] * len(lower_classes))
                conditions.append(f"frame_id IN (SELECT DISTINCT frame_id FROM detections WHERE LOWER(class_name) IN ({placeholders}))")
                params.extend(lower_classes)
            if "camera_id" in filters:
                conditions.append("camera_id = %s")
                params.append(filters["camera_id"])
            if "source" in filters:
                conditions.append("source = %s")
                params.append(filters["source"])

            where = " AND ".join(conditions) if conditions else "TRUE"
            query = f"""
                SELECT frame_id, model_id, latitude, longitude, image_url,
                       detections_count, camera_id, source, created_at
                FROM frames
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("Error buscando frames: %s", e)
            return []

    def count_frames(self, filters: Dict) -> int:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            conditions = []
            params = []

            if "lat_min" in filters and "lat_max" in filters:
                conditions.append("latitude BETWEEN %s AND %s")
                params.extend([filters["lat_min"], filters["lat_max"]])
            if "lon_min" in filters and "lon_max" in filters:
                conditions.append("longitude BETWEEN %s AND %s")
                params.extend([filters["lon_min"], filters["lon_max"]])
            # Case-insensitive: LOWER() en BD y filtro en minusculas para
            # que "Ball", "ball", "BALL" matcheen (ver Tarea 0.4)
            if "classes" in filters:
                lower_classes = [c.lower() for c in filters["classes"]]
                placeholders = ",".join(["%s"] * len(lower_classes))
                conditions.append(f"frame_id IN (SELECT DISTINCT frame_id FROM detections WHERE LOWER(class_name) IN ({placeholders}))")
                params.extend(lower_classes)
            if "camera_id" in filters:
                conditions.append("camera_id = %s")
                params.append(filters["camera_id"])
            if "source" in filters:
                conditions.append("source = %s")
                params.append(filters["source"])

            where = " AND ".join(conditions) if conditions else "TRUE"
            query = f"SELECT COUNT(*) FROM frames WHERE {where}"

            cursor.execute(query, tuple(params))
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return count
        except Exception as e:
            logger.error("Error contando frames: %s", e)
            return 0

    def get_frame_detections(self, frame_id: str) -> List[Dict]:
        """
        Obtiene todas las detecciones de un frame

        Args:
            frame_id: ID del frame

        Returns:
            Lista de detecciones
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
            SELECT detection_id, class_name, class_id, confidence,
                   bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max
            FROM detections
            WHERE frame_id = %s
            ORDER BY confidence DESC
            """

            cursor.execute(query, (frame_id,))
            results = cursor.fetchall()

            cursor.close()
            conn.close()
            return results

        except Exception as e:
            logger.error("Error obteniendo detecciones: %s", e)
            return []

    def update_person(self, person_id: str, name: str, email: str = None,
                      metadata: dict = None) -> bool:
        """
        Actualiza los datos de una persona existente en la base de datos.

        Args:
            person_id: ID de la persona a actualizar
            name: Nombre completo actualizado
            email: Email actualizado
            metadata: Metadatos adicionales actualizados

        Returns:
            True si se actualizo correctamente, False en caso contrario
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
            UPDATE persons
            SET name = %s, email = %s, metadata = %s, updated_at = NOW()
            WHERE person_id = %s
            """
            cursor.execute(query, (name, email,
                                   json.dumps(metadata) if metadata else None,
                                   person_id))
            conn.commit()
            success = cursor.rowcount > 0
            cursor.close()
            conn.close()
            return success
        except Exception as e:
            logger.error("Error actualizando persona: %s", e)
            return False

    def delete_person(self, person_id: str) -> bool:
        """
        Elimina una persona y sus embeddings asociados de la base de datos.

        Primero elimina los embeddings (tabla face_embeddings) para mantener
        la integridad referencial, luego elimina el registro de la persona.

        Args:
            person_id: ID de la persona a eliminar

        Returns:
            True si se elimino correctamente, False en caso contrario
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            # Eliminar primero los embeddings asociados a la persona
            cursor.execute("DELETE FROM face_embeddings WHERE person_id = %s", (person_id,))
            # Luego eliminar la persona
            cursor.execute("DELETE FROM persons WHERE person_id = %s", (person_id,))
            conn.commit()
            success = cursor.rowcount > 0
            cursor.close()
            conn.close()
            return success
        except Exception as e:
            logger.error("Error eliminando persona: %s", e)
            return False

    def create_person(self, person_id: str, name: str, email: str = None,
                      metadata: dict = None,
                      keycloak_user_id: str = None) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = """
            INSERT INTO persons (person_id, name, email, keycloak_user_id, metadata)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (person_id, name, email, keycloak_user_id,
                                   json.dumps(metadata) if metadata else None))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error("Error creando persona: %s", e)
            return False

    @staticmethod
    def _name_to_parts(name: str) -> dict:
        parts = name.strip().split(" ", 1)
        return {"nombre": parts[0], "apellido": parts[1] if len(parts) > 1 else ""}

    def get_person(self, person_id: str) -> Optional[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            query = """
            SELECT p.person_id::TEXT, p.name, p.email, p.keycloak_user_id,
                   p.metadata, p.created_at::TEXT, p.updated_at::TEXT,
                   (SELECT COUNT(*) > 0 FROM face_embeddings fe WHERE fe.person_id = p.person_id) AS has_faces
            FROM persons p
            WHERE p.person_id = %s
            """
            cursor.execute(query, (person_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if not result:
                return None
            d = dict(result)
            name = d.pop("name", "")
            d.update(self._name_to_parts(name))
            return d
        except Exception as e:
            logger.error("Error obteniendo persona: %s", e)
            return None

    def get_person_by_keycloak_id(self, keycloak_user_id: str) -> Optional[dict]:
        """
        Busca una persona por su keycloak_user_id (sub del token JWT).
        Retorna el mismo formato que get_person().
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            query = """
            SELECT p.person_id::TEXT, p.name, p.email, p.keycloak_user_id,
                   p.metadata, p.created_at::TEXT, p.updated_at::TEXT,
                   (SELECT COUNT(*) > 0 FROM face_embeddings fe WHERE fe.person_id = p.person_id) AS has_faces
            FROM persons p
            WHERE p.keycloak_user_id = %s
            LIMIT 1
            """
            cursor.execute(query, (keycloak_user_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if not result:
                return None
            d = dict(result)
            name = d.pop("name", "")
            d.update(self._name_to_parts(name))
            return d
        except Exception as e:
            logger.error("Error obteniendo persona por keycloak_id: %s", e)
            return None

    def list_persons(self) -> list[dict]:
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            query = """
            SELECT p.person_id::TEXT, p.name, p.email, p.keycloak_user_id,
                   p.metadata, p.created_at::TEXT, p.updated_at::TEXT,
                   (SELECT COUNT(*) > 0 FROM face_embeddings fe WHERE fe.person_id = p.person_id) AS has_faces
            FROM persons p
            ORDER BY p.name ASC
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            out = []
            for r in results:
                d = dict(r)
                name = d.pop("name", "")
                d.update(self._name_to_parts(name))
                out.append(d)
            return out
        except Exception as e:
            logger.error("Error listando personas: %s", e)
            return []

# Instancia global (singleton)
db_service = DatabaseService()
