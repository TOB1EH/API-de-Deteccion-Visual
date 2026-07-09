# Referencia de Endpoints API

Todas las rutas usan el prefijo `/api` (proxeado por Nginx).

## Health Check

```
GET /api/health
```

```bash
curl http://localhost/api/health
```

Respuesta: `"API Detection Service OK"`

## S1 - Listar Modelos

```
GET /api/models
```

```bash
curl http://localhost/api/models
```

```json
["yolo11n.pt", "yolo11s.pt"]
```

## S2 - Ejecutar Deteccion

```
POST /api/detections
```

**Parametros:**
- `image` (file, required): imagen JPEG/PNG
- `lat` (form, required): latitud
- `lon` (form, required): longitud
- `modelId` (form, optional): nombre del modelo (default: `yolo11n.pt`)

```bash
curl -X POST http://localhost/api/detections \
  -F "image=@foto.jpg" \
  -F "lat=-34.6037" \
  -F "lon=-58.3816" \
  -F "modelId=yolo11n.pt"
```

```json
{
  "frameId": "uuid-string",
  "detections": [
    {
      "detectionId": "uuid",
      "class": "person",
      "confidence": 0.95,
      "bbox": [100, 200, 300, 400]
    }
  ],
  "imageUrl": "http://..."
}
```

## S3 - Obtener Fotograma

```
GET /api/frames/{frameId}?thumbnail=true
```

```bash
curl -o fotograma.jpg "http://localhost/api/frames/uuid-del-frame?thumbnail=true"
```

- `thumbnail=true` (opcional): devuelve miniatura en lugar de imagen completa

## S4 - Buscar Fotogramas

```
GET /api/frames/search?clases=&lat=&lon=&limit=50
```

```bash
curl "http://localhost/api/frames/search?clases=person,car&lat=-34.6&lon=-58.38"
```

```json
{
  "results": [
    {
      "frameId": "uuid",
      "timestamp": "2026-07-03T20:00:00Z",
      "lat": -34.6037,
      "lon": -58.3816,
      "detections": ["person", "car"]
    }
  ],
  "total": 1
}
```

## S5.1 - Crear Persona

```
POST /api/persons
```

```bash
curl -X POST http://localhost/api/persons \
  -H "Content-Type: application/json" \
  -d '{"name": "Juan Perez", "metadata": {"notas": "estudiante"}}'
```

```json
{
  "personId": "uuid",
  "name": "Juan Perez",
  "createdAt": "2026-07-03T20:00:00Z"
}
```

## S5.1 - Obtener Persona

```
GET /api/persons/{personId}
```

```bash
curl http://localhost/api/persons/uuid-de-persona
```

```json
{
  "personId": "uuid",
  "name": "Juan Perez",
  "metadata": {},
  "createdAt": "2026-07-03T20:00:00Z"
}
```

## S5.2 - Generar Embeddings Faciales

```
POST /api/persons/{personId}/embeddings
```

```bash
curl -X POST http://localhost/api/persons/uuid/embeddings \
  -F "image=@rostro.jpg"
```

```json
{
  "personId": "uuid",
  "embedding_dim": 128,
  "processed": true
}
```

## S5.3 - Reconocimiento Facial

```
POST /api/face-recognition
```

**Parametros:**
- `image` (file): imagen con rostro
- `threshold` (opcional, default: 0.8)

```bash
curl -X POST http://localhost/api/face-recognition \
  -F "image=@rostro.jpg" \
  -F "threshold=0.85"
```

```json
{
  "personId": "uuid",
  "name": "Juan Perez",
  "confidence": 0.92,
  "match": true
}
```

Si `confidence <= threshold`, retorna `"match": false` y `"personId": null`.

## Metricas Prometheus

```
GET /metrics
```

```bash
curl http://localhost:8000/metrics
```

```
# HELP api_requests_total Total de requests HTTP
# TYPE api_requests_total counter
api_requests_total{endpoint="/api/health",method="GET",http_status="200"} 42
```
