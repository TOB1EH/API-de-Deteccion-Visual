# Fase 5: Reconocimiento Facial (S5.1, S5.2, S5.3)

## Resumen de Implementacion

Se implemento el subsistema completo de reconocimiento facial utilizando una arquitectura de **microservicios** dentro del mismo Docker Compose. Se creo un servicio separado `face-api` que ejecuta **DeepFace** para generacion de embeddings y busqueda por similitud via **pgvector**.

---

## Arquitectura de Microservicios

```
docker-compose.local.yml
├── db           (PostgreSQL 16 + pgvector)
├── seaweed-master (SeaweedFS coordinador)
├── seaweed-volume (SeaweedFS almacenamiento)
├── nginx        (Proxy reverso - rutea segun endpoint)
├── pgadmin      (Gestion visual de BD)
├── api          (FastAPI - S1, S2, S3, S4, S5.1 CRUD)
└── face-api     (FastAPI + DeepFace - S5.2 y S5.3)  ← NUEVO
```

### Ruteo Nginx

Nginx redirige segun el endpoint:

| Ruta | Destino | Servicio |
|---|---|---|
| `/api/persons` (GET/POST) | `api:8000` | CRUD basico de personas |
| `/api/persons/{id}/embeddings` | `face-api:8000` | DeepFace genera embedding |
| `/api/face-recognition` | `face-api:8000` | Busqueda en pgvector |
| `/api/*` (resto) | `api:8000` | Endpoints S1-S4 existentes |

---

## Endpoints Implementados

### S5.1 - Gestion de Personas (CRUD basico)

```
POST /api/persons              → Crear persona
GET  /api/persons              → Listar todas las personas
GET  /api/persons/{personId}   → Obtener persona por ID
```

**Ejemplo de creacion:**
```json
// POST /api/persons
{
    "name": "Messi",
    "email": "messi@test.com"
}

// Respuesta:
{
    "person_id": "d13c8cb5-...",
    "name": "Messi",
    "created_at": "2026-06-02T21:34:00Z"
}
```

### S5.2 - Generacion de Embeddings Faciales

```
POST /api/persons/{personId}/embeddings
```

**Ejemplo:**
```json
// Request
{
    "image_url": "http://localhost/seaweed/7,12bf82df02.jpg"
}

// Respuesta
{
    "person_id": "d13c8cb5-...",
    "embedding_id": "0fb52e6c-...",
    "confidence": 1.0,
    "status": "generated",
    "message": "Embedding generado exitosamente para Messi"
}
```

### S5.3 - Reconocimiento Facial

```
POST /api/face-recognition
```

**Ejemplo:**
```json
// Request
{
    "image_url": "http://localhost/seaweed/3,1056005c6e.jpg",
    "threshold": 0.5
}

// Respuesta (reconocido)
{
    "recognized": true,
    "matches": [
        {
            "person_id": "0af04092-...",
            "name": "Colapinto",
            "distance": 0.0,
            "confidence": 1.0
        }
    ]
}
```

---

## Base de Datos (pgvector)

### Tablas nuevas agregadas a `docker/init-db.sql`

```sql
-- Tabla: persons
CREATE TABLE persons (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla: face_embeddings (vectores faciales 128D)
CREATE TABLE face_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding vector(128) NOT NULL,
    confidence FLOAT CHECK (confidence >= 0.0 AND confidence <= 1.0),
    image_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indice IVFFLAT para busqueda vectorial aproximada
CREATE INDEX idx_face_embeddings_ivfflat
    ON face_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

## Microservicio face-api

### Archivos nuevos creados

| Archivo | Proposito |
|---|---|
| `Dockerfile.face_api` | Imagen Docker con DeepFace + TensorFlow |
| `requirements.face_api.txt` | Dependencias (deepface, tensorflow, etc.) |
| `src/face_api/__init__.py` | Package init |
| `src/face_api/main.py` | App FastAPI independiente |
| `src/face_api/routes/face.py` | Endpoints S5.2 y S5.3 |
| `src/face_api/schemas/face.py` | Modelos Pydantic |
| `src/face_api/services/db_service.py` | Conexion a PostgreSQL + pgvector |
| `src/face_api/services/face_service.py` | Logica DeepFace (embeddings) |

### Dependencias principales

- **deepface==0.0.80**: Libreria de reconocimiento facial
- **tensorflow==2.15.0**: Backend de redes neuronales
- **Backend Facenet**: Modelo de embeddings de 128 dimensiones

---

## Script de Carga Automatica

### `scripts/upload_facial_images.py`

Script que automatiza todo el proceso:

1. Lee imagenes JPG/PNG desde `~/Escritorio/famous_photos/`
2. Sube cada imagen a SeaweedFS
3. Crea una persona en BD
4. Genera el embedding facial con DeepFace
5. Guarda el embedding en pgvector

**Uso:**
```bash
python3 scripts/upload_facial_images.py           # Ejecutar carga real
python3 scripts/upload_facial_images.py --dry-run  # Simular sin cambios
```

---

## Datos de Prueba Cargados

| Persona | Embedding ID | Confianza |
|---|---|---|
| Colapinto | `14dd0a4f-...` | 1.0 |
| Colapinto2 | `a5481ece-...` | 1.0 |
| Messi | `0fb52e6c-...` | 1.0 |
| Ozzy | `75a0030c-...` | 1.0 |
| Ronaldo | `603c85f7-...` | 1.0 |

---

## Como Probar Manualmente

```bash
# 1. Crear persona
curl -X POST http://localhost/api/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Persona Test"}'

# 2. Listar personas
curl http://localhost/api/persons

# 3. Generar embedding (reemplazar ID e IMAGE_URL)
curl -X POST http://localhost/api/persons/{PERSON_ID}/embeddings \
  -H "Content-Type: application/json" \
  -d '{"image_url": "http://localhost/seaweed/{FID}.jpg"}'

# 4. Reconocimiento facial
curl -X POST http://localhost/api/face-recognition \
  -H "Content-Type: application/json" \
  -d '{"image_url": "http://localhost/seaweed/{FID}.jpg", "threshold": 0.5}'
```

---

## Notas Tecnicas

- **DeepFace** corre en modo CPU (sin GPU). En hardware limitado (2 cores, 3.4GB RAM) cada embedding tarda ~2-5 segundos.
- **Indice IVFFLAT** optimizado para busqueda aproximada con `lists=100`. Adecuado para menos de 10,000 embeddings.
- **Distancia cosine** usada como metrica de similitud. Un valor de 0.0 = identico, 1.0 = completamente diferente.
- El modelo **Facenet** se descarga automaticamente (~90MB) en el primer uso desde GitHub.
- Se agrego DNS `8.8.8.8` al contenedor face-api para permitir descarga de modelos.
