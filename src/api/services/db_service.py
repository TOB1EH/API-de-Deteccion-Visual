"""
Servicio para manejar la conexión con PostgreSQL. Capa intermedia entre
las rutas y la base de datos, es decir, abstrae la lógica de la BD de las rutas
"""

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

# Instancia global (singleton)
db_service = DatabaseService()
