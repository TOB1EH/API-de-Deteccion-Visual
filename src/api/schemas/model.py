"""
Define la estructura de datos que retorna GET /models. Con esto Pydantic
se encarga de validar que la respuesta tenga el formato correcto, y también
de generar la documentación automática de la API.
"""

from pydantic import BaseModel
from typing import List

# Estructura de un modelo individual
class ModelInfo(BaseModel):
    """
    Información detallada de un modelo, que se incluye en la lista de modelos
    """
    name: str   # Nombre del modelo
    size: int   # Bytes del archivo
    type: str   # Tipo de modelo
    path: str   # Ruta al archivo del modelo

    class Config:
        """
        Ejemplo de cómo se vería un modelo en la documentación automática de la API
        """
        json_schema_extra = {
            "example": {
                "name": "yolov5s.pt",
                "size": 12345678,
                "type": "PyTorch",
                "path": "/models/yolov5s.pt"
            }
        }

# Estructura de la respuesta de GET /models
class ModelsResponse(BaseModel):
    """
    Respuesta del endpoint GET /models, que incluye el número total de modelos y una lista
    """
    total: int              # Número total de modelos disponibles
    models: List[ModelInfo] # Lista de modelos con su información detallada

    class Config:
        """
        Ejemplo de cómo se vería la respuesta completa en la documentación automática de la API
        """
        json_schema_extra = {
            "example": {
                "total": 2,
                "models": [
                    {
                        "name": "yolov5s.pt",
                        "size": 12345678,
                        "type": "PyTorch",
                        "path": "/models/yolov5s.pt"
                    },
                    {
                        "name": "yolov5m.pt",
                        "size": 23456789,
                        "type": "PyTorch",
                        "path": "/models/yolov5m.pt"
                    }
                ]
            }
        }
