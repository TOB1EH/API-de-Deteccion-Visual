"""
Cliente para interactuar con el sistema de almacenamiento SeaweedFS. Proporciona
métodos para subir, descargar y eliminar archivos, así como para generar URLs públicas
de acceso a los archivos almacenados.
"""

import requests
import base64
from typing import Optional
import os
from io import BytesIO

class SeaweedFSClient:
    """Cliente para interactuar con SeaweedFS"""

    def __init__(self):
        """Inicializa cliente SeaweedFS"""
        # URL de SeaweedFS Volume
        self.seaweed_url = os.getenv("SEAWEED_URL", "http://seaweed-volume:8080")
        self.seaweed_public_url = os.getenv(
            "SEAWEED_PUBLIC_URL",
            "https://bfts2026.mooo.com/seaweed"
        )

    def upload_image(self, image_base64: str, frame_id: str) -> Optional[str]:
        """
        Sube una imagen (codificada en base64) a SeaweedFS

        Args:
            image_base64: Imagen en base64
            frame_id: ID único para nombrar la imagen

        Returns:
            URL pública de la imagen, o None si error
        """
        try:
            # Decodificar base64 a bytes
            image_bytes = base64.b64decode(image_base64)

            # Preparar request a SeaweedFS
            files = {
                'file': (f"{frame_id}.jpg", BytesIO(image_bytes), 'image/jpeg')
            }

            # Subir a SeaweedFS
            response = requests.post(
                f"{self.seaweed_url}/submit",
                files=files,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                # SeaweedFS retorna: {"name": "550e8400", "fid": "1,abc123"}
                file_id = data.get('fid')
                file_name = data.get('name')

                # Construir URL pública
                public_url = f"{self.seaweed_public_url}/{file_id}/{file_name}"
                return public_url
            else:
                print(f"Error uploading to SeaweedFS: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Error en SeaweedFS upload: {e}")
            return None

    def download_image(self, fid: str, file_name: str) -> Optional[bytes]:
        """
        Descarga una imagen desde SeaweedFS

        Args:
            fid: File ID de SeaweedFS (ej: "1,abc123")
            file_name: Nombre del archivo

        Returns:
            Bytes de la imagen, o None si error
        """
        try:
            url = f"{self.seaweed_url}/{fid}/{file_name}"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                return response.content
            else:
                print(f"Error downloading from SeaweedFS: {response.status_code}")
                return None

        except Exception as e:
            print(f"Error en SeaweedFS download: {e}")
            return None

    def get_public_url(self, fid: str, file_name: str) -> str:
        """Construye URL pública para una imagen"""
        return f"{self.seaweed_public_url}/{fid}/{file_name}"

# Instancia global (singleton)
seaweedfs_client = SeaweedFSClient()
