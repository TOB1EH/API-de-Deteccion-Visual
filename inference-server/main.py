import logging
import os
import shutil
import time
import uuid
import base64
from pathlib import Path

import cv2
import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
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
    version="2.2.0",
)

DEFAULT_CORS_ORIGINS = "https://bfts2026.mooo.com"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_private_network_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

MODELS_DIR = Path("/app/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

ANNOTATED_DIR = Path("/tmp/annotated_images")
ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

FACE_TEMP_DIR = Path("/tmp/face_temp")
FACE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

loaded_models = {}

API_URL = os.environ.get("API_URL", "http://host.docker.internal:8000")
DEEPFACE_BACKEND = os.environ.get("DEEPFACE_BACKEND", "Facenet")
DEEPFACE_DETECTOR = os.environ.get("DEEPFACE_DETECTOR", "mtcnn")


def generate_embedding(image_path: str) -> dict:
    from deepface import DeepFace
    import numpy as np
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name=DEEPFACE_BACKEND,
            enforce_detection=False,
            detector_backend=DEEPFACE_DETECTOR,
            normalization="Facenet",
        )
        if isinstance(result, list) and len(result) > 0:
            item = result[0]
            if isinstance(item, dict):
                embedding = item.get("embedding", [])
                raw_conf = item.get("face_confidence", 1.0)
                facial_area = item.get("facial_area", {})
            elif isinstance(item, list):
                embedding = item
                raw_conf = 1.0
                facial_area = {}
            else:
                return {"error": "Formato de resultado inesperado"}
        elif isinstance(result, dict):
            embedding = result.get("embedding", [])
            raw_conf = result.get("face_confidence", 1.0)
            facial_area = result.get("facial_area", {})
        else:
            return {"error": "No se detectaron rostros"}
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        if not isinstance(embedding, list) or len(embedding) == 0:
            return {"error": "Embedding vacio o invalido"}
        return {
            "embedding": embedding,
            "confidence": min(float(raw_conf), 1.0),
            "facial_area": facial_area,
        }
    except Exception as e:
        logger.error("DeepFace error: %s", e)
        return {"error": str(e)}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models_count": len([f for f in MODELS_DIR.iterdir() if f.is_file() and f.suffix == ".pt"]),
        "loaded_models": list(loaded_models.keys()),
        "face_recognition": True,
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
    image: UploadFile = File(...),
    token: str = Form(""),
):
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
        with open(temp_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(temp_path)
        image_b64 = f"data:image/jpeg;base64,{image_b64}"
        payload = {
            "image_base64": image_b64,
            "embedding": emb_result["embedding"],
            "confidence": emb_result["confidence"],
        }
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.post(
            f"{API_URL}/api/persons/{person_id}/embeddings",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        return result
    except requests.RequestException as e:
        logger.exception("Error forwarding to API")
        raise HTTPException(status_code=502, detail=f"Error de conexion con la API: {str(e)}")
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
        os.remove(temp_path)
        facial_area = emb_result.get("facial_area", {})
        payload = {
            "embedding": emb_result["embedding"],
            "threshold": threshold,
        }
        resp = requests.post(
            f"{API_URL}/api/face-recognition",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        result["facial_area"] = facial_area
        return result
    except requests.RequestException as e:
        logger.exception("Error forwarding to API")
        raise HTTPException(status_code=502, detail=f"Error de conexion con la API: {str(e)}")
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
