# Fase 0: Correcciones Primera Entrega + Segunda Entrega

## Introduccion

Este documento detalla el trabajo pendiente para completar el proyecto segun la especificacion del Trabajo Integrador SOA 2026. Se divide en dos grandes bloques:

- **Fase 0**: Correcciones y mejoras de la Primera Entrega (anterior al 9/6/2026)
- **Fase 1**: Implementacion de la Segunda Entrega (punto 6 del espec: frontend, Keycloak, monitoreo)

---

# Fase 0: Correcciones de la Primera Entrega

## 0.1 Mejora del reconocimiento facial (CRITICO)

### Problema detectado

El reconocimiento facial fallo con Cristiano Ronaldo: se creo la persona y se genero un embedding desde `adna.jpg`, pero al intentar reconocer `ronaldo.jpg` (misma persona) no se encontro match ni siquiera con threshold 0.1.

Diagnostico parcial: `detector_backend="opencv"` (Haar Cascade) detecto el rostro con confianza 0.88 y sin ojos, lo que sugiere deteccion debil para fotos no-frontales o con distinta iluminacion.

### Solucion propuesta: multiples embeddings por persona

**Objetivo**: Almacenar N embeddings por persona (frente, perfil, distintas condiciones) para que el recognize tenga mas puntos de referencia.

### Tareas

#### 0.1.1 Modificar `faces embed` para aceptar directorio

**Archivos**: `client/setup_cliente.py`, `inference-server/main.py`

**Cambios en CLI**:
```python
# Actual: acepta 1 foto
faces_embed.add_argument("image", help="Ruta a la imagen con el rostro")

# Nuevo: acepta 1 foto O un directorio
faces_embed.add_argument("image_or_dir", help="Ruta a la imagen o directorio con multiples fotos")
```

**Cambios en inference-server**:
```python
# /face/embed debe aceptar y procesar multiples imagenes en un solo request
# O el CLI itera y llama N veces
```

**Flujo nuevo**:
1. CLI recibe path (archivo o directorio)
2. Si es directorio, lista todos los archivos de imagen dentro
3. Para cada imagen, llama a `/face/embed`
4. El inference-server genera embedding y reenvia a API
5. API persiste cada embedding como fila independiente en `face_embeddings`
6. CLI muestra resumen: X imagenes procesadas, Y embeddings validos, Z rechazados

#### 0.1.2 Almacenar multiples embeddings por persona

**Archivo**: `src/api/routes/face_proxy.py`

La BD ya lo soporta: `face_embeddings` tiene `person_id` sin unique constraint, permitiendo N filas por persona. No requiere cambios en el schema.

Validar:
```sql
SELECT person_id, COUNT(*) FROM face_embeddings GROUP BY person_id;
```

#### 0.1.3 Mejorar recognize para buscar contra TODOS los embeddings

**Archivo**: `src/api/routes/face_proxy.py:recognize_face()`

**Logica actual**:
```sql
SELECT fe.embedding <=> %s::vector AS distance
FROM face_embeddings fe
JOIN persons p ON p.person_id = fe.person_id
WHERE fe.embedding <=> %s::vector < %s
ORDER BY distance ASC
LIMIT 1
```

Esto ya busca contra TODOS los embeddings de TODAS las personas y devuelve el mejor match global. **No necesita cambios**. Lo que cambia es que ahora hay mas embeddings por persona para encontrar match.

**Mejora adicional**: si hay 3+ embeddings de la misma persona, se puede calcular el centroide (embedding promedio) y comparar contra el centroide en vez de contra cada embedding individual.

#### 0.1.4 Endpoint para promediar embeddings (opcional)

**Archivo**: `src/api/routes/face_proxy.py`

Nuevo endpoint:
```
POST /api/persons/{person_id}/embeddings/average
```

**Logica**:
1. Obtener todos los embeddings de `person_id`
2. Calcular promedio vectorial (centroide)
3. Opcional: reemplazar los N embeddings por el centroide
4. Devolver embedding_id del centroide

```python
@router.post("/persons/{person_id}/embeddings/average")
async def average_embeddings(person_id: str):
    # SELECT embedding FROM face_embeddings WHERE person_id = %s
    # Calcular media de todos los vectores
    # INSERT OR REPLACE con el embedding promedio
    # Opcional: DELETE de los originales
```

#### 0.1.5 Pruebas

Fotos a probar (Cristiano Ronaldo, Messi, Franco Colapinto):
- 3-5 fotos de cada persona con distintos angulos (frente, semi-perfil, perfil)
- 1 foto de cada persona con distinta iluminacion
- Fotos de personas NO registradas (deben dar `person_id: null`)
- Verificar que con 3+ embeddings el recognize funciona a threshold 0.5

Comandos de prueba:
```bash
# Subir directorio con multiples fotos
python3 setup_cliente.py faces embed <person_id> ~/fotos_messi/

# Reconocer
python3 setup_cliente.py faces recognize ~/messi_test.jpg --threshold 0.5
```

### Verificacion de calidad

Para cada embedding generado, verificar:
- `face_confidence` > 0.9 (ideal)
- `facial_area` contiene ojos detectados (left_eye, right_eye no None)
- Embedding tiene 128 dimensiones (Facenet)

---

## 0.2 Indice pgvector

### Problema

La tabla `face_embeddings` no tiene indice, lo que degrada performance al crecer (full scan en cada recognize).

### Solucion

Ejecutar via pgAdmin o psql en la BD remota:

```sql
CREATE INDEX IF NOT EXISTS idx_face_embeddings_vector
ON face_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

Verificar:
```sql
SELECT relname, relkind, amname
FROM pg_class c
JOIN pg_am a ON c.relam = a.oid
WHERE relname = 'idx_face_embeddings_vector';
```

Nota: IVFFLAT requiere rebuild periodico si los datos cambian mucho. Para el volumen del proyecto es suficiente.

---

## 0.3 Limpieza de Dockerfile.api

### Problema

`Dockerfile.api` instala dependencias que ya no se usan desde que refactorizamos el proxy facial via API en vez de conexion directa a BD.

### Archivo: `Dockerfile.api`

**Lineas a eliminar**:
```dockerfile
# Instalar dependencias del sistema necesarias para compilar psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
```

**Lineas a agregar**:
```dockerfile
# Instalar dependencias del sistema para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*
```

### Verificacion

Rebuildear y verificar que la API sigue funcionando:
```bash
docker compose up -d --build api
curl https://bfts2026.mooo.com/health
```

---

## 0.4 Mejor manejo de errores en CLI

### Problema

Cuando el modelo no existe en el contenedor, el CLI muestra un traceback de Python poco amigable.

### Archivo: `client/setup_cliente.py:cmd_infer()`

**Codigo actual** (lineas 390-391):
```python
with urllib.request.urlopen(req, timeout=120) as resp:
    infer_result = json.loads(resp.read().decode())
```

**Codigo nuevo**:
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

---

## 0.5 Docstring del script desactualizado

### Archivo: `client/setup_cliente.py`

**Linea 19 actual**:
```python
#   python3 setup_cliente.py persons create "Juan Perez"
```

**Corregir a**:
```python
#   python3 setup_cliente.py persons create "Juan" "Perez"
```

---

## 0.6 Mejora de inferencia: la API como orquestador

### Problema actual

Hoy el pipeline de inferencia funciona asi:
1. CLI envia imagen a inference-server local (`POST /infer`)
2. Inference-server devuelve detecciones
3. CLI arma payload y envia a API remota (`POST /api/detections`)
4. API persiste

Esto obliga al frontend a pasar por el inference-server local. El frontend web no puede hacer esto.

### Solucion: `POST /api/detections` acepta imagen cruda

#### 0.6.1 Modificar endpoint detections

**Archivo**: `src/api/routes/detections.py`

**Cambio**: Si el payload NO incluye `detections` (vacio o ausente), la API debe:
1. Guardar la imagen temporalmente
2. Llamar al inference-server via HTTP (post `http://inference-server:8000/infer`)
3. Obtener detecciones
4. Persistir todo
5. Devolver frameId + detecciones

**Nuevo schema de entrada**:
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
    ...
```

**Funcion auxiliar**:
```python
async def _run_inference(image_base64: str, model_id: str, confidence: float) -> list:
    """Envía imagen al inference-server y devuelve detecciones."""
    # Decodificar base64
    # Enviar POST a http://inference-server:8000/infer con form-data
    # Parsear respuesta
    # Devolver lista de detecciones en formato esperado
```

#### 0.6.2 inference-server accesible desde la API

Si la API corre en Docker, el inference-server debe estar en la misma red o ser accesible via URL configurable.

**Variable de entorno en API**:
```
INFERENCE_SERVER_URL=http://inference-server:8000
```

En `docker-compose.yml`:
```yaml
api:
  environment:
    - INFERENCE_SERVER_URL=http://yolo-inference-local:8000
  networks:
    - api-detection-net-local
```

#### 0.6.3 CLI simplificado

Nuevo comando:
```bash
python3 setup_cliente.py process foto.jpg --model pelotas.pt
```

Que hace:
1. Envia imagen a `POST /api/detections` (sin detecciones pre-computadas)
2. La API llama al inference-server internamente
3. API persiste y devuelve frameId + detecciones
4. CLI muestra resultados y descarga imagen anotada

Nota: el comando `infer` tradicional sigue existiendo para usuarios que quieran control local.

---

# Fase 1: Segunda Entrega

## 1.1 Seguridad con Keycloak

### Arquitectura

```
[Frontend/Navegador]  →  Keycloak (login)  →  JWT Token
                     →  API (valida JWT via middleware)  →  servicios
```

### Tareas

#### 1.1.1 Agregar Keycloak a docker-compose.yml

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

#### 1.1.2 Configurar realm y clientes

- Realm: `api-detection`
- Client: `api-backend` (confidential, service account)
- Roles: `admin`, `operator`, `viewer`
- Usuarios de prueba:
  - `admin` / `admin123` (rol admin)
  - `operator1` / `op123` (rol operator)
  - `viewer1` / `view123` (rol viewer)

#### 1.1.3 Middleware JWT en FastAPI

**Archivo**: `src/api/services/auth.py`

```python
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests

security = HTTPBearer()

KEYCLOAK_URL = "https://bfts2026.mooo.com/auth"
REALM = "api-detection"
JWKS_URL = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Validar JWT contra Keycloak
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="api-backend"
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
```

#### 1.1.4 Proteger endpoints

**Archivo**: `src/api/main.py`

```python
from .services.auth import verify_token

# Proteger todos los endpoints menos health y docs
app.include_router(models.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(detections.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(frames.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(persons.router, prefix="/api", dependencies=[Depends(verify_token)])
app.include_router(face_proxy.router, prefix="/api", dependencies=[Depends(verify_token)])
```

#### 1.1.5 Integracion facial con Keycloak (opcional)

Asociar `personId` con `sub` (user id) de Keycloak.
Cuando S5.3 reconoce una persona, verificar que esa persona tenga un usuario Keycloak activo.
Endpoint para login facial: `POST /api/auth/face`.

---

## 1.2 Frontend (UI)

### Tecnologia sugerida

React + Vite (o Vue 3 + Vite), empaquetado como contenedor Docker servido por Nginx.

### Estructura sugerida

```
frontend/
├── Dockerfile
├── nginx.conf
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

### Pantallas y APIs que consumen

| Pantalla | API | Metodo |
|---|---|---|
| Login | Keycloak OAuth2 | Redirect |
| Dashboard (cargar imagen) | `POST /api/detections` | Form con imagen + lat/lon + modelo |
| Ver detecciones | `GET /api/frames/{id}` | Imagen con bounding boxes overlay |
| Buscar fotogramas | `GET /api/frames/search` | Form con filtros + tabla de resultados |
| Gestionar personas | `GET /api/persons`, `POST /api/persons` | CRUD table |
| Subir fotos faciales | `POST /api/persons/{id}/embeddings` | Upload + progreso |
| Reconocimiento facial | `POST /api/face-recognition` | Upload foto + resultado |

### Endpoint nuevo necesario para frontend

Aca se integra la tarea **0.6**: `POST /api/detections` aceptando imagen cruda sin detecciones pre-computadas. Sin esto, el frontend no puede funcionar.

### Dockerfile para frontend

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

### Nginx (frontend + API)

```nginx
server {
    listen 80;
    
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass https://api:8000;
    }
}
```

---

## 1.3 Monitoreo (Telegraf + Grafana)

### Arquitectura

```
[FastAPI] → /metrics endpoint (prometheus format)
    → Telegraf (scrape)
    → InfluxDB (storage)
    → Grafana (dashboard)
```

### Tareas

#### 1.3.1 Agregar servicios a docker-compose.yml

```yaml
telegraf:
  image: telegraf:latest
  container_name: api_detection_telegraf
  volumes:
    - ./docker/telegraf.conf:/etc/telegraf/telegraf.conf:ro
  networks:
    - api-detection-net

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

#### 1.3.2 Telegraf config

**Archivo**: `docker/telegraf.conf`

```toml
[[inputs.prometheus]]
  urls = ["http://api:8000/metrics"]

[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8086"]
  token = "admin-token"
  organization = "soa"
  bucket = "metrics"
```

#### 1.3.3 Exponer metricas desde FastAPI

**Archivo**: `src/api/routes/metrics.py`

Usar `prometheus_client`:
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

**Middleware para contar requests**:
```python
@app.middleware("http")
async def count_requests(request: Request, call_next):
    REQUEST_COUNT.labels(endpoint=request.url.path, method=request.method).inc()
    response = await call_next(request)
    return response
```

#### 1.3.4 Dashboard Grafana

Paneles a incluir:
- Tiempo promedio de inferencia (histograma)
- Cantidad de requests por minuto (por endpoint)
- Ratio de errores vs exitos
- Reconocimientos faciales exitosos vs fallidos
- Embeddings generados por persona
- Uso de CPU/memoria de los contenedores (via Telegraf docker input)

Provisionar dashboard via JSON en `docker/grafana-dashboards/`.

---

## 1.4 Autenticacion biometrica (opcional)

### Endpoint

```
POST /api/auth/face
```

### Entrada
```json
{
    "image_base64": "...",
    "threshold": 0.8
}
```

### Proceso
1. Decodificar imagen
2. Llamar a `POST /api/face-recognition` con la imagen
3. Si se reconoce una persona (`personId != null`):
   - Buscar usuario Keycloak asociado a ese personId
   - Generar JWT token temporal
   - Devolver token + datos de usuario
4. Si no se reconoce:
   - Devolver 401 Unauthorized

### Salida (exito)
```json
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "person_id": "uuid",
    "nombre": "Juan",
    "apellido": "Perez"
}
```

### Salida (fallo)
```json
{
    "detail": "Rostro no reconocido"
}
```
Status: 401

---

## Dependencias entre tareas

```
0.1 Multiples embeddings
  └── 1.4 Auth biometrica (depende de S5.3 mejorado)

0.6 API orquestador
  └── 1.2 Frontend (depende de POST /api/detections con imagen cruda)

1.1 Keycloak
  ├── 1.2 Frontend (login)
  └── 1.4 Auth biometrica (asociar personId con usuario)

1.3 Monitoreo
  └── No depende de nada (independiente)
```

### Orden recomendado de implementacion

| Orden | Tarea | Esfuerzo |
|---|---|---|
| 1 | 0.1 Multiples embeddings | 2 dias |
| 2 | 0.6 API orquestador | 2 dias |
| 3 | 0.2 Indice pgvector | 10 min |
| 4 | 0.3 Limpieza Dockerfile | 30 min |
| 5 | 0.4 Errores CLI | 30 min |
| 6 | 0.5 Docstring | 5 min |
| 7 | 1.1 Keycloak | 3-4 dias |
| 8 | 1.2 Frontend | 5-7 dias |
| 9 | 1.3 Monitoreo | 2-3 dias |
| 10 | 1.4 Auth biometrica | 1-2 dias |

---

## Archivos afectados por cada tarea

| Tarea | Archivos |
|---|---|
| 0.1 | `client/setup_cliente.py`, `inference-server/main.py`, `src/api/routes/face_proxy.py` |
| 0.2 | `docker/init-db.sql` (agregar CREATE INDEX) |
| 0.3 | `Dockerfile.api` |
| 0.4 | `client/setup_cliente.py` |
| 0.5 | `client/setup_cliente.py` |
| 0.6 | `src/api/routes/detections.py`, `src/api/main.py`, `.env.example`, `docker-compose.yml` |
| 1.1 | `docker-compose.yml`, `src/api/services/auth.py`, `src/api/main.py`, `.env.example` |
| 1.2 | `frontend/` (nuevo directorio), `docker-compose.yml`, `docker/nginx.conf` |
| 1.3 | `docker-compose.yml`, `docker/telegraf.conf`, `src/api/routes/metrics.py`, `src/api/main.py` |
| 1.4 | `src/api/routes/auth.py`, `src/api/main.py` |
