"""
Rutas para la Recuperación y Consulta de Datos.

Actividad S3 (Obtención de fotograma): Implementa la recuperación de imágenes 
binarias desde SeaweedFS, soportando la generación de thumbnails bajo demanda.

Actividad S4 (Servicio de consulta): Proporciona un endpoint de búsqueda con 
filtros por geolocalización (lat/lon) y tipos de objetos detectados (clases).
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from ..services.db_service import db_service
from ..services.seaweedfs_client import seaweedfs_client
from ..schemas.frame import FrameSearchResponse, FrameSearchResult, DetectionInfo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/frames",
    tags=["frames"],
    responses={404: {"description": "Frame not found"}},
)

@router.get("/search", response_model=FrameSearchResponse)
async def search_frames(
    lat_min: Optional[float] = Query(None),
    lat_max: Optional[float] = Query(None),
    lon_min: Optional[float] = Query(None),
    lon_max: Optional[float] = Query(None),
    clases: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        class_list = [c.strip() for c in clases.split(",")] if clases else None

        filters = {}
        if lat_min is not None and lat_max is not None:
            filters["lat_min"] = lat_min
            filters["lat_max"] = lat_max
        if lon_min is not None and lon_max is not None:
            filters["lon_min"] = lon_min
            filters["lon_max"] = lon_max
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
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                image_url=row["image_url"],
                detections_count=row["detections_count"],
                metadata={
                    "camera_id": row.get("camera_id"),
                    "source": row.get("source")
                },
                created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
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
async def get_frame(frame_id: str, thumbnail: Optional[bool] = Query(False)):
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

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error obteniendo frame")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
