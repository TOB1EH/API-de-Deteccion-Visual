"""
Utilidades para deteccion y validacion de formatos de imagen.

Centraliza la logica de:
1. Detectar formato real de una imagen a partir de sus magic bytes
   (JPEG = 0xFFD8, PNG = 0x89504E47, GIF = GIF87a/GIF89a, WebP = RIFF+WEBP, BMP = BM)
2. Validar que los bytes correspondan a una imagen valida (via PIL)
3. Mapear formato a MIME type

Esto resuelve el problema de que todo el sistema hardcodeaba 'image/jpeg'
independientemente del formato real de la imagen, causando:
- Visor de Ubuntu rechazaba PNGs servidos como image/jpeg
- No habia validacion temprana de formato (errores opacos 502 en inference-server)
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Mapa de magic bytes a nombre de formato
# Cada entrada: (nombre_formato, bytes_de_inicio)
# Usamos startswith multiple para detectar el formato
MAGIC_BYTES = [
    ('jpeg', b'\xff\xd8\xff'),
    ('png', b'\x89PNG\r\n\x1a\n'),
    ('gif', b'GIF87a'),
    ('gif', b'GIF89a'),
    ('webp', b'RIFF'),  # WebP empieza con RIFF, hay que chequear offset 8
    ('bmp', b'BM'),
]

MIME_MAP = {
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'bmp': 'image/bmp',
}

EXTENSION_MAP = {
    'jpeg': 'jpg',
    'png': 'png',
    'gif': 'gif',
    'webp': 'webp',
    'bmp': 'bmp',
}


def detect_image_format(image_bytes: bytes) -> Optional[str]:
    """
    Detecta el formato de imagen a partir de los magic bytes.

    Args:
        image_bytes: Bytes de la imagen

    Returns:
        Nombre del formato ('jpeg', 'png', 'gif', 'webp', 'bmp')
        o None si no se pudo detectar
    """
    if not image_bytes or len(image_bytes) < 4:
        return None

    # WebP requiere chequeo adicional en offset 8
    if image_bytes.startswith(b'RIFF') and len(image_bytes) > 12:
        if image_bytes[8:12] == b'WEBP':
            return 'webp'

    for fmt, magic in MAGIC_BYTES:
        if fmt == 'webp':
            continue  # ya lo chequeamos arriba
        if image_bytes.startswith(magic):
            return fmt

    return None


def get_mime_type(image_format: str) -> str:
    """
    Retorna el MIME type correspondiente a un formato.

    Args:
        image_format: Nombre del formato ('jpeg', 'png', etc.)

    Returns:
        MIME type string (ej: 'image/jpeg')
    """
    return MIME_MAP.get(image_format, 'application/octet-stream')


def get_extension(image_format: str) -> str:
    """
    Retorna la extension de archivo correspondiente a un formato.

    Args:
        image_format: Nombre del formato ('jpeg', 'png', etc.)

    Returns:
        Extension sin punto (ej: 'jpg', 'png')
    """
    return EXTENSION_MAP.get(image_format, 'jpg')


def get_format_and_mime(image_bytes: bytes) -> tuple:
    """
    Detecta formato y MIME type de una imagen.

    Args:
        image_bytes: Bytes de la imagen

    Returns:
        Tuple (formato, mime_type). Si no se detecta, defaults a ('jpeg', 'image/jpeg')
    """
    fmt = detect_image_format(image_bytes)
    if not fmt:
        logger.warning("No se pudo detectar formato de imagen, usando default jpeg")
        fmt = 'jpeg'
    return fmt, get_mime_type(fmt)


def validate_image(image_bytes: bytes) -> bool:
    """
    Valida que los bytes correspondan a una imagen procesable
    intentando abrirla con PIL.

    Args:
        image_bytes: Bytes a validar

    Returns:
        True si es una imagen valida, False si no
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        return True
    except Exception:
        logger.warning("Falló validacion de imagen PIL: los bytes no son una imagen valida")
        return False
