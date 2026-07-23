"""
Rutas para la Recuperación y Consulta de Datos.

Actividad S3 (Obtención de fotograma): Implementa la recuperación de imágenes 
binarias desde SeaweedFS, soportando la generación de thumbnails bajo demanda.

Actividad S4 (Servicio de consulta): Proporciona un endpoint de búsqueda con 
filtros por geolocalización (lat/lon) y tipos de objetos detectados (clases).
"""
import logging
from datetime import timezone
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from ..services.db_service import db_service
from ..services.seaweedfs_client import seaweedfs_client
from ..services.image_utils import get_format_and_mime
from ..schemas.frame import FrameSearchResponse, FrameSearchResult, DetectionInfo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/frames",
    tags=["frames"],
    responses={404: {"description": "Frame not found"}},
)

@router.get("/search", response_model=FrameSearchResponse)
async def search_frames(
    # Usamos Optional[str] en vez de Optional[float] porque el frontend
    # puede enviar strings vacios ("") cuando el usuario no completa el campo.
    # FastAPI/Pydantic fallaria al parsear "" como float.
    lat_min: Optional[str] = Query(None),
    lat_max: Optional[str] = Query(None),
    lon_min: Optional[str] = Query(None),
    lon_max: Optional[str] = Query(None),
    clases: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    # Si clases llega como string vacio, lo tratamos como None
    if clases == "":
        clases = None

    # Convertimos los strings a float, manejando casos de string vacio o invalido
    try:
        lat_min_f = float(lat_min) if lat_min else None
    except (ValueError, TypeError):
        lat_min_f = None
    try:
        lat_max_f = float(lat_max) if lat_max else None
    except (ValueError, TypeError):
        lat_max_f = None
    try:
        lon_min_f = float(lon_min) if lon_min else None
    except (ValueError, TypeError):
        lon_min_f = None
    try:
        lon_max_f = float(lon_max) if lon_max else None
    except (ValueError, TypeError):
        lon_max_f = None

    # Auto-swap si el usuario invirtio min y max
    if lat_min_f is not None and lat_max_f is not None and lat_min_f > lat_max_f:
        lat_min_f, lat_max_f = lat_max_f, lat_min_f
    if lon_min_f is not None and lon_max_f is not None and lon_min_f > lon_max_f:
        lon_min_f, lon_max_f = lon_max_f, lon_min_f

    try:
        class_list = [c.strip() for c in clases.split(",")] if clases else None

        filters = {}
        if lat_min_f is not None and lat_max_f is not None:
            filters["lat_min"] = lat_min_f
            filters["lat_max"] = lat_max_f
        if lon_min_f is not None and lon_max_f is not None:
            filters["lon_min"] = lon_min_f
            filters["lon_max"] = lon_max_f
        if class_list:
            filters["classes"] = class_list
        if camera_id is not None:
            filters["camera_id"] = camera_id
        if source is not None:
            filters["source"] = source

        results = db_service.search_frames(filters, limit=limit, offset=offset)
        total = db_service.count_frames(filters)

        frames = []
        for row in results:
            detections = db_service.get_frame_detections(row["frame_id"])
            frames.append(FrameSearchResult(
                frame_id=row["frame_id"],
                model_id=row["model_id"],
                latitude=float(row["latitude"]) if row["latitude"] is not None else None,
                longitude=float(row["longitude"]) if row["longitude"] is not None else None,
                image_url=row["image_url"],
                detections_count=row["detections_count"],
                metadata={
                    "camera_id": row.get("camera_id"),
                    "source": row.get("source")
                },
                    created_at=row["created_at"].replace(tzinfo=timezone.utc).isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
                detections=[
                    DetectionInfo(
                        detection_id=d["detection_id"],
                        class_name=d["class_name"],
                        class_id=d["class_id"],
                        confidence=float(d["confidence"]),
                        bbox={"x_min": d["bbox_x_min"], "y_min": d["bbox_y_min"],
                              "x_max": d["bbox_x_max"], "y_max": d["bbox_y_max"]}
                    ) for d in detections
                ]
            ))

        return FrameSearchResponse(total=total, frames=frames)

    except Exception as e:
        logger.exception("Error en busqueda de frames")
        raise HTTPException(status_code=500, detail=f"Error en busqueda: {str(e)}")

@router.get("/{frame_id}")
async def get_frame_image(frame_id: str, thumbnail: Optional[bool] = Query(False)):
    try:
        frame = db_service.get_frame_by_id(frame_id)
        if not frame:
            raise HTTPException(status_code=404, detail=f"Frame {frame_id} no encontrado")

        image_url = frame["image_url"]
        fid = image_url.rstrip("/").rsplit("/", 1)[-1].rsplit(".", 1)[0]

        image_bytes = seaweedfs_client.download_image(fid)
        if not image_bytes:
            raise HTTPException(status_code=404, detail="Imagen no encontrada en storage")

        if thumbnail:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(image_bytes))
            img.thumbnail((300, 300))
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()
            return Response(content=image_bytes, media_type="image/jpeg")

        # Detectar formato real de la imagen para devolver Content-Type correcto
        # (resuelve error "Not a JPEG file" cuando la imagen es PNG, WebP, etc.)
        _, mime_type = get_format_and_mime(image_bytes)
        return Response(content=image_bytes, media_type=mime_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error obteniendo frame")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{frame_id}/detail")
async def get_frame_detail(frame_id: str):
    try:
        frame = db_service.get_frame_by_id(frame_id)
        if not frame:
            raise HTTPException(status_code=404, detail=f"Frame {frame_id} no encontrado")

        detections = db_service.get_frame_detections(frame_id)

        return {
            "frame_id": frame["frame_id"],
            "model_id": frame["model_id"],
            "latitude": float(frame["latitude"]),
            "longitude": float(frame["longitude"]),
            "image_url": frame["image_url"],
            "detections_count": frame["detections_count"],
            "metadata": {
                "camera_id": frame.get("camera_id"),
                "source": frame.get("source")
            },
            "created_at": frame["created_at"].replace(tzinfo=timezone.utc).isoformat() if hasattr(frame["created_at"], "isoformat") else str(frame["created_at"]),
            "detections": [
                {
                    "detection_id": d["detection_id"],
                    "class_name": d["class_name"],
                    "class_id": d["class_id"],
                    "confidence": float(d["confidence"]),
                    "bbox": {
                        "x_min": d["bbox_x_min"], "y_min": d["bbox_y_min"],
                        "x_max": d["bbox_x_max"], "y_max": d["bbox_y_max"]
                    }
                } for d in detections
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error obteniendo detalle del frame")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
