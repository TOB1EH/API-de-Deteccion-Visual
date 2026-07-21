import logging
import os
import time
import asyncio
import requests
from fastapi import APIRouter, Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["metrics"],
)

REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total de requests HTTP",
    ["endpoint", "method", "http_status"],
)

INFERENCE_TIME = Histogram(
    "inference_time_seconds",
    "Tiempo de inferencia YOLO en segundos",
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
)

RECOGNITION_COUNT = Counter(
    "face_recognition_total",
    "Total de reconocimientos faciales",
    ["result"],
)

DETECTION_COUNT = Counter(
    "detections_total",
    "Total de detecciones ejecutadas",
)

EMBEDDING_TIME = Histogram(
    "embedding_time_seconds",
    "Tiempo de generacion de embeddings faciales en segundos",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

COMPARISON_TIME = Histogram(
    "comparison_time_seconds",
    "Tiempo de comparacion facial en segundos",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

INFERENCE_SERVER_UP = Gauge(
    "inference_server_up",
    "Estado del nodo de inferencia (1=online, 0=offline)",
)

INFERENCE_SERVER_URL = os.getenv("INFERENCE_SERVER_URL", "http://localhost:8001")


def _check_inference_server() -> bool:
    try:
        resp = requests.get(f"{INFERENCE_SERVER_URL}/health", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


async def inference_server_healthcheck_loop(interval: int = 30):
    while True:
        INFERENCE_SERVER_UP.set(0)
        is_up = await asyncio.to_thread(_check_inference_server)
        if is_up:
            INFERENCE_SERVER_UP.set(1)
        await asyncio.sleep(interval)


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
