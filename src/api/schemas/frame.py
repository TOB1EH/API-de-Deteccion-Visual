"""
Actividad S4: Esquemas de datos para Consulta y Filtrado.
Define la estructura de salida para los resultados de búsqueda de fotogramas,
incluyendo metadatos geográficos, URLs de imágenes y la lista detallada de 
detecciones (detectionId, bbox, confianza) según el modelo de datos del sistema.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

class DetectionInfo(BaseModel):
    detection_id: str
    class_name: str
    class_id: int
    confidence: float
    bbox: Dict[str, int]

class FrameSearchResult(BaseModel):
    frame_id: str
    model_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: str
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos originales completos")
    detections_count: int
    created_at: str
    detections: List[DetectionInfo] = []

class FrameSearchResponse(BaseModel):
    total: int
    frames: List[FrameSearchResult]
