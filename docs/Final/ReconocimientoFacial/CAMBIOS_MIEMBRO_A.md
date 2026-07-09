# Cambios del Miembro A — Reconocimiento Facial

## Problema original

DeepFace con `detector_backend="opencv"` (Haar Cascade) no detectaba rostros de forma confiable en fotos con distinto angulo o iluminacion. Las dos fotos de Cristiano Ronaldo (`adna.jpg` vs `ronaldo.jpg`) producian distancia coseno > 0.99 (confianza < 0.01), incluso con threshold 0.1. Causa raiz: Haar Cascade solo funciona bien con rostros frontales.

## Solucion aplicada

### 1. Mejora del detector: opencv -> mtcnn

**Archivo:** `inference-server/main.py`
**Cambio:** `detector_backend="opencv"` -> `detector_backend="mtcnn"`

MTCNN (Multi-Task Cascaded Convolutional Networks) detecta rostros en angulos variados, perfiles, y condiciones de iluminacion dificiles. Es mas lento que opencv pero mucho mas preciso.

### 2. Normalizacion correcta: base -> Facenet

**Archivo:** `inference-server/main.py`
**Cambio:** `normalization="base"` -> `normalization="Facenet"`

El modelo Facenet fue entrenado con normalizacion z-score especifica. Usar `"base"` (pixeles crudos) producia embeddings inconsistentes. Con `"Facenet"` el preprocesamiento se alinea con el entrenamiento del modelo.

### 3. Multiples embeddings por persona

**Archivo:** `client/setup_cliente.py`
**Cambios:**
- `faces embed` ahora acepta `path` (archivo o directorio)
- Si es directorio, escanea `*.jpg/*.jpeg/*.png`, itera cada foto
- Muestra progreso `[i/N]` y resumen final: `X procesadas, Y exitos, Z errores`
- Logica extraida a `_embed_one_image()` reusable

### 4. Fix installer Docker

**Archivo:** `client/setup_cliente.py`

**Problema:** `host.docker.internal` no funciona en Linux. El installer solo conectaba el container a la red Docker si `API_URL` contenia `"api_detection_api_local"`, que nunca se cumplia con `localhost`.

**Solucion:**
- `start_container()` detecta `localhost`, `127.0.0.1` o `api_detection_api_local` en `API_URL`
- Si es local: conecta a la red Docker y traduce `localhost:8000` -> `api:8000`
- Si es remoto: pasa `API_URL` directo (sin red Docker)
- `cmd_install()` ahora siempre baja la ultima imagen y recrea el container (elimina early return)

### 5. DEEPFACE_BACKEND configurable

**Archivo:** `client/setup_cliente.py`
**Cambio:** Ya no hardcodea `Facenet`. Lee de `DEEPFACE_BACKEND` env var (default: Facenet). Permite cambiar a ArcFace/Facenet512 sin modificar codigo.

### 6. Imagen Docker Hub actualizada

**Repositorio:** `docker.io/tfunes/inference-server:latest`
**Configuracion actual:**
- Modelo: Facenet (128 dimensiones)
- Detector: MTCNN
- Normalizacion: Facenet

## Resultados de las pruebas

### Con las fotos de Franco Colapinto (4 fotos de referencia)

| Foto de prueba | Antes (opencv + base) | Despues (mtcnn + Facenet) |
|---|---|---|
| franco_frontal.jpg | 1.0000 | 1.0000 |
| franco_prueba.jpg | No reconocido | **0.9194** |
| franco_prueba_+.jpeg | No reconocido | **0.8456** |
| franco_prueba_3.jpeg | No reconocido | **0.7163** |
| franco_prueba_2.jpg | No reconocido | No reconocido |

**Mejora: 0/5 -> 4/5 reconocidos con threshold 0.5**

La unica foto que sigue fallando (`franco_prueba_2.jpg`) es un angulo muy distinto a las 4 fotos de referencia. Solucion: agregar una foto similar como referencia extra.

## Arquitectura final

```
CLI (faces embed ./directorio/)
  |
  v
inference-server local (DeepFace: mtcnn + Facenet + normalization=Facenet)
  |
  v
API (POST /api/persons/{id}/embeddings)
  -> PostgreSQL + pgvector (embedding 128d)
  -> SeaweedFS (imagen original)
```

## Archivos modificados

| Archivo | Cambios |
|---|---|
| `client/setup_cliente.py` | Multiples embeddings, fix installer, DEEPFACE_BACKEND configurable |
| `inference-server/main.py` | Detector: mtcnn, Normalizacion: Facenet |
| `inference-server/Dockerfile` | Sin cambios |
| `AGENTS.md` | Actualizado con config actual |
