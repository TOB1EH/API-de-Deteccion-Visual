"""
Cliente para interactuar con el sistema de almacenamiento SeaweedFS. Proporciona
métodos para subir, descargar y eliminar archivos, así como para generar URLs públicas
de acceso a los archivos almacenados.
"""

import logging
import requests
import base64
from typing import Optional
import os
from io import BytesIO
from .image_utils import get_format_and_mime, get_extension

logger = logging.getLogger(__name__)

class SeaweedFSClient:
    """Cliente para interactuar con SeaweedFS"""

    def __init__(self):
        """Inicializa cliente SeaweedFS"""
        # URL de SeaweedFS Volume
        self.seaweed_url = os.getenv("SEAWEED_URL", "http://seaweed-volume:8080")
        self.seaweed_master_url = os.getenv("SEAWEED_MASTER_URL", "http://seaweed-master:9333")
        self.seaweed_public_url = os.getenv(
            "SEAWEED_PUBLIC_URL",
            "https://bfts2026.mooo.com/seaweed"
        )

    def upload_image(self, image_base64: str, frame_id: str, mime_type: Optional[str] = None) -> Optional[str]:
        """
        Sube una imagen (codificada en base64) a SeaweedFS

        Args:
            image_base64: Imagen en base64
            frame_id: ID único para nombrar la imagen
            mime_type: MIME type real de la imagen (ej: image/png, image/webp).
                       Si es None, se detecta automaticamente de los magic bytes.

        Returns:
            URL pública de la imagen, o None si error
        """
        try:
            # Decodificar base64 a bytes
            # Limpiar prefijo data URI si existe (ej: "data:image/jpeg;base64,...")
            if image_base64.startswith("data:"):
                image_base64 = image_base64.split(",", 1)[1]
            image_bytes = base64.b64decode(image_base64)

            # Si no se especifico MIME type, detectar de los magic bytes
            if mime_type is None:
                _, mime_type = get_format_and_mime(image_bytes)

            # Extension de archivo acorde al formato real
            image_format = mime_type.split("/")[-1]
            ext = get_extension(image_format)

            # Preparar request a SeaweedFS
            files = {
                'file': (f"{frame_id}.{ext}", BytesIO(image_bytes), mime_type)
            }

            # Subir a SeaweedFS
            response = requests.post(
                f"{self.seaweed_master_url}/submit",
                files=files,
                timeout=30
            )

            if response.status_code in (200, 201):
                data = response.json()
                # SeaweedFS retorna: {"fid": "5,035e06afbe", "fileName": "...", ...}
                file_id = data.get('fid')

                # Formato estandar: /fid.ext
                public_url = f"{self.seaweed_public_url}/{file_id}.{ext}"
                return public_url
            else:
                logger.error("Error uploading to SeaweedFS: %d - %s", response.status_code, response.text)
                return None

        except Exception as e:
            logger.exception("Error en SeaweedFS upload")
            return None

    def download_image(self, fid: str, file_name: str = "") -> Optional[bytes]:
        """
        Descarga una imagen desde SeaweedFS

        Args:
            fid: File ID de SeaweedFS (ej: "6,0149f1f8e2")
            file_name: Nombre del archivo (opcional)

        Returns:
            Bytes de la imagen, o None si error
        """
        try:
            if file_name:
                url = f"{self.seaweed_url}/{fid}/{file_name}"
            else:
                url = f"{self.seaweed_url}/{fid}"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                return response.content
            else:
                logger.error("Error downloading from SeaweedFS: %d %s", response.status_code, url)
                return None

        except Exception as e:
            logger.exception("Error en SeaweedFS download")
            return None

    def get_public_url(self, fid: str, file_name: str) -> str:
        """Construye URL pública para una imagen"""
        return f"{self.seaweed_public_url}/{fid}/{file_name}"

# Instancia global (singleton)
seaweedfs_client = SeaweedFSClient()
