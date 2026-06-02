"""
Punto de entrada del microservicio face-api.
Procesa embeddings faciales (S5.2) y reconocimiento facial (S5.3).
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import face

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Face Recognition API",
    description="Microservicio de reconocimiento facial (DeepFace + pgvector)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(face.router, prefix="/api")

@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Face Recognition API",
        "version": "1.0.0"
    }
