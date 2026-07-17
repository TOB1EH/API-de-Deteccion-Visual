# YOLO Inference Server

Servidor FastAPI para subir modelos YOLO y realizar inferencia en imagenes.

## Caracteristicas

- Lista modelos YOLO disponibles (`GET /models`)
- Sube nuevos modelos YOLO (`POST /models`)
- Realiza inferencia en imagenes con modelo y umbral de confianza (`POST /infer`)
- Descarga de imagenes anotadas (`GET /infer/download/{image_id}`)
- Health check (`GET /health`)
- Documentacion Swagger automatica en `/docs`
- CORS habilitado para integracion con otros servicios

## Estructura

```
inference-server/
├── main.py            # Aplicacion FastAPI
├── requirements.txt   # Dependencias de Python
├── Dockerfile         # Instrucciones de construccion de Docker
├── docker-compose.yml # Configuracion de docker-compose
├── build.sh           # Script de build y push a Docker Hub
├── models/            # Modelos YOLO (.pt)
└── README.md          # Este archivo
```

## Uso con Docker

```bash
# Construir la imagen
docker build -t tfunes/inference-server .

# Ejecutar el contenedor
docker run -d \
  --name inference-server \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  tfunes/inference-server
```

## Uso con Docker Compose

```bash
docker-compose up -d
```

## Endpoints

### GET /health
Verifica que el servidor esta operativo.

**Respuesta:**
```json
{
  "status": "healthy",
  "models_count": 3,
  "loaded_models": ["yolo11n.pt"]
}
```

### GET /models
Lista los modelos YOLO disponibles.

**Respuesta:**
```json
["yolo11n.pt", "celular.pt", "mouse.pt"]
```

### POST /models
Sube un nuevo modelo YOLO (.pt).

**Parametros:**
- `file`: archivo `.pt` a subir

### POST /infer
Realiza inferencia en una imagen.

**Parametros:**
- `image`: archivo de imagen (PNG, JPG, JPEG, BMP, TIFF)
- `model_name`: nombre del modelo YOLO
- `confidence`: umbral de confianza (default: 0.25)

**Respuesta:**
```json
{
  "info": {
    "error": false,
    "errormsg": "",
    "infertimems": 116
  },
  "results": [
    {
      "bbox": [1.25, 2.44, 884.40, 712.48],
      "bbox_object": {
        "x_min": 1.25, "y_min": 2.44,
        "x_max": 884.40, "y_max": 712.48
      },
      "classname": "cat",
      "classnumber": 15,
      "conf": 46.7
    }
  ],
  "annotated_image_url": "/infer/download/uuid"
}
```

### GET /infer/download/{image_id}
Descarga la imagen anotada con bounding boxes.

## Imagen Docker Hub

```bash
docker pull tfunes/inference-server:latest
```

## Build y Push automatizado

```bash
chmod +x build.sh
./build.sh
```

## Desarrollo local

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Licencia

Proyecto de uso academico - Trabajo Integrador SOA 2026.
