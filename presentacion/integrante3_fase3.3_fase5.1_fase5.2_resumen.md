# Integrante 3 -- Fase 3.3 (S3: GET /frames/{frameId}) + Fase 5.1 (S5.1: CRUD Personas) + Fase 5.2 (S5.2: Embeddings Faciales) + Resumen del Proyecto

---

## Fase 3.3: Endpoint S3 -- GET /api/frames/{frameId}

### Objetivo
Recuperar la imagen original de un fotograma almacenado en SeaweedFS. Soporta generacion opcional de thumbnail (miniatura) bajo demanda.

### Ubicacion en el codigo
- `src/api/routes/frames.py`
- `src/api/services/db_service.py`
- `src/api/services/seaweedfs_client.py`

### Input
```
GET /api/frames/a1b2c3d4-e5f6-7890-abcd-ef1234567890?thumbnail=true
```

| Parametro | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| frameId | path (string) | Si | UUID del fotograma |
| thumbnail | query (bool) | No | Si es true, genera miniatura 300x300 |

### Output
- **Content-Type**: `image/jpeg`
- **Body**: Binario de la imagen (JPEG)
- Si `thumbnail=true`: imagen redimensionada a 300x300px manteniendo aspecto

### Flujo Completo

```
    CLIENTE                    SERVIDOR                 POSTGRESQL    SEAWEEDFS
       |                          |                        |             |
       | GET /frames/{frameId}    |                        |             |
       | ?thumbnail=true          |                        |             |
       |------------------------->|                        |             |
       |                          |                        |             |
       |              1. Buscar frame por ID              |             |
       |                 SELECT image_url FROM frames      |             |
       |                 WHERE frame_id = %s  |----------->|             |
       |                          |<-----------| {image_url}|             |
       |                          |                        |             |
       |              2. Extraer fid de la URL              |             |
       |                 "https://.../seaweed/5,abc.jpg"   |             |
       |                 fid = "5,abc"                     |             |
       |                          |                        |             |
       |              3. Descargar de SeaweedFS            |             |
       |                 GET http://seaweed-volume:8080    |             |
       |                 /5,abc               |----------->|             |
       |                          |<-----------| JPEG bytes |             |
       |                          |                        |             |
       |              4. Si thumbnail=true:                 |             |
       |                 Abrir con PIL (Pillow)             |             |
       |                 Redimensionar a 300x300            |             |
       |                 Guardar como JPEG calidad 85       |             |
       |                          |                        |             |
       |              5. Retornar Response                 |             |
       |                 content-type: image/jpeg          |             |
       |<-------------------------|                        |             |
```

### Tecnologias

| Componente | Tecnologia | Rol |
|---|---|---|
| Web framework | FastAPI + `Response` | Retornar binario directamente |
| Procesamiento imagen | Pillow (PIL) | Abrir, redimensionar, guardar JPEG |
| Descarga SeaweedFS | `requests` | Obtener bytes desde Volume |
| Buffer | `io.BytesIO` | Manipular imagen en memoria (sin disco) |

### Detalles de Implementacion

```python
# Pseudocodigo reducido
frame = db_service.get_frame_by_id(frame_id)
if not frame:
    return 404

fid = extraer_fid(frame["image_url"])
image_bytes = seaweedfs_client.download_image(fid)

if thumbnail:
    img = Image.open(BytesIO(image_bytes))
    img.thumbnail((300, 300))
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    image_bytes = buffer.getvalue()

return Response(content=image_bytes, media_type="image/jpeg")
```

### Caracteristicas Clave

1. **Thumbnail bajo demanda**: No se almacenan miniaturas pre-generadas. Se genera en el momento solo si se solicita, ahorrando espacio de almacenamiento

2. **Streaming en memoria**: La imagen nunca se escribe en disco del servidor. Todo el proceso usa `BytesIO`

3. **Error 404**: Si el frame no existe en la base de datos, retorna 404 inmediatamente sin consultar a SeaweedFS

4. **Cache HTTP**: Se pueden agregar headers `Cache-Control` para que los clientes cacheen la imagen

### Ejemplo de Uso

```bash
# Descargar imagen original
curl -o frame.jpg https://bfts2026.mooo.com/api/frames/a1b2c3d4...?thumbnail=false

# Descargar miniatura
curl -o thumbnail.jpg https://bfts2026.mooo.com/api/frames/a1b2c3d4...?thumbnail=true

# Via cliente CLI
python3 client/setup_cliente.py frames get a1b2c3d4...
python3 client/setup_cliente.py frames get a1b2c3d4... --thumb
```

---

## Fase 5.1: Endpoints S5.1 -- CRUD de Personas

### Objetivo
Gestionar el registro de personas que seran utilizadas posteriormente para reconocimiento facial. Incluye creacion, consulta individual y listado.

### Ubicacion en el codigo
- `src/api/routes/persons.py`
- `src/api/services/db_service.py`
- `src/api/schemas/persons.py`

### Endpoints

#### POST /api/persons -- Crear Persona

```json
// Request
{
  "name": "Juan Perez",
  "email": "juan@example.com",
  "metadata": { "departamento": "ventas" }
}

// Response (201 Created)
{
  "person_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Juan Perez",
  "email": "juan@example.com",
  "metadata": { "departamento": "ventas" },
  "created_at": "2026-06-09T12:00:00Z",
  "updated_at": "2026-06-09T12:00:00Z"
}
```

#### GET /api/persons/{person_id} -- Obtener Persona

```json
// Response (200 OK)
{
  "person_id": "a1b2c3d4-...",
  "name": "Juan Perez",
  "email": "juan@example.com",
  "metadata": { "departamento": "ventas" },
  "created_at": "2026-06-09T12:00:00Z",
  "updated_at": "2026-06-09T12:00:00Z"
}

// Si no existe: 404 Not Found
```

#### GET /api/persons -- Listar Personas

```json
// Response (200 OK)
{
  "total": 7,
  "persons": [ { ... }, { ... } ]
}
```

### Tabla `persons`

| Columna | Tipo | Descripcion |
|---|---|---|
| person_id | UUID PK | Generado automaticamente con `gen_random_uuid()` |
| name | VARCHAR(255) NOT NULL | Nombre completo de la persona |
| email | VARCHAR(255) | Email (opcional) |
| metadata | JSONB | Datos arbitrarios adicionales |
| created_at | TIMESTAMP | Fecha de creacion |
| updated_at | TIMESTAMP | Fecha de actualizacion |

### Tecnologias
- FastAPI + Pydantic (validacion)
- psycopg2 (PostgreSQL)
- JSONB para metadata (flexible, sin esquema fijo)

---

## Fase 5.2: Endpoint S5.2 -- POST /api/persons/{personId}/embeddings

### Objetivo
Generar un embedding facial (vector numerico de 128 dimensiones) a partir de una foto de una persona usando DeepFace con modelo FaceNet. El vector se almacena en PostgreSQL usando la extension pgvector para busquedas por similitud posterior.

### Ubicacion en el codigo
- `src/face_api/routes/face.py`
- `src/face_api/services/face_service.py`
- `src/face_api/services/db_service.py`

**Importante**: Este endpoint corre en un microservicio separado (`face-api`) debido a las dependencias pesadas de DeepFace/TensorFlow.

### Input
```json
{
  "image_url": "https://bfts2026.mooo.com/seaweed/5,035e06afbe.jpg",
  "confidence": 0.95
}
```

### Output
```json
{
  "person_id": "uuid",
  "embedding_id": "uuid",
  "confidence": 0.95,
  "image_url": "https://bfts2026.mooo.com/seaweed/5,035e06afbe.jpg",
  "status": "generated",
  "message": "Embedding generado exitosamente"
}
```

### Flujo Completo

```
    CLIENTE                 FACE-API                POSTGRESQL    SEAWEEDFS

       | POST /persons/{id}   |                        |             |
       | /embeddings          |                        |             |
       | { "image_url": ... } |                        |             |
       |--------------------->|                        |             |
       |                      |                        |             |
       |       1. Verificar persona existe             |             |
       |          SELECT FROM persons   |------------->|             |
       |                      |<-----------| existe    |             |
       |                      |                        |             |
       |       2. Descargar imagen de SeaweedFS        |             |
       |          (convierte URL publica a interna)    |             |
       |          GET /{fid}              |----------->|             |
       |                      |<-----------| bytes     |             |
       |                      |                        |             |
       |       3. DeepFace.represent()                 |             |
       |          - Backend: Facenet  |   ---> [TensorFlow]         |
       |          - Retorna: embedding (128 floats),                  |
       |            facial_area (x, y, w, h),                        |
       |            confidence                                       |
       |                      |                        |             |
       |       4. Guardar en face_embeddings           |             |
       |          INSERT INTO face_embeddings          |             |
       |          (embedding_id, person_id,            |             |
       |           embedding::vector,                  |             |
       |           confidence, image_url) |----------->|             |
       |                      |<-----------| OK       |             |
       |                      |                        |             |
       |       5. Retornar EmbeddingResponse           |             |
       |<---------------------|                        |             |
```

### Procesamiento con DeepFace

```python
# Pseudocodigo de face_service.py
from deepface import DeepFace

# El metodo represent() extrae el embedding facial
result = DeepFace.represent(
    img_path="/tmp/face_api/temp.jpg",
    model_name="Facenet",       # Modelo de Google (128 dims)
    detector_backend="opencv",  # Detector de rostros
    enforce_detection=False     # No falla si no hay rostro
)

# Resultado tipico:
{
    "embedding": [0.023, -0.156, ..., 0.089],  # 128 floats
    "facial_area": {"x": 100, "y": 150, "w": 200, "h": 250},
    "face_confidence": 0.99
}
```

### Tabla `face_embeddings`

| Columna | Tipo | Descripcion |
|---|---|---|
| embedding_id | UUID PK | Identificador unico del embedding |
| person_id | UUID FK | Relacion con persons (CASCADE DELETE) |
| embedding | vector(128) NOT NULL | Vector facial de 128 dimensiones |
| confidence | FLOAT | Confianza de la deteccion facial |
| image_url | TEXT | URL de la imagen origen |
| created_at | TIMESTAMP | Fecha de creacion |

### Tecnologias

| Componente | Tecnologia | Rol |
|---|---|---|
| Face Recognition | DeepFace 0.0.80 | Framework de reconocimiento facial |
| Modelo | FaceNet (Google) | Genera embeddings de 128 dimensiones |
| Deep Learning | TensorFlow 2.15 | Backend de red neuronal |
| Detector rostros | OpenCV | Detecta rostros en la imagen |
| Vectores | pgvector | Almacena y consulta vectores en PostgreSQL |

### Requisitos del Microservicio face-api

Por las dependencias pesadas, este endpoint corre en un contenedor separado:

- `Dockerfile.face_api`: Imagen Python 3.11 con OpenCV, TensorFlow, DeepFace
- `requirements.face_api.txt`: dependencias adicionales
- Se comunica con la misma BD PostgreSQL y SeaweedFS que la API principal
- Accesible via Nginx bajo la misma ruta `/api/persons/{id}/embeddings`

### Uso desde Cliente

```bash
# 1. Crear persona
python3 client/setup_cliente.py persons create "Juan Perez"

# 2. Generar embedding (sube imagen a SeaweedFS, luego llama S5.2)
python3 client/setup_cliente.py faces embed <person_id> ~/foto_juan.jpg

# Verificar en BD
python3 client/setup_cliente.py persons get <person_id>
```

---

## Resumen del Proyecto

### Que construimos

Una **API de Deteccion Visual y Reconocimiento Facial** con arquitectura de microservicios (SOA) que permite:

1. **Deteccion de objetos** en imagenes usando modelos YOLO
2. **Almacenamiento persistente** de imagenes y metadatos
3. **Busqueda geografica y por clases** de detecciones
4. **Reconocimiento facial** usando DeepFace + FaceNet + pgvector

### Arquitectura Final

```
                    INTERNET (HTTPS)
                          |
                      [NGINX]
                     /   |    \
                    /    |     \
                   /     |      \
              [API]  [pgAdmin] [SeaweedFS]
                |         |     /       \
           [PostgreSQL]   | [Master] [Volume]
           + pgvector     |
                      [face-api]
                   (DeepFace + TF)
```

### Stack Tecnologico Completo

| Capa | Tecnologia |
|---|---|
| Proxy / SSL | Nginx + Let's Encrypt |
| API Principal | FastAPI (Python 3.11) |
| Face API | FastAPI + DeepFace + TensorFlow |
| Base de Datos | PostgreSQL 16 + pgvector |
| Almacenamiento | SeaweedFS (distribuido) |
| Contenedores | Docker Compose |
| Cliente CLI | Python (stdlib + Pillow) |
| Deteccion YOLO | Cliente local con Docker |

### Servicios Implementados

| # | Endpoint | Metodo | Descripcion | Fase |
|---|---|---|---|---|
| S1 | `/api/models` | GET | Listar modelos YOLO | Fase 2 |
| S2 | `/api/detections` | POST | Procesar y persistir detecciones | Fase 3.1 |
| S3 | `/api/frames/{id}` | GET | Obtener fotograma con thumbnail | Fase 3.3 |
| S4 | `/api/frames/search` | GET | Busqueda geografica y por clases | Fase 3.2 |
| S5.1 | `/api/persons` | POST/GET | CRUD de personas | Fase 5.1 |
| S5.2 | `/api/persons/{id}/embeddings` | POST | Generar embeddings faciales | Fase 5.2 |
| S5.3 | `/api/face-recognition` | POST | Reconocimiento facial | Fase 5.3 |

### Flujo de Uso Completo (Caso Tipico)

```
1. Cliente consulta modelos disponibles   (S1 - GET /models)
2. Cliente ejecuta YOLO localmente
3. Cliente sube resultado + imagen        (S2 - POST /detections)
4. Usuario busca detecciones por zona     (S4 - GET /frames/search)
5. Usuario descarga fotograma             (S3 - GET /frames/{id})
6. Admin registra persona facial           (S5.1 + S5.2)
7. Sistema reconoce persona en foto nueva (S5.3)
```

### Clave del Diseno: Procesamiento Distribuido

La inferencia YOLO (deteccion de objetos) corre **del lado del cliente** en su propia maquina. El servidor recibe solo los resultados. Esto:

- Evita saturar el servidor con procesamiento de IA
- Aprovecha GPUs de clientes si las tienen
- Escala naturalmente: mas clientes = mas capacidad de procesamiento

El reconocimiento facial (DeepFace) corre en un **microservicio separado** (`face-api`) porque TensorFlow/DeepFace son pesados y no deben contaminar la API principal.

### Decisiones Tecnicas Clave

1. **pgvector en lugar de FAISS**: Busqueda vectorial directamente en PostgreSQL, sin servicios externos
2. **SeaweedFS en lugar de S3**: Sistema de archivos distribuido ligero, facil de deployar con Docker
3. **FastAPI en lugar de Express/Spring**: Unifica el backend en Python (YOLO y face recognition son nativos de Python)
4. **Microservicio separado para facial**: DeepFace requiere TensorFlow (2GB+), mejor aislarlo
5. **Cliente thin**: El cliente CLI usa solo librerias stdlib + Pillow, sin dependencias pesadas
