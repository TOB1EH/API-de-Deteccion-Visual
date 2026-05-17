# Primera entrega - Resumen del alcance

Según el PDF, la **primera entrega** cubre hasta el punto **5.4 inclusive** (fecha: **9/6/2026**). Lo que viene después (Keycloak, Grafana, frontend) es segunda entrega y queda fuera de este alcance.

---

## Filosofía central

Backend puro, **sin interfaz gráfica**. Todo se expone como **APIs REST** consumibles desde Postman, curl o scripts. Cada operación queda vinculada con identificadores únicos (frameId, personId, detectionId, etc.) para trazabilidad total.

---

## Servicios a implementar (MVP)

### S1 - Listado de modelos

- `GET /models`
- Lee modelos desde una carpeta local y los lista.
- Ejemplo de respuesta: `["yolo11n.pt", "yolo11s.pt"]`

---

### S2 - Ejecución de detección

- `POST /detections`
- El núcleo del sistema.
- **Entrada**: imagen + metadatos (lat/lon obligatorio) + modelId.
- Ejecuta el modelo de detección sobre el fotograma.
- **Persiste 3 cosas**:
  1. **Imagen** en almacenamiento de objetos (ej: SeaweedFS)
  2. **Metadatos** en base de datos relacional (mínimo: latitud, longitud)
  3. **Detecciones** en base de datos (formato JSON: clases, bounding boxes, scores)
- Todo vinculado a un mismo `frameId`.
- Opcional pero valorado: procesamiento asíncrono (hilos o colas).

---

### S3 - Obtención de fotograma

- `GET /frames/{frameId}`
- Recupera la imagen original o thumbnail (`?thumbnail=true`).

---

### S4 - Consulta y filtrado

- `GET /frames/search`
- Filtra por: clases detectadas, lat/lon (rangos), metadatos variables.
- Retorna lista con `frameId`, `imageURL`, metadata completa y detecciones.

---

### S5.1 - Gestión de personas

- `POST /persons` — crear persona
- `GET /persons/{personId}` — obtener persona
- Datos: personId (UUID), nombre, apellido, email, campo extra JSON.

---

### S5.2 - Carga y generación de embeddings

- `POST /persons/{personId}/embeddings`
- Recibe imagen(es), detecta el rostro, genera embedding, lo asocia a la persona.
- Almacena embeddings en BD.
- Opcional: almacenar las imágenes en el mismo sistema de objetos.

---

### S5.3 - Reconocimiento facial

- `POST /face-recognition`
- **Entrada**: imagen + threshold (default 0.8).
- **Proceso**: detecta rostro, genera embedding, compara contra almacenados.
- **Salida (reconocido)**: `{ personId, nombre, apellido, confidence }`
- **Salida (no reconocido)**: `{ personId: null, confidence }`
- Solo retorna persona si `confidence > threshold`.

---

### Punto 5.4 (opcional)

- FAISS / pgvector para búsqueda vectorial
- Procesamiento concurrente para cargas masivas
- Validación de calidad de imágenes (resolución, rostro único)

---

## Decisiones técnicas pendientes

1. **Lenguaje(s) de programación** (Python, Node.js, múltiples lenguajes, etc.)
2. **Framework web** (FastAPI, Flask, Express, etc.)
3. **Base de datos** (PostgreSQL, SQLite, más vectorial para embeddings)
4. **Almacenamiento de objetos** (SeaweedFS sugerido, o filesystem local)
5. **Modelo de detección** (YOLO — los ejemplos usan `yolo11n.pt`, `yolo11s.pt`)
6. **Librería de reconocimiento facial** (face_recognition, DeepFace, etc.)

---

## Restricciones de la primera entrega

- No existe interfaz gráfica
- Todos los servicios deben exponerse como APIs REST
- Deben poder ser consumidos mediante: Postman, curl, scripts automatizados
