"""
Orquestador Principal de la API (Arquitectura SOA).

Configura el servidor FastAPI e integra los routers correspondientes a los 
servicios S1, S2, S3 y S4. 
del sistema mediante el prefijo unificado /api y la documentación automática.
"""

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.middleware.cors import CORSMiddleware
from .routes import models, detections, frames, persons, face_proxy
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ===== CREAR APLICACIÓN FASTAPI =====
app = FastAPI(
    title="API Deteccion Visual",
    description="API para deteccion visual, almacenamiento y reconocimiento facial",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# ===== MIDDLEWARE CORS =====

# Permitir solicitudes desde cualquier origen (desarrollo)
# En producción, especificar dominios: allow_origins=["https://bfts2026.mooo.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== INCLUIR ROUTERS (RUTAS) =====
# Estos prefijos se agregan a las rutas definidas en cada router
app.include_router(models.router, prefix="/api")       # GET /api/models
app.include_router(detections.router, prefix="/api")   # POST /api/detections
app.include_router(frames.router, prefix="/api")       # GET /api/frames, /api/frames/search
app.include_router(persons.router, prefix="/api")      # POST/GET /api/persons
app.include_router(face_proxy.router, prefix="/api")  # POST /api/faces/embeddings, /api/faces/recognize

# ===== ENDPOINTS GLOBALES =====
@app.get("/")
async def root():
    """Bienvenida e instrucciones de instalacion del nodo local."""
    return {
        "message": "API Detection Service OK",
        "version": "1.0.0",
        "docs": "/api/docs",
        "setup_cliente": "/setup_cliente.py",
        "instrucciones": (
            "Para procesar imagenes con tu propia PC, "
            "abre tu terminal y ejecuta:"
        ),
        "comando_linux_mac": (
            "curl -sO https://bfts2026.mooo.com/setup_cliente.py "
            "&& python3 setup_cliente.py"
        ),
        "comando_windows": (
            "curl -sO https://bfts2026.mooo.com/setup_cliente.py "
            "&& python setup_cliente.py"
        )
    }


@app.get("/health")
async def health_check():
    """Endpoint de healthcheck detallado"""
    return {
        "status": "healthy",
        "service": "API Deteccion Visual",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }


@app.get("/setup_cliente.py", include_in_schema=False)
async def download_setup_script():
    """Descarga el script de instalacion del nodo de inferencia local."""
    script_path = Path("/app/client/setup_cliente.py")
    if script_path.exists():
        return FileResponse(
            script_path,
            media_type="text/plain",
            filename="setup_cliente.py"
        )
    return PlainTextResponse(
        "Error: Script de instalacion no disponible en el servidor.",
        status_code=503
    )


REDOC_JS_URL = "https://cdn.jsdelivr.net/npm/redoc@2.4.0/bundles/redoc.standalone.js"
SWAGGER_CSS_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css"
SWAGGER_BUNDLE_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"


@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui():
    """
    Servicio para visualizar la documentación de la API en Swagger UI.
    """
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="API Deteccion Visual - Swagger UI",
        swagger_js_url=SWAGGER_BUNDLE_URL,
        swagger_css_url=SWAGGER_CSS_URL,
    )


@app.get("/api/redoc", include_in_schema=False)
async def custom_redoc():
    """Servicio para visualizar la documentación de la API en ReDoc."""
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title="API Deteccion Visual - ReDoc",
        redoc_js_url=REDOC_JS_URL,
    )


# ===== EJECUTAR SI SE LLAMA DIRECTAMENTE =====
if __name__ == "__main__":
    import uvicorn
    # Ejecuta servidor en 0.0.0.0:8000 con reload (para desarrollo)
    uvicorn.run(app, host="0.0.0.0", port="8000", reload=True)
