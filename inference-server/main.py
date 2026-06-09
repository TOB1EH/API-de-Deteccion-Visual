import logging
import os
import shutil
import time
import uuid
from pathlib import Path

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("yolo-server")

app = FastAPI(
    title="YOLO Inference + Face Recognition Server",
    description="Servidor de inferencia YOLO y reconocimiento facial DeepFace.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS_DIR = Path("/app/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

ANNOTATED_DIR = Path("/tmp/annotated_images")
ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

FACE_TEMP_DIR = Path("/tmp/face_temp")
FACE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

loaded_models = {}

DATABASE_URL = os.environ.get("DATABASE_URL")
SEAWEED_URL = os.environ.get("SEAWEED_URL")
DEEPFACE_BACKEND = os.environ.get("DEEPFACE_BACKEND", "Facenet")
face_db = None
if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    logger.info("Face recognition enabled: DATABASE_URL configured")
else:
    logger.info("Face recognition disabled: set DATABASE_URL to enable")


def get_db_connection():
    if not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error("DB connection error: %s", e)
        return None


def upload_to_seaweed(file_path: str, filename: str) -> str:
    if not SEAWEED_URL:
        return ""
    import requests
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{SEAWEED_URL}/",
                files={"file": (filename, f)},
                timeout=30,
            )
        resp.raise_for_status()
        fid = resp.json().get("fid", "")
        if fid:
            return f"{SEAWEED_URL}/{fid}"
        return ""
    except Exception as e:
        logger.error("SeaweedFS upload error: %s", e)
        return ""


def generate_embedding(image_path: str) -> dict:
    from deepface import DeepFace
    import numpy as np
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name=DEEPFACE_BACKEND,
            enforce_detection=False,
            detector_backend="opencv",
            normalization="base",
        )
        if isinstance(result, list) and len(result) > 0:
            item = result[0]
            if isinstance(item, dict):
                embedding = item.get("embedding", [])
                raw_conf = item.get("face_confidence", 1.0)
            elif isinstance(item, list):
                embedding = item
                raw_conf = 1.0
            else:
                return {"error": "Formato de resultado inesperado"}
        elif isinstance(result, dict):
            embedding = result.get("embedding", [])
            raw_conf = result.get("face_confidence", 1.0)
        else:
            return {"error": "No se detectaron rostros"}
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        if not isinstance(embedding, list) or len(embedding) == 0:
            return {"error": "Embedding vacio o invalido"}
        return {"embedding": embedding, "confidence": min(float(raw_conf), 1.0)}
    except Exception as e:
        logger.error("DeepFace error: %s", e)
        return {"error": str(e)}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models_count": len([f for f in MODELS_DIR.iterdir() if f.is_file() and f.suffix == ".pt"]),
        "loaded_models": list(loaded_models.keys()),
        "face_recognition": DATABASE_URL is not None,
    }


@app.get("/models", response_model=list[str])
async def list_models():
    try:
        models = [f.name for f in MODELS_DIR.iterdir() if f.is_file() and f.suffix == ".pt"]
        return models
    except Exception as e:
        logger.exception("Error listing models")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models", response_model=dict)
async def upload_model(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".pt"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .pt")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = MODELS_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info("Modelo subido: %s (%d bytes)", file.filename, file_path.stat().st_size)
    return {"message": f"Modelo {file.filename} subido correctamente", "filename": file.filename}


@app.post("/infer")
async def infer(
    image: UploadFile = File(...),
    model_name: str = Form(...),
    confidence: float = Form(0.25),
):
    model_path = MODELS_DIR / model_name
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Modelo {model_name} no encontrado")
    if not image.filename or not image.filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
        raise HTTPException(
            status_code=400,
            detail="Formato de imagen invalido. Soportados: PNG, JPG, JPEG, BMP, TIFF",
        )
    temp_image_path = f"/tmp/{uuid.uuid4()}_{image.filename}"
    try:
        with open(temp_image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        if model_name not in loaded_models:
            try:
                loaded_models[model_name] = YOLO(str(model_path))
                logger.info("Modelo cargado: %s", model_name)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al cargar el modelo: {str(e)}")
        model = loaded_models[model_name]
        start_time = time.time()
        results = model(temp_image_path, conf=confidence)
        end_time = time.time()
        inference_time_ms = int((end_time - start_time) * 1000)
        annotated_image_id = str(uuid.uuid4())
        if len(results) > 0:
            annotated_frame = results[0].plot()
            output_image_path = ANNOTATED_DIR / f"{annotated_image_id}.jpg"
            cv2.imwrite(str(output_image_path), annotated_frame)
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                conf = float(box.conf[0]) * 100
                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "bbox_object": {
                        "x_min": x1,
                        "y_min": y1,
                        "x_max": x2,
                        "y_max": y2,
                    },
                    "classname": class_name,
                    "classnumber": class_id,
                    "conf": round(conf, 1),
                })
        os.remove(temp_image_path)
        logger.info(
            "Inferencia completada: %s - %d detecciones en %dms",
            model_name,
            len(detections),
            inference_time_ms,
        )
        return {
            "info": {
                "error": False,
                "errormsg": "",
                "infertimems": inference_time_ms,
            },
            "results": detections,
            "annotated_image_url": f"/infer/download/{annotated_image_id}",
        }
    except HTTPException:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        raise
    except Exception as e:
        logger.exception("Error en inferencia")
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        return {
            "info": {
                "error": True,
                "errormsg": str(e),
                "infertimems": -1,
            },
            "results": [],
        }


@app.get("/infer/download/{image_id}")
async def download_annotated_image(image_id: str):
    file_path = ANNOTATED_DIR / f"{image_id}.jpg"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Imagen anotada no encontrada")
    return FileResponse(file_path, media_type="image/jpeg")


@app.post("/face/embed")
async def face_embed(
    person_id: str = Form(...),
    image: UploadFile = Form(...),
):
    if not DATABASE_URL:
        raise HTTPException(status_code=501, detail="Face recognition no habilitado (falta DATABASE_URL)")
    if not image.filename:
        raise HTTPException(status_code=400, detail="Archivo de imagen requerido")
    temp_path = str(FACE_TEMP_DIR / f"{uuid.uuid4()}_{image.filename}")
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="No se pudo conectar a la base de datos")
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT person_id::TEXT, name FROM persons WHERE person_id = %s", (person_id,))
        person = cursor.fetchone()
        if not person:
            cursor.close()
            conn.close()
            os.remove(temp_path)
            raise HTTPException(status_code=404, detail=f"Persona {person_id} no encontrada")
        emb_result = generate_embedding(temp_path)
        if "error" in emb_result:
            cursor.close()
            conn.close()
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=emb_result["error"])
        image_url = upload_to_seaweed(temp_path, f"face_{person_id}_{uuid.uuid4()}.jpg")
        embedding_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO face_embeddings (embedding_id, person_id, embedding, confidence, image_url)
            VALUES (%s, %s, %s::vector, %s, %s)
            """,
            (embedding_id, person_id, emb_result["embedding"], emb_result["confidence"], image_url),
        )
        conn.commit()
        cursor.close()
        conn.close()
        os.remove(temp_path)
        logger.info("Embedding generado: %s para persona %s", embedding_id, person_id)
        return {
            "embedding_id": embedding_id,
            "person_id": person_id,
            "name": person["name"],
            "confidence": emb_result["confidence"],
            "image_url": image_url,
            "status": "generated",
        }
    except HTTPException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.exception("Error en face/embed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/face/recognize")
async def face_recognize(
    image: UploadFile = File(...),
    threshold: float = Form(0.8),
):
    if not DATABASE_URL:
        raise HTTPException(status_code=501, detail="Face recognition no habilitado (falta DATABASE_URL)")
    if not image.filename:
        raise HTTPException(status_code=400, detail="Archivo de imagen requerido")
    temp_path = str(FACE_TEMP_DIR / f"{uuid.uuid4()}_{image.filename}")
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        emb_result = generate_embedding(temp_path)
        if "error" in emb_result:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=emb_result["error"])
        conn = get_db_connection()
        if not conn:
            os.remove(temp_path)
            raise HTTPException(status_code=500, detail="No se pudo conectar a la base de datos")
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT fe.embedding_id::TEXT,
                   p.person_id::TEXT,
                   p.name,
                   fe.confidence,
                   fe.embedding <-> %s::vector AS distance
            FROM face_embeddings fe
            JOIN persons p ON p.person_id = fe.person_id
            WHERE fe.embedding <-> %s::vector < %s
            ORDER BY distance ASC
            LIMIT 5
            """,
            (emb_result["embedding"], emb_result["embedding"], 2.0 - threshold),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        os.remove(temp_path)
        matches = []
        for row in rows:
            distance = row["distance"]
            conf = max(0.0, 1.0 - distance)
            if conf >= threshold:
                matches.append({
                    "person_id": row["person_id"],
                    "name": row["name"],
                    "distance": distance,
                    "confidence": round(conf, 4),
                })
        return {
            "recognized": len(matches) > 0,
            "matches": matches,
            "threshold": threshold,
        }
    except HTTPException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.exception("Error en face/recognize")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
