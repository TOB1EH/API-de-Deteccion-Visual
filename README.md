# API de Deteccion Visual

API REST para deteccion de objetos en imagenes (YOLO) y reconocimiento facial (DeepFace) con persistencia distribuida. Proyecto integrador de la materia Sistemas Operativos Avanzados (SOA) 2026.

## Arquitectura

```
+---------------------+     HTTPS     +---------------------------+
| Nodo Local           |  ----------> | VM Remota                  |
|                      |              | bfts2026.mooo.com          |
| setup_cliente.py     |              |                            |
|   (CLI Python)       |              | Nginx (proxy reverso)      |
|                      |              |   +-> FastAPI (Backend)    |
| inference-server     |              |   +-> SeaweedFS (Storage)  |
|   YOLO + DeepFace    |              |   +-> pgAdmin (DB admin)   |
|   (Docker local)     |              |                            |
+---------------------+              | PostgreSQL 16 + pgvector   |
                                      +---------------------------+
```

### Flujo de datos
1. El usuario captura una imagen en su PC
2. El CLI local la envia al inference-server (Docker con YOLO/DeepFace)
3. Las detecciones + imagen se envian via HTTPS a la API remota
4. La API persiste la imagen en SeaweedFS y los metadatos en PostgreSQL
5. Los embeddings faciales se almacenan como vectores pgvector para busqueda por similitud

## Stack tecnologico

| Componente | Tecnologia | Version |
|---|---|---|
| Backend API | Python FastAPI | 3.11 / 0.115 |
| Deteccion de objetos | Ultralytics YOLO | 11n/s |
| Reconocimiento facial | DeepFace (Facenet) | 0.0.79 |
| Base de datos | PostgreSQL + pgvector | 16 |
| Almacenamiento de objetos | SeaweedFS | latest |
| Proxy reverso | Nginx + Let's Encrypt | 1.31.1 |
| Contenedores | Docker Compose | 3.9 |
| Cliente | Python (CLI) | 3.8+ |

## Instalacion y uso

### 1. Clonar el repositorio
```bash
git clone https://github.com/bfts2026/api_detection_visual.git
cd api_detection_visual
```

### 2. Instalar nodo de inferencia local
```bash
pip install Pillow
python3 client/setup_cliente.py install
```
Esto descarga Docker, la imagen del inference-server y los modelos YOLO, e inicia el contenedor en `localhost:8001`.

Tambien se puede descargar el script directamente desde el servidor remoto:
```bash
curl -O https://bfts2026.mooo.com/setup_cliente.py
python3 setup_cliente.py install
```

### 3. Inferir una imagen
```bash
python3 client/setup_cliente.py infer ~/foto.jpg --model yolo11n.pt --lat -34.60 --lon -58.38
```

### 4. Consultar fotogramas
```bash
python3 client/setup_cliente.py frames list --clases person --limit 10
python3 client/setup_cliente.py frames get <frame_id> --thumbnail
python3 client/setup_cliente.py frames annotate <frame_id>
```

### 5. Reconocimiento facial
```bash
python3 client/setup_cliente.py persons create "Juan" "Perez"
python3 client/setup_cliente.py faces embed <person_id> ~/foto_referencia.jpg
python3 client/setup_cliente.py faces recognize ~/foto_test.jpg --threshold 0.5
```

## Endpoints de la API

| # | Metodo | Ruta | Descripcion |
|---|---|---|---|
| S1 | GET | `/api/models` | Lista modelos YOLO disponibles |
| S1 | POST | `/api/models` | Sube un nuevo modelo YOLO |
| S2 | POST | `/api/detections` | Ejecuta deteccion y persiste resultados |
| S3 | GET | `/api/frames/{id}` | Descarga imagen de un fotograma (?thumbnail=true) |
| S4 | GET | `/api/frames/search` | Busca fotogramas con filtros |
| S5.1 | POST | `/api/persons` | Crea una persona |
| S5.1 | GET | `/api/persons/{id}` | Obtiene una persona |
| S5.2 | POST | `/api/persons/{id}/embeddings` | Almacena embedding facial |
| S5.3 | POST | `/api/face-recognition` | Reconoce rostro por similitud coseno |
| - | GET | `/health` | Health check del servicio |
| - | GET | `/setup_cliente.py` | Descarga el CLI cliente |

## Estructura del repositorio

```
.
├── src/api/                 # Backend FastAPI
│   ├── main.py              # Orquestador principal
│   ├── routes/              # Endpoints por servicio (S1-S5)
│   ├── schemas/             # Modelos Pydantic
│   └── services/            # Conexion BD, SeaweedFS
├── client/                  # CLI cliente
│   ├── setup_cliente.py     # Script de usuario
│   └── README.md            # Documentacion del CLI
├── inference-server/        # Servidor YOLO + DeepFace (Docker)
├── docker/                  # Configuracion Nginx, BD
├── docker-compose.yml       # Despliegue remoto (HTTPS)
├── docker-compose.local.yml # Despliegue local (HTTP)
├── Dockerfile.api           # Build de la API
└── models/                  # Pesos de modelos YOLO
```

## Despliegue

### Local (desarrollo)
```bash
docker compose -f docker-compose.local.yml up -d
```
- API en `http://localhost:8000`
- Sin HTTPS, sin SeaweedFS (depende del remoto)

### Remoto (produccion)
```bash
docker compose up -d
```
- API en `https://bfts2026.mooo.com/api/`
- HTTPS con Let's Encrypt
- PostgreSQL + pgvector, SeaweedFS, pgAdmin

## Acceso remoto

| Servicio | URL | Credenciales |
|---|---|---|
| API Health | `https://bfts2026.mooo.com/` | - |
| Swagger UI | `https://bfts2026.mooo.com/api/docs` | - |
| pgAdmin | `https://bfts2026.mooo.com/pgadmin/` | admin@bfts2026.mooo.com / bfts2026. |
| SeaweedFS | `https://bfts2026.mooo.com/seaweed/` | - |

## Variables de entorno

| Variable | Default | Descripcion |
|---|---|---|
| `API_BASE` | `https://bfts2026.mooo.com` | URL del backend |
| `API_URL` | `https://bfts2026.mooo.com` | URL para persistencia facial |
| `FACE_INFER_URL` | `http://localhost:8001` | URL del inference-server local |
| `INFER_URL` | `http://localhost:8001/infer` | Endpoint de inferencia YOLO |

## Licencia

Proyecto academico - Trabajo Integrador SOA 2026.
