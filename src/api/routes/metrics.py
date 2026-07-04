import logging
import time
from fastapi import APIRouter, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

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
    "Tiempo de inferencia en segundos",
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


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
