# Distribucion de trabajo - Segunda entrega

## Equipo: 4 miembros

---

## Dependencias entre tareas

```
Timeline:
Semana 1                    Semana 2                 Semana 3
──────────────────────────────────────────────────────────────────
0.1 (embeddings)     ─────▶  (ayuda frontend)  ───▶  integracion
                              
0.6 (API orquest)    ─────▶  1.2 Frontend       ───▶  integracion
                              
1.1 (Keycloak)       ─────▶  1.3 Monitoreo      ───▶  integracion
                              
0.2+0.3+0.4+0.5     ─────▶  pruebas/1.4        ───▶  integracion
```

---

## Distribucion por roles

### Miembro A: Reconocimiento Facial (DeepFace + Face Proxy)

#### Tareas

| Tarea | Que hacer | Archivos |
|---|---|---|
| **0.1** Multiples embeddings | Modificar CLI + inference-server para aceptar directorio de fotos. Mejorar recognize contra multiples embeddings. | `client/setup_cliente.py`, `inference-server/main.py`, `src/api/routes/face_proxy.py` |
| **0.5** Docstring | Corregir linea 19 del CLI | `client/setup_cliente.py` |
| **1.4** Auth biometrica (si queda tiempo) | Endpoint `POST /api/auth/face` que usa S5.3 + Keycloak | `src/api/routes/auth.py`, `src/api/main.py` |

#### Detalle 0.1: Multiples embeddings por persona

**CLI** (`client/setup_cliente.py`):
- Modificar `faces_embed` para aceptar archivo O directorio
- Si es directorio, iterar sobre todos los archivos de imagen dentro
- Para cada imagen, llamar a `/face/embed`
- Mostrar resumen: X procesadas, Y embeddings validos, Z rechazados

```python
# Antes:
faces_embed.add_argument("image", help="Ruta a la imagen con el rostro")

# Despues:
faces_embed.add_argument("image_or_dir", help="Ruta a la imagen o directorio con multiples fotos")
```

**Inference-server** (`inference-server/main.py`):
- No requiere cambios mayores (ya acepta una imagen por request)
- El CLI itera y llama N veces

**Face proxy** (`src/api/routes/face_proxy.py`):
- La BD ya soporta N embeddings por persona
- El recognize ya busca contra TODOS los embeddings de TODAS las personas
- Opcional: endpoint `POST /api/persons/{id}/embeddings/average` para promediar

#### Detalle 0.5: Docstring

Linea 19 actual:
```python
#   python3 setup_cliente.py persons create "Juan Perez"
```

Corregir a:
```python
#   python3 setup_cliente.py persons create "Juan" "Perez"
```

#### Bloqueante: Nada. Arranca dia 1.

---

### Miembro B: Frontend (UI)

#### Tareas

| Tarea | Que hacer | Archivos |
|---|---|---|
| **0.2** Indice pgvector | Ejecutar CREATE INDEX en BD remota via pgAdmin o psql | SQL directo |
| **0.3** Limpieza Dockerfile | Sacar libpq-dev + gcc, agregar libglib2.0-0 + libgl1 | `Dockerfile.api` |
| **1.2** Frontend | Aplicacion React/Vue con login, carga de imagen, busqueda, CRUD personas, reconocimiento facial | `frontend/` (nuevo directorio) |

#### Detalle 0.2: Indice pgvector

Ejecutar en BD remota:
```sql
CREATE INDEX IF NOT EXISTS idx_face_embeddings_vector
ON face_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### Detalle 0.3: Limpieza Dockerfile.api

**Eliminar**:
```dockerfile
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
```

**Agregar**:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*
```

#### Detalle 1.2: Frontend

Tecnologia sugerida: React + Vite, empaquetado como contenedor Docker servido por Nginx.

**Estructura**:
```
frontend/
├── Dockerfile
├── nginx.conf
├── package.json
├── src/
│   ├── components/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── FrameViewer.jsx
│   │   ├── FrameSearch.jsx
│   │   ├── PersonManager.jsx
│   │   └── FaceRecognition.jsx
│   ├── services/
│   │   └── api.js
│   └── App.jsx
```

**Pantallas y APIs**:

| Pantalla | API | Metodo |
|---|---|---|
| Login | Keycloak OAuth2 | Redirect |
| Dashboard (cargar imagen) | `POST /api/detections` | Form con imagen + lat/lon + modelo |
| Ver detecciones | `GET /api/frames/{id}` | Imagen con bounding boxes overlay |
| Buscar fotogramas | `GET /api/frames/search` | Form con filtros + tabla |
| Gestionar personas | `GET /api/persons`, `POST /api/persons` | CRUD table |
| Subir fotos faciales | `POST /api/persons/{id}/embeddings` | Upload + progreso |
| Reconocimiento facial | `POST /api/face-recognition` | Upload foto + resultado |

**Dockerfile**:
```dockerfile
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Bloqueante**: 1.2 requiere que **0.6** (Miembro D) este listo para tener `POST /api/detections` que acepte imagen cruda. 
**Mientras tanto**: hacer 0.2, 0.3, y maquetar componentes visuales con datos mockeados.

---

### Miembro C: Seguridad + Monitoreo

#### Tareas

| Tarea | Que hacer | Archivos |
|---|---|---|
| **1.1** Keycloak | Agregar Keycloak a docker-compose, configurar realm/roles/clientes, implementar middleware JWT en FastAPI | `docker-compose.yml`, `src/api/services/auth.py`, `src/api/main.py`, `.env.example` |
| **1.3** Monitoreo | Agregar Telegraf + InfluxDB + Grafana, endpoint `/metrics`, dashboard Grafana | `docker-compose.yml`, `docker/telegraf.conf`, `src/api/routes/metrics.py`, `src/api/main.py` |

#### Detalle 1.1: Keycloak

**docker-compose.yml** - agregar servicio:
```yaml
keycloak:
  image: quay.io/keycloak/keycloak:latest
  container_name: api_detection_keycloak
  environment:
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://db:5432/keycloak_db
    KC_DB_USERNAME: ${POSTGRES_USER}
    KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
    KC_HOSTNAME: bfts2026.mooo.com
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: admin123
  ports:
    - "8080:8080"
  command: start
  networks:
    - api-detection-net
```

**Configuracion Keycloak**:
- Realm: `api-detection`
- Client: `api-backend` (confidential, service account)
- Roles: `admin`, `operator`, `viewer`
- Usuarios de prueba:
  - `admin` / `admin123` (rol admin)
  - `operator1` / `op123` (rol operator)
  - `viewer1` / `view123` (rol viewer)

**Middleware JWT** en `src/api/services/auth.py`:
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt, JWTError

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    token = credentials.credentials
    try:
        jwks_client = PyJWKClient(f"https://bfts2026.mooo.com/auth/realms/api-detection/protocol/openid-connect/certs")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["RS256"], audience="api-backend")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
```

**Proteger endpoints** en `src/api/main.py`:
```python
from .services.auth import verify_token

app.include_router(models.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(detections.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(frames.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(persons.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(face_proxy.router, prefix="/api", dependencies=[Depends(verify_token)])
```

Dejar `/health` y `/setup_cliente.py` sin autenticar.

#### Detalle 1.3: Monitoreo

**docker-compose.yml** - agregar servicios:
```yaml
telegraf:
  image: telegraf:latest
  container_name: api_detection_telegraf
  volumes:
    - ./docker/telegraf.conf:/etc/telegraf/telegraf.conf:ro
  networks:
    - api-detection-net
  depends_on:
    - api

influxdb:
  image: influxdb:2
  container_name: api_detection_influxdb
  environment:
    DOCKER_INFLUXDB_INIT_MODE: setup
    DOCKER_INFLUXDB_INIT_USERNAME: admin
    DOCKER_INFLUXDB_INIT_PASSWORD: admin123
    DOCKER_INFLUXDB_INIT_ORG: soa
    DOCKER_INFLUXDB_INIT_BUCKET: metrics
  volumes:
    - ./volumes/influxdb:/var/lib/influxdb2
  networks:
    - api-detection-net

grafana:
  image: grafana/grafana:latest
  container_name: api_detection_grafana
  environment:
    GF_SECURITY_ADMIN_PASSWORD: admin123
  volumes:
    - ./volumes/grafana:/var/lib/grafana
    - ./docker/grafana-dashboards:/etc/grafana/provisioning/dashboards
  ports:
    - "3000:3000"
  networks:
    - api-detection-net
```

**Endpoint `/metrics`** en `src/api/routes/metrics.py`:
```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

REQUEST_COUNT = Counter('api_requests_total', 'Total requests', ['endpoint', 'method'])
INFERENCE_TIME = Histogram('inference_time_ms', 'Tiempo de inferencia', buckets=[50, 100, 200, 500, 1000, 2000])
RECOGNITION_COUNT = Counter('face_recognition_total', 'Reconocimientos', ['result'])

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

**Middleware** en `src/api/main.py`:
```python
@app.middleware("http")
async def count_requests(request: Request, call_next):
    REQUEST_COUNT.labels(endpoint=request.url.path, method=request.method).inc()
    response = await call_next(request)
    return response
```

**Config Telegraf** en `docker/telegraf.conf`:
```toml
[[inputs.prometheus]]
  urls = ["http://api:8000/metrics"]

[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8086"]
  token = "admin-token"
  organization = "soa"
  bucket = "metrics"
```

**Dashboard Grafana** - paneles a incluir:
- Tiempo promedio de inferencia
- Cantidad de requests por minuto por endpoint
- Ratio de errores vs exitos
- Reconocimientos faciales exitosos vs fallidos
- Uso de CPU/memoria de los contenedores

#### Bloqueante: Nada. Arranca dia 1.

---

### Miembro D: Backend API + CLI + Integracion

#### Tareas

| Tarea | Que hacer | Archivos |
|---|---|---|
| **0.6** API orquestador | Modificar `POST /api/detections` para aceptar imagen cruda y delegar en inference-server | `src/api/routes/detections.py`, `src/api/main.py`, `.env.example` |
| **0.4** Errores CLI | Capturar HTTP 404 y mostrar mensaje claro | `client/setup_cliente.py` |
| **Integracion final** | Unir ramas, probar flujo completo, resolver conflictos, coordinar merge | Git |

#### Detalle 0.6: API como orquestador

Modificar `POST /api/detections` en `src/api/routes/detections.py`:

**Nuevo schema de entrada** (cuando no vienen detecciones pre-computadas):
```json
{
    "image_base64": "...",
    "model_id": "pelotas.pt",
    "latitude": -34.6,
    "longitude": -58.4,
    "confidence": 0.25,
    "metadata": {
        "camera_id": "frontend-web",
        "source": "frontend"
    }
}
```

**Logica**:
```python
@router.post("/detections")
async def create_detection(request: DetectionRequest):
    # Si no vienen detecciones, ejecutar inferencia via inference-server
    if not request.detections:
        detections = await _run_inference(
            image_base64=request.image_base64,
            model_id=request.model_id,
            confidence=request.confidence
        )
        request.detections = detections
    
    # Persistir (codigo existente)
    frame_id = str(uuid4())
    # ... guardar imagen, metadatos, detecciones ...
```

**Funcion auxiliar**:
```python
async def _run_inference(image_base64: str, model_id: str, confidence: float) -> list:
    """Envía imagen al inference-server y devuelve detecciones."""
    inference_url = os.environ.get("INFERENCE_SERVER_URL", "http://localhost:8001")
    # Decodificar base64 a bytes
    # Construir form-data multipart
    # POST a inference_url/infer
    # Parsear respuesta
    # Transformar al formato esperado por detections
    return detections_list
```

**Variable de entorno**: `INFERENCE_SERVER_URL=http://inference-server:8000`

#### Detalle 0.4: Errores CLI

En `client/setup_cliente.py:cmd_infer()` (linea 390):

```python
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        infer_result = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    if e.code == 404:
        print_error(f"Modelo '{model_name}' no encontrado en el contenedor local.")
        print_error("Modelos disponibles:")
        try:
            models_req = urllib.request.Request("http://localhost:8001/models")
            with urllib.request.urlopen(models_req) as mresp:
                models = json.loads(mresp.read().decode())
                for m in models:
                    print(f"    - {m}")
        except:
            print_error("(no se pudo obtener la lista de modelos)")
        print_error("Ejecuta 'python3 setup_cliente.py install' para descargar modelos.")
        sys.exit(1)
    else:
        print_error(f"Error {e.code}: {e.reason}")
        sys.exit(1)
```

#### Bloqueante: Nada. Arranca dia 1. Es la tarea mas critica porque es requerida por el frontend.

---

## Roadmap semanal

### Semana 1 (paralelo total)

| Dia | Miembro A | Miembro B | Miembro C | Miembro D |
|---|---|---|---|---|
| Lunes | 0.1 CLI multi-foto | 0.2 + 0.3 | 1.1 docker-compose Keycloak | 0.6 detections.py |
| Martes | 0.1 inference-server | Mockups frontend | 1.1 realm/roles | 0.6 conectar inference |
| Miercoles | 0.1 face_proxy | Maquetado UI | 1.1 middleware JWT | 0.6 pruebas |
| Jueves | 0.1 pruebas | Maquetado UI | 1.1 proteger endpoints | 0.4 errores CLI |
| Viernes | 0.5 + fixes | Componentes base | 1.3 metricas endpoint | Documentar API |

### Semana 2 (dependencias resueltas)

| Dia | Miembro A | Miembro B | Miembro C | Miembro D |
|---|---|---|---|---|
| Lunes | Ayuda frontend facial | 1.2 conectar API real | 1.3 Telegraf config | Pruebas 0.6 + 0.4 |
| Martes | Ayuda frontend | 1.2 busqueda | 1.3 Grafana dashboard | Pruebas integracion |
| Miercoles | 1.4 (si sobra tiempo) | 1.2 CRUD personas | 1.3 pruebas | Bugfixes |
| Jueves | 1.4 | 1.2 facial UI | Ayuda en lo que falte | Coordinar merge |
| Viernes | 1.4 | 1.2 pulido | Ayuda en lo que falte | Preparar deploy |

### Semana 3: Integracion y pruebas finales

| Dia | Actividad |
|---|---|
| Lunes | Merge de todas las ramas, resolver conflictos |
| Martes | Deploy en VM remota, probar flujo completo |
| Miercoles | Corregir bugs de integracion |
| Jueves | Preparar presentacion, documentacion |
| Viernes | Entrega |

---

## Ramas de Git propuestas

```
main
├── feat/embeddings-multiples    (Miembro A)
├── feat/frontend                (Miembro B)
├── feat/keycloak                (Miembro C, despues crear feat/monitoreo)
├── feat/monitoreo               (Miembro C, desde feat/keycloak)
└── feat/api-orquestador         (Miembro D)
```

**Orden de merge** (lo coordina Miembro D):

1. `feat/api-orquestador` → `main` (necesario para frontend)
2. `feat/embeddings-multiples` → `main`
3. `feat/keycloak` → `main`
4. `feat/frontend` → `main`
5. `feat/monitoreo` → `main`

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigacion |
|---|---|---|
| Conflictos en `docker-compose.yml` (varios miembros modifican) | Alta | Asignar a UN solo miembro (Miembro C) los cambios de infraestructura. Los demas NO tocan ese archivo |
| Frontend bloqueado por 0.6 (API orquestador) | Alta | Miembro B arranca con mockups y componentes visuales sin API real. Miembro D prioriza 0.6 en Semana 1 |
| Keycloak + JWT rompe pruebas con curl | Media | Dejar endpoint `/health` y `/setup_cliente.py` sin autenticar para verificacion basica |
| Miembro A termina antes | Baja | Que ayude en frontend (componente de reconocimiento facial) o auth biometrica |
| Conflictos de merge | Media | Miembro D coordina merges incrementalmente, no todo junto al final |

---

## Archivos afectados por cada miembro

| Miembro | Archivos que modifica | Archivos nuevos |
|---|---|---|
| A | `client/setup_cliente.py`, `inference-server/main.py`, `src/api/routes/face_proxy.py` | `src/api/routes/auth.py` |
| B | `Dockerfile.api`, `docker-compose.yml` | `frontend/` (directorio completo) |
| C | `docker-compose.yml`, `src/api/main.py`, `.env.example` | `src/api/services/auth.py`, `src/api/routes/metrics.py`, `docker/telegraf.conf` |
| D | `src/api/routes/detections.py`, `client/setup_cliente.py` | Ninguno |
