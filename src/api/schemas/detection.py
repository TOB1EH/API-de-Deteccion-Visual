"""
Define la estructura de datos para POST /detections. Con esto Pydantic se
encarga de validar que la solicitud tenga el formato correcto, y también
de generar la documentación automática de la API.
Sirve para validar que el cliente envia los datos correctos.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

# Entrada: Lo que el Cliente envia

class BboxSchema(BaseModel):
    """
    Bounding box de una deteccion
    """
    x_min: int      # Esquina superior izquierda de la caja delimitadora X
    y_min: int      # Esquina superior izquierda de la caja delimitadora Y
    x_max: int      # Esquina inferior derecha de la caja delimitadora X
    y_max: int      # Esquina inferior derecha de la caja delimitadora Y

class SingleDetectionRequest(BaseModel):
    """
    Una deteccion individual, que se incluye en la lista de detecciones
    """
    class_name: str                             # Nombre de la clase detectada
    class_id: int                               # ID de la clase detectada
    confidence: float = Field(..., ge=0, le=1)  # Confianza de la detección (0.0 - 1.0)
    bbox: BboxSchema                            # Bounding box de la detección

class MetadataSchema(BaseModel):
    """
    Metadatos opcionales de la imagen
    """
    camera_id: Optional[str] = None   # ID de la cámara que capturó la imagen
    source: Optional[str] = None      # Fuente de la imagen
    timestamp: Optional[str] = None   # Timestamp de la captura de la imagen

class DetectionRequest(BaseModel):
    """
    Estructura de la solicitud POST /detections
    """
    # ConfigDict para evitar que Pydantic trate de validar campos con nombres reservados
    model_config = ConfigDict(protected_namespaces=())

    image_base64: str                          # Imagen codificada en base64
    model_id: str                              # ID del modelo utilizado para la detección
    latitude: float                            # Latitud de la ubicación donde se tomó la imagen
    longitude: float                           # Longitud de la ubicación donde se tomó la imagen
    detections: List[SingleDetectionRequest]   # Lista de detecciones en la imagen
    metadata: Optional[MetadataSchema] = None  # Metadatos opcionales de la imagen

# Salida: Lo que el Servidor responde

class DetectionResponse(BaseModel):
    """
    Respuesta exitosa del POST /detections
    """
    frame_id: str # ID unico del fotograma procesado
    image_url: str # URL publica para descargar la imagen procesada
    detections_count: int # Número total de detecciones procesadas
    status: str
    message: Optional[str] = None # Mensaje adicional (opcional)
    timestamp: str # Timestamp de cuando se procesó la solicitud

class ErrorResponse(BaseModel):
    """
    Respuesta de error del POST /detections
    """
    error: str # Descripción del error
    status_code: int # Código de estado HTTP
    timestamp: str # Timestamp de cuando se produjo el error
