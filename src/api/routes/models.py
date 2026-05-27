"""
Modelos para las rutas de la API, define que hace cada URL
"""

from fastapi import APIRouter
from pathlib import Path
from ..schemas.model import ModelInfo, ModelsResponse

router = APIRouter(
    prefix="/models",
    tags=["models"],
    responses={404: {"description": "Models not found"}},
)

# Ruta donde están los modelos locales
MODELS_PATH = Path("./models/local")
@router.get("", response_model=ModelsResponse)
async def get_models():
    """
    Lista todos los modelos disponibles en la carpeta local.

    GET /api/models

    Lee la carpeta models/local/ y retorna información de cada modelo.
    Solo incluye archivos con extensión .pt, .weights, .onnx

    Retorna:
        - total: cantidad de modelos encontrados
        - models: lista de ModelInfo con nombre, tamaño, tipo, ruta
    """
    models = []

    # Verificar que la carpeta existe
    if not MODELS_PATH.exists():
        return ModelsResponse(total=0, models=[])

    try:
        # Recorrer archivos en models/local/
        for file_path in MODELS_PATH.iterdir():
            # Solo incluir archivos (no carpetas) con extensiones válidas
            if file_path.is_file() and file_path.suffix in ['.pt', '.weights', '.onnx']:
                file_size = file_path.stat().st_size

                # Crear objeto ModelInfo
                model_info = ModelInfo(
                    name=file_path.name,                    # ej: yolo11n.pt
                    size=file_size,                         # tamaño en bytes
                    type="yolo",                            # tipo de modelo
                    path=f"models/local/{file_path.name}"   # ruta relativa
                )
                models.append(model_info)

        # Ordenar alfabéticamente por nombre
        models.sort(key=lambda m: m.name)

        return ModelsResponse(total=len(models), models=models)

    except Exception as e:
        print(f"Error leyendo modelos: {e}")
        return ModelsResponse(total=0, models=[])

@router.get("/{model_name}", response_model=ModelInfo)
async def get_model(model_name: str):
    """
    Obtiene información detallada de un modelo específico.

    GET /api/models/yolo11n.pt

    Args:
        model_name: nombre del archivo del modelo (ej: yolo11n.pt)

    Retorna:
        - ModelInfo con información del modelo
        - 404 si no existe
    """
    model_path = MODELS_PATH / model_name

    # Verificar que existe y es un archivo
    if not model_path.exists() or not model_path.is_file():
        return {"error": f"Modelo '{model_name}' no encontrado"}, 404

    # Verificar extensión válida
    if model_path.suffix not in ['.pt', '.weights', '.onnx']:
        return {"error": f"Tipo de archivo no válido: {model_path.suffix}"}, 400

    try:
        file_size = model_path.stat().st_size

        return ModelInfo(
            name=model_path.name,
            size=file_size,
            type="yolo",
            path=f"models/local/{model_path.name}"
        )

    except Exception as e:
        print(f"Error obteniendo modelo: {e}")
        return {"error": "Error interno del servidor"}, 500
