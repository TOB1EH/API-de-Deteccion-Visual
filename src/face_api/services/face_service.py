"""
Servicio de DeepFace: detección facial, generación de embeddings y comparación.
"""

import logging
import os
import requests
import numpy as np
from deepface import DeepFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaceService:

    def __init__(self):
        self.backend = os.getenv("DEEPFACE_BACKEND", "Facenet")
        self.seaweed_url = os.getenv("SEAWEED_URL", "http://seaweed-volume:8080")
        self._ensure_models()
        self._model_downloaded = False

    def _ensure_models(self):
        logger.info("Verificando modelos DeepFace (%s)...", self.backend)

    def generate_embedding(self, image_url: str) -> dict:
        image_path = self._download_image(image_url)
        if not image_path:
            return {"error": "No se pudo descargar la imagen"}

        try:
            result = DeepFace.represent(
                img_path=image_path,
                model_name=self.backend,
                enforce_detection=False,
                detector_backend="opencv",
                normalization="base"
            )

            self._model_downloaded = True

            if isinstance(result, list) and len(result) > 0:
                item = result[0]
                if isinstance(item, dict):
                    embedding = item.get("embedding", [])
                    raw_confidence = item.get("face_confidence", 1.0)
                    facial_area = item.get("facial_area", {})
                elif isinstance(item, list):
                    embedding = item
                    raw_confidence = 1.0
                    facial_area = {}
                else:
                    return {"error": "Formato de resultado inesperado"}

                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                if not isinstance(embedding, list) or len(embedding) == 0:
                    return {"error": "Embedding vacío o inválido"}

                confidence = min(float(raw_confidence), 1.0)
                return {"embedding": embedding, "confidence": confidence, "faces_detected": len(result), "facial_area": facial_area}
            elif isinstance(result, dict):
                embedding = result.get("embedding", [])
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                raw_confidence = result.get("face_confidence", 1.0)
                confidence = min(float(raw_confidence), 1.0)
                return {"embedding": embedding, "confidence": confidence, "faces_detected": 1}
            else:
                return {"error": "No se detectaron rostros en la imagen"}
        except Exception as e:
            logger.error("Error generando embedding: %s", e)
            return {"error": f"Error generando embedding: {str(e)}"}
        finally:
            self._cleanup(image_path)

    def compare_embeddings(self, embedding1: list[float], embedding2: list[float]) -> float:
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 1.0
        cosine_sim = np.dot(v1, v2) / (norm1 * norm2)
        return float(1.0 - cosine_sim)

    def _download_image(self, url: str) -> str:
        temp_dir = "/tmp/face_api"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, "query_image.jpg")
        try:
            fid = url.split("/seaweed/")[-1]
            internal_url = f"{self.seaweed_url}/{fid}"
            response = requests.get(internal_url, timeout=30)
            response.raise_for_status()
            with open(temp_path, "wb") as f:
                f.write(response.content)
            return temp_path
        except Exception as e:
            logger.error("Error descargando imagen: %s", e)
            return ""

    def _cleanup(self, path: str):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


face_service = FaceService()
