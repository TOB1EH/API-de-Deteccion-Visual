"""
Punto de entrada de la aplicación, define las rutas y los servicios que se van a
utilizar en la API. Es el archivo principal de la aplicación, donde se configura
el servidor y se importan las rutas y servicios necesarios para el funcionamiento
de la API.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import models, detections
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ===== CREAR APLICACIÓN FASTAPI =====
app = FastAPI(
    title="API Detección Visual",
    description="API para detección visual, almacenamiento y reconocimiento facial",
    version="1.0.0",
    docs_url="/docs",              # Swagger UI en /docs
    redoc_url="/redoc",            # ReDoc en /redoc
    openapi_url="/openapi.json",   # OpenAPI schema
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

# ===== ENDPOINTS GLOBALES =====
@app.get("/")
async def root():
    """Health check en raíz"""
    return {
        "message": "API Detection Service OK",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Endpoint de healthcheck detallado"""
    return {
        "status": "healthy",
        "service": "API Detección Visual",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

# ===== EJECUTAR SI SE LLAMA DIRECTAMENTE =====
if __name__ == "__main__":
    import uvicorn
    # Ejecuta servidor en 0.0.0.0:8000 con reload (para desarrollo)
    uvicorn.run(app, host="0.0.0.0", port="8000", reload=True)
