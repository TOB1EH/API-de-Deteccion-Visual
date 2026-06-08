# Informe de Progreso: Fase 3 - Implementacion Miembro C (S3, S4, S5.1)

**Rol:** Miembro C - Backend Data (Busqueda, Recuperacion de Imagenes e Identidad)
**Fecha:** 2/6/2026
**Estado:** COMPLETADO

---

## Resumen

Se implementaron los endpoints S3, S4 y S5.1 correspondientes al Miembro C del proyecto SOA. La infraestructura (PostgreSQL + pgvector, SeaweedFS, Nginx, Docker) ya estaba operativa por el Miembro A, y los endpoints S1/S2 ya habian sido implementados por el Miembro B.

---

## Endpoints Implementados

| ID | Metodo | Ruta | Descripcion |
|----|--------|------|-------------|
| S3 | GET | `/api/frames/{frameId}?thumbnail=true` | Obtiene fotograma como binario (image/jpeg). `thumbnail=true` redimensiona en memoria con Pillow |
| S4 | GET | `/api/frames/search?clases=&lat_min=&lat_max=&lon_min=&lon_max=` | Busqueda con filtros por clase de objeto y rango geografico |
| S5.1 | POST | `/api/persons` | Crea persona con nombre, apellido, email (obligatorios) y extra (JSON libre) |
| S5.1 | GET | `/api/persons/{personId}` | Obtiene persona por ID |
| S5.1 | GET | `/api/persons` | Lista todas las personas |

---

## Archivos Creados

| Archivo | Descripcion |
|---------|-------------|
| `src/api/routes/frames.py` | Rutas S3 y S4: GET `/frames/{frame_id}` y GET `/frames/search` |
| `src/api/routes/persons.py` | Rutas S5.1: CRUD de personas |
| `src/api/schemas/person.py` | Schemas Pydantic: PersonCreate, PersonResponse, PersonListResponse |
| `src/api/schemas/frame.py` | Schemas Pydantic: FrameSearchResult, FrameSearchResponse, DetectionInfo |
| `scripts/seed.py` | Generador de datos de prueba (5 imagenes sinteticas + metadatos + personas) |

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `docker/init-db.sql` | Agregadas tablas `persons` y `embeddings` con indices |
| `requirements.txt` | Agregada dependencia Pillow para thumbnails |
| `src/api/main.py` | Registrados los routers `frames` y `persons` |
| `src/api/routes/__init__.py` | Exportados los modulos `frames` y `persons` |
| `src/api/services/db_service.py` | Agregados metodos: get_frame_by_id, search_frames, count_frames, create_person, get_person_by_id, list_persons, count_persons |
| `src/api/services/seaweedfs_client.py` | Mejorado download_image (file_name opcional) |

---

## Base de Datos: Nuevas Tablas

### Tabla `persons`
| Columna | Tipo | Descripcion |
|---------|------|-------------|
| person_id | VARCHAR(36) PK | UUID v4 |
| nombre | VARCHAR(255) NOT NULL | Nombre de pila |
| apellido | VARCHAR(255) NOT NULL | Apellido |
| email | VARCHAR(255) NOT NULL UNIQUE | Correo electronico |
| extra | JSONB DEFAULT {} | Campos adicionales libres |
| created_at | TIMESTAMP | Auditoria |
| updated_at | TIMESTAMP | Auditoria |

### Tabla `embeddings` (preparada para Fase 5.2/5.3)
| Columna | Tipo | Descripcion |
|---------|------|-------------|
| embedding_id | VARCHAR(36) PK | UUID v4 |
| person_id | VARCHAR(36) FK | Referencia a persons (CASCADE) |
| vector | vector(128) | Embedding facial (pgvector) |
| image_url | TEXT | URL de la imagen del rostro |
| created_at | TIMESTAMP | Auditoria |

---

## Datos de Prueba (Seed)

El script `scripts/seed.py` genera automaticamente:

- **5 imagenes sinteticas** con Pillow (colores, rectangulos, texto con nombre de ciudad)
- **5 frames** en PostgreSQL con coordenadas de ciudades argentinas:
  - Buenos Aires (-34.6037, -58.3816)
  - Cordoba (-31.4201, -64.1888)
  - Rosario (-32.9468, -60.6393)
  - Mendoza (-32.8895, -68.8458)
  - Bariloche (-41.1335, -71.3103)
- **14 detecciones** (2-4 por frame) de clases COCO: person, car, dog, cat, bicycle
- **3 personas** de prueba con datos ficticios

Las imagenes se almacenan en SeaweedFS y los metadatos en PostgreSQL.

---

---

## Guia de Ejecucion desde Cero

### Prerequisitos
- Docker y Docker Compose instalados
- Python 3.10+ con pip
- Puertos 80, 5432, 8000, 8090, 9333 disponibles

### 1. Clonar y configurar

```bash
git clone <url-del-repo>
cd API-de-Deteccion-Visual
cp .env.example .env
# Editar .env segun el entorno (para local, dejar defaults o ajustar)
```

### 2. Construir y levantar servicios

```bash
# Construir la imagen de la API (incluye Pillow para thumbnails)
docker compose -f docker-compose.local.yml build

# Levantar todos los servicios (PostgreSQL, SeaweedFS, Nginx, API, pgAdmin)
docker compose -f docker-compose.local.yml up -d

# Verificar que todos esten "Up"
docker compose -f docker-compose.local.yml ps
```

### 3. Verificar que la BD tenga las tablas

Las tablas `frames` y `detections` se crean automaticamente via `docker/init-db.sql`.  
Las tablas `persons` y `embeddings` (agregadas en esta fase) tambien se crean automaticamente al iniciar PostgreSQL.

Si los contenedores ya estaban corriendo antes de agregar las nuevas tablas, ejecutar:

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://usuario_bd:password_seguro_bd@localhost:5432/nombre_bd')
cursor = conn.cursor()
# Crear tabla persons
cursor.execute('''CREATE TABLE IF NOT EXISTS persons (
    person_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    nombre VARCHAR(255) NOT NULL,
    apellido VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    extra JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)''')
# Crear tabla embeddings
cursor.execute('''CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    person_id VARCHAR(36) NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
    vector vector(128),
    image_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)''')
conn.commit()
cursor.close()
conn.close()
print('Tablas persons y embeddings listas')
"
```

### 4. Sembrar datos de prueba

Instalar dependencias necesarias en el host:

```bash
pip install Pillow psycopg2-binary requests
```

Ejecutar el script de siembra:

```bash
python3 scripts/seed.py \
  --db-url "postgresql://usuario_bd:password_seguro_bd@localhost:5432/nombre_bd" \
  --seaweed-url "http://localhost:8090" \
  --seaweed-master-url "http://localhost:9333" \
  --seaweed-public-url "http://localhost/seaweed" \
  --force
```

Esto genera:
- 5 imagenes sinteticas (Buenos Aires, Cordoba, Rosario, Mendoza, Bariloche)
- 5 frames en PostgreSQL vinculados a las imagenes en SeaweedFS
- 14 detecciones con clases COCO (person, car, dog, cat, bicycle)
- 3 personas de prueba

### 5. Verificar que todo funciona

#### Opcion A: Tests automatizados rapidos

```bash
python3 -c "
import requests, json

BASE = 'http://localhost/api'
passed = 0; total = 0

def test(name, condition, detail):
    global passed, total; total += 1
    if condition: passed += 1
    print(f'  {\"PASS\" if condition else \"FAIL\"} {name}: {detail}')

print('=== VERIFICACION DE ENDPOINTS ===')

# Health check
r = requests.get('http://localhost/')
test('GET /', r.status_code == 200, str(r.status_code))

# S1 - Modelos
r = requests.get(f'{BASE}/models')
test('S1 GET /models', r.status_code == 200 and r.json()['total'] > 0, f'{r.status_code} total={r.json()[\"total\"]}')

# S3 - Frame (usar frame_id del seed)
r = requests.get(f'{BASE}/frames')
frames = r.json().get('frames', [])
if frames:
    fid = frames[0]['frame_id']
    r = requests.get(f'{BASE}/frames/{fid}')
    test('S3 GET /frames/{id}', r.status_code == 200 and r.headers['Content-Type'] == 'image/jpeg', f'{r.status_code} size={len(r.content)}b')
    r = requests.get(f'{BASE}/frames/{fid}', params={'thumbnail': 'true'})
    test('S3 GET /frames/{id}?thumbnail=true', r.status_code == 200 and len(r.content) < 5000, f'{r.status_code} size={len(r.content)}b')

# S4 - Search
r = requests.get(f'{BASE}/frames/search')
test('S4 GET /frames/search', r.status_code == 200 and r.json()['total'] > 0, f'{r.status_code} total={r.json()[\"total\"]}')

# S4 - Search filtrado
r = requests.get(f'{BASE}/frames/search', params={'clases': 'person', 'lat_min': -35, 'lat_max': -30})
test('S4 GET /frames/search filtrado', r.status_code == 200 and r.json()['total'] > 0, f'{r.status_code} total={r.json()[\"total\"]}')

# S5.1 - Crear persona
r = requests.post(f'{BASE}/persons', json={'nombre':'Test','apellido':'User','email':'t@u.com','extra':{}})
test('S5.1 POST /persons', r.status_code == 201 and 'person_id' in r.json(), f'{r.status_code}')
pid = r.json().get('person_id','')

# S5.1 - Obtener persona
if pid:
    r = requests.get(f'{BASE}/persons/{pid}')
    test('S5.1 GET /persons/{id}', r.status_code == 200, f'{r.status_code}')

# S5.1 - Listar personas
r = requests.get(f'{BASE}/persons')
test('S5.1 GET /persons lista', r.status_code == 200 and r.json()['total'] > 0, f'{r.status_code} total={r.json()[\"total\"]}')

print(f'\\nResultados: {passed}/{total} tests pasados')
"

```

#### Opcion B: Swagger UI
Abrir en el navegador: `http://localhost/api/docs`

#### Opcion C: Pruebas con curl

```bash
# Obtener lista de frames
curl -s http://localhost/api/frames/search | python3 -m json.tool

# Descargar imagen de un frame (reemplazar FRAME_ID)
curl -s -o frame.jpg http://localhost/api/frames/FRAME_ID

# Descargar thumbnail
curl -s -o thumb.jpg "http://localhost/api/frames/FRAME_ID?thumbnail=true"

# Filtrar frames por clase y ubicacion
curl -s "http://localhost/api/frames/search?clases=person,car&lat_min=-35&lat_max=-30" | python3 -m json.tool

# Crear persona
curl -s -X POST http://localhost/api/persons \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Juan","apellido":"Perez","email":"juan@test.com","extra":{"edad":30,"ciudad":"Buenos Aires"}}' | python3 -m json.tool

# Listar personas
curl -s http://localhost/api/persons | python3 -m json.tool
```

### 6. Verificacion en base de datos

```bash
python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://usuario_bd:password_seguro_bd@localhost:5432/nombre_bd')
cursor = conn.cursor()
cursor.execute('SELECT count(*) FROM frames'); print(f'Frames: {cursor.fetchone()[0]}')
cursor.execute('SELECT count(*) FROM detections'); print(f'Detections: {cursor.fetchone()[0]}')
cursor.execute('SELECT count(*) FROM persons'); print(f'Persons: {cursor.fetchone()[0]}')
cursor.close(); conn.close()
"
```

Deberia mostrar:
```
Frames: 5
Detections: 14
Persons: 3
```
(mas los que se hayan agregado durante las pruebas)

### 7. Correr tests de regresion (S1 y S2)

```bash
python3 tests/test_api.py --env local
```

---

## Detalles de Implementacion

### S3 - GET /frames/{frameId}
1. Busca el frame en PostgreSQL por frameId
2. Extrae el fid de la image_url almacenada
3. Descarga la imagen desde SeaweedFS (volumen interno)
4. Si `thumbnail=true`, redimensiona con Pillow a 300x300 manteniendo aspect ratio
5. Retorna `Response(content=bytes, media_type="image/jpeg")`

### S4 - GET /frames/search
- Query params: `clases` (separadas por coma), `lat_min`, `lat_max`, `lon_min`, `lon_max`, `limit`, `offset`
- Construye consulta SQL dinamica con filtros opcionales
- Retorna lista con datos de frame + detecciones anidadas

### S5.1 - POST /persons
- Validacion Pydantic: nombre y apellido (1-255 chars), email obligatorio, extra (dict opcional)
- Genera UUID v4 como person_id
- Inserta con `ON CONFLICT (email) DO NOTHING` para evitar duplicados

---

## Pruebas Realizadas

### Resultados: 10/10 endpoints verificados

```
Test                                          Status     Detail
============================================================
GET /                                         PASS       200
S1 GET /models                                PASS       200 total=1
S3 GET /frames/{id}                           PASS       200 type=image/jpeg size=12396
S3 GET /frames/{id}?thumbnail=true            PASS       200 size=3663
S4 GET /frames/search                         PASS       200 total=6
S4 GET /frames/search?clases=&lat=            PASS       200 total=5
S5.1 POST /persons                            PASS       201 id=dc607b83...
S5.1 GET /persons/{id}                        PASS       200 email=final@test.com
S5.1 GET /persons                             PASS       200 total=5
S2 POST /detections (regresion)               PASS       200 frame_id=...
```

### Tests de regresion
Los endpoints S1 (GET /models) y S2 (POST /detections) del Miembro B continuan funcionando correctamente. No se introdujeron breaking changes.

---

## Arquitectura de Rutas

```
FastAPI App (main.py)
  |
  +-- /api/models (S1 - Miembro B)
  +-- /api/detections (S2 - Miembro B)
  +-- /api/frames (S3 + S4 - Miembro C)
  |     +-- GET /{frame_id}?thumbnail=true
  |     +-- GET /search?clases=&lat_min=&lat_max=&lon_min=&lon_max=
  +-- /api/persons (S5.1 - Miembro C)
        +-- POST /
        +-- GET /{person_id}
        +-- GET /
```
