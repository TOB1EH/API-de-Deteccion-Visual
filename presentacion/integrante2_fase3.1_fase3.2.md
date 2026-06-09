# Integrante 2 -- Fase 3.1 (S2: POST /detections) + Fase 3.2 (S4: GET /frames/search)

---

## Fase 3.1: Endpoint S2 -- POST /api/detections

### Objetivo
Recibir resultados de deteccion desde el cliente (imagen + bounding boxes + geolocalizacion), persistir la imagen en SeaweedFS, guardar metadatos y detecciones en PostgreSQL, y retornar un `frame_id` unico.

### Ubicacion en el codigo
- `src/api/routes/detections.py`
- `src/api/schemas/detections.py`
- `src/api/services/seaweedfs_client.py`
- `src/api/services/db_service.py`

### Input
```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
  "model_id": "yolo11n.pt",
  "latitude": -34.6037,
  "longitude": -58.3816,
  "detections": [
    {
      "class_name": "person",
      "class_id": 0,
      "confidence": 0.95,
      "bbox": {
        "x_min": 100, "y_min": 200,
        "x_max": 300, "y_max": 400
      }
    }
  ],
  "metadata": {
    "camera_id": "cam-001",
    "source": "setup-cliente",
    "timestamp": "2026-06-09T12:00:00Z"
  }
}
```

### Output
```json
{
  "frame_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "image_url": "https://bfts2026.mooo.com/seaweed/5,035e06afbe.jpg",
  "detections_count": 3,
  "status": "processed",
  "message": "Se procesaron 3 detecciones"
}
```

### Flujo Completo (Paso a Paso)

```
    CLIENTE                    SERVIDOR
       |                          |
       | POST /api/detections     |
       | (imagen base64 +         |
       |  detecciones + lat/lon)  |
       |------------------------->|
       |                          |
       |              1. Generar frame_id (UUID v4)
       |              2. Decodificar base64 a binario
       |              3. Limpiar prefijo "data:image/..."
       |                          |
       |              4. Subir imagen a SeaweedFS:
       |                 POST http://seaweed-master:9333/submit
       |                 (multipart/form-data)
       |                          |
       |                 +------> SeaweedFS Master
       |                 |       Retorna: { "fid": "5,035e06afbe" }
       |                 |       Construye URL publica
       |                 |       https://.../seaweed/5,035e06afbe.jpg
       |                 |                          |
       |              5. Insertar en tabla `frames`:
       |                 frame_id, model_id,
       |                 latitude, longitude,
       |                 image_url, detections_count,
       |                 camera_id, source
       |                          |
       |              6. Por cada deteccion:
       |                 Generar detection_id (UUID v4)
       |                 Insertar en tabla `detections`
       |                          |
       |              7. Retornar DetectionResponse
       |<-------------------------|
```

### Tecnologias y Librerias

| Componente | Tecnologia | Rol |
|---|---|---|
| Recepcion | FastAPI + Pydantic | Validar request, serializar response |
| Base64 | `base64` (stdlib) | Decodificar imagen del payload |
| HTTP | `requests` | Subir imagen a SeaweedFS |
| PostgreSQL | `psycopg2` | Insertar frame + detecciones |
| UUID | `uuid` (stdlib) | Generar identificadores unicos |

### Esquema de Base de Datos Involucrado

#### Tabla `frames`
| Columna | Tipo | Descripcion |
|---|---|---|
| frame_id | VARCHAR(36) PK | UUID v4 unico |
| model_id | VARCHAR(255) | Modelo YOLO usado (ej: yolo11n.pt) |
| latitude | FLOAT8 | Geolocalizacion (obligatorio) |
| longitude | FLOAT8 | Geolocalizacion (obligatorio) |
| image_url | TEXT | URL publica en SeaweedFS |
| detections_count | INT | Cantidad de objetos detectados |
| camera_id | VARCHAR(255) | Identificador de camara opcional |
| source | VARCHAR(255) | Origen del fotograma |
| created_at | TIMESTAMP | Fecha de creacion |
| updated_at | TIMESTAMP | Fecha de actualizacion |

#### Tabla `detections`
| Columna | Tipo | Descripcion |
|---|---|---|
| detection_id | VARCHAR(36) PK | UUID v4 unico |
| frame_id | VARCHAR(36) FK | Relacion con frames (CASCADE DELETE) |
| class_name | VARCHAR(255) | Clase COCO (person, car, dog...) |
| class_id | INT | ID numerico de la clase COCO |
| confidence | FLOAT8 | Confianza del modelo (0.0 a 1.0) |
| bbox_x_min | INT | Coordenada X minima del bounding box |
| bbox_y_min | INT | Coordenada Y minima del bounding box |
| bbox_x_max | INT | Coordenada X maxima del bounding box |
| bbox_y_max | INT | Coordenada Y maxima del bounding box |
| created_at | TIMESTAMP | Fecha de creacion |

### Interaccion con SeaweedFS

La subida a SeaweedFS se realiza enviando un POST multipart al **Master**:

```python
# Pseudocodigo de seaweedfs_client.py
response = requests.post(
    "http://seaweed-master:9333/submit",
    files={"file": (filename, image_bytes, "image/jpeg")}
)
result = response.json()
fid = result["fid"]  # ej: "5,035e06afbe"
public_url = f"{SEAWEED_PUBLIC_URL}/{fid}.jpg"
```

El Master redirige automaticamente la imagen a un Volume disponible.

### Procesamiento Distribuido

El cliente (`setup_cliente.py`) ejecuta la inferencia YOLO localmente en su propia PC usando un contenedor Docker de inferencia. Luego sube **solo los resultados** (no ejecuta YOLO en el servidor). Esto:

- Reduce la carga computacional del servidor
- Permite que clientes con GPU propia procesen mas rapido
- Escala horizontalmente: cada cliente aporta su propio poder de computo

---

## Fase 3.2: Endpoint S4 -- GET /api/frames/search

### Objetivo
Buscar y filtrar fotogramas almacenados usando criterios geograficos (latitud/longitud) y por clases de objetos detectados. Soporta paginacion.

### Ubicacion en el codigo
- `src/api/routes/frames.py` (funcion `search_frames_endpoint`)
- `src/api/services/db_service.py` (funcion `search_frames`)

### Input (Query Parameters)
```
GET /api/frames/search?clases=person,car&lat_min=-34.7&lat_max=-34.5&lon_min=-58.5&lon_max=-58.3&limit=10&offset=0
```

| Parametro | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| clases | string | No | Clases separadas por coma (person, car, dog...) |
| lat_min / lat_max | float | No | Rango de latitud |
| lon_min / lon_max | float | No | Rango de longitud |
| limit | int (1-200) | No | Resultados por pagina (default 50) |
| offset | int | No | Desplazamiento (default 0) |

### Output
```json
{
  "total": 150,
  "frames": [
    {
      "frame_id": "uuid",
      "model_id": "yolo11n.pt",
      "latitude": -34.6037,
      "longitude": -58.3816,
      "image_url": "https://bfts2026.mooo.com/seaweed/5,035e06afbe.jpg",
      "detections_count": 5,
      "metadata": {
        "camera_id": "cam-001",
        "source": "setup-cliente"
      },
      "created_at": "2026-06-09T12:00:00Z",
      "detections": [
        {
          "detection_id": "uuid",
          "class_name": "person",
          "class_id": 0,
          "confidence": 0.95,
          "bbox": {
            "x_min": 100, "y_min": 200,
            "x_max": 300, "y_max": 400
          }
        }
      ]
    }
  ]
}
```

### Logica Interna

```
    CLIENTE                    SERVIDOR                  POSTGRESQL
       |                          |                          |
       | GET /frames/search       |                          |
       | ?clases=person,car       |                          |
       | &lat_min=-34.7           |                          |
       | &lat_max=-34.5           |                          |
       |------------------------->|                          |
       |                          |                          |
       |              1. Construir WHERE dinamico            |
       |                 - Si clases: subquery               |
       |                   frame_id IN (SELECT DISTINCT      |
       |                   frame_id FROM detections          |
       |                   WHERE class_name IN (...))        |
       |                 - Si lat/lon: filtro de rango       |
       |                   latitude BETWEEN lat_min AND max  |
       |                          |                          |
       |              2. COUNT(*) con filtros  |------------>| (total)
       |                          |<------------| 150        |
       |                          |                          |
       |              3. SELECT principal                    |
       |                 con LIMIT/OFFSET     |------------>|
       |                          |<------------| frames     |
       |                          |                          |
       |              4. Por cada frame:                     |
       |                 SELECT detections   |------------>|
       |                          |<------------| dets[]    |
       |                          |                          |
       |              5. Armar FrameSearchResponse           |
       |<-------------------------|                          |
```

### Tecnologias

| Componente | Tecnologia | Rol |
|---|---|---|
| Query params | FastAPI (Query) | Parsear y validar parametros opcionales |
| Consulta dinamica | `psycopg2` + SQL construido | WHERE clauses condicionales |
| Cursor | `RealDictCursor` | Retorna resultados como diccionarios |
| Paginacion | `LIMIT` / `OFFSET` | Control de volumen de datos |

### Caracteristicas Clave

1. **Filtros combinables**: Se pueden aplicar filtros de clase Y geograficos simultaneamente, o solo uno, o ninguno (lista completa)

2. **Paginacion**: Controlada por `limit` y `offset` para evitar respuestas masivas

3. **Subquery por clases**: Para filtrar por clases usa `IN (SELECT DISTINCT frame_id FROM detections WHERE class_name IN (...))` -- esto encuentra todos los frames que tienen al menos una deteccion de las clases solicitadas

4. **Total count**: Retorna `total` (con los mismos filtros) para que el cliente pueda implementar paginacion del lado frontend

5. **Detecciones embebidas**: Cada frame en la respuesta incluye sus detecciones (no es necesario hacer request separado)

### Ejemplos de Uso

```bash
# Todos los frames
GET /api/frames/search

# Solo frames con personas y autos
GET /api/frames/search?clases=person,car

# Frames en un area geografica especifica
GET /api/frames/search?lat_min=-34.7&lat_max=-34.5&lon_min=-58.5&lon_max=-58.3

# Paginacion: segunda pagina, 20 resultados
GET /api/frames/search?limit=20&offset=20

# Combinado
GET /api/frames/search?clases=person&lat_min=-34.7&lat_max=-34.5&limit=5
```

### Consideraciones de Rendimiento

- Indices en `frames.created_at DESC`, `frames.model_id`, y `(latitude, longitude)` aceleran las consultas de rango
- Indice en `detections.frame_id` y `detections.class_id` aceleran el filtro por clases
- El `LIMIT` maximo es 200 para evitar respuestas demasiado grandes
- Cada frame incluye sus detecciones, lo que agrega N consultas adicionales (1 por frame), pero simplifica el consumo desde el cliente
