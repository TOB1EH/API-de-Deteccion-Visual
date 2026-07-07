# Servicios

## mock.js

Contiene todos los datos falsos para desarrollo. Ubicado en `src/services/mock.js`.

Cada constante exportada simula la respuesta de un endpoint de la API real.

### MOCK_MODELS

Simula `GET /api/models`.

```js
{
  total: 2,
  models: [
    { name: "yolo11n.pt", size: 4712345, type: "yolo", path: "models/local/yolo11n.pt" },
    { name: "yolo11s.pt", size: 18123456, type: "yolo", path: "models/local/yolo11s.pt" }
  ]
}
```

Usado por: `DashboardView.vue` (select de modelos).

---

### MOCK_DETECTIONS

Simula detecciones individuales devueltas por el modelo.

```js
[
  { class_name: "person", class_id: 0, confidence: 0.95, bbox: { x_min: 100, y_min: 200, x_max: 300, y_max: 400 } },
  { class_name: "car", class_id: 2, confidence: 0.87, bbox: { x_min: 50, y_min: 150, x_max: 200, y_max: 300 } }
]
```

Disponible pero no usado actualmente por ninguna vista (las detecciones vienen anidadas dentro de cada frame).

---

### MOCK_FRAME_RESULT

Simula `POST /api/detections`.

```js
{
  frame_id: "a1b2c3d4-e5f6-7890-aaaa-bbbbccccdddd",
  image_url: "https://via.placeholder.com/800x600",
  detections_count: 2,
  status: "processed",
  message: "Se procesaron 2 detecciones",
  timestamp: "2026-07-07T..."
}
```

Usado por: `DashboardView.vue` (resultado del procesamiento).

---

### MOCK_SEARCH_RESULTS

Simula `GET /api/frames/search`.

```js
{
  total: 25,
  frames: [
    {
      frame_id: "uuid-1",
      model_id: "yolo11n.pt",
      latitude: -34.6037,
      longitude: -58.3816,
      image_url: "https://via.placeholder.com/400x300?text=Frame+1",
      metadata: { camera_id: "cam-001", source: "web" },
      detections_count: 3,
      created_at: "2026-06-28T12:00:00Z",
      detections: [
        { detection_id: "det-1", class_name: "person", confidence: 0.95, bbox: { x_min: 100, y_min: 200, x_max: 300, y_max: 400 } },
        { detection_id: "det-2", class_name: "car", confidence: 0.87, bbox: { x_min: 50, y_min: 150, x_max: 200, y_max: 300 } }
      ]
    },
    { ... } // segundo frame
  ]
}
```

Contiene 2 frames mockeados con distintas clases, ubicaciones y camaras.

Usado por: `SearchView.vue` (filtrado y listado de resultados).

---

### MOCK_PERSONS

Simula `GET /api/persons`.

```js
{
  total: 3,
  persons: [
    { person_id: "p-1", nombre: "Juan", apellido: "Perez", email: "juan@mail.com", created_at: "2026-06-01", updated_at: "2026-06-01" },
    { person_id: "p-2", nombre: "Maria", apellido: "Garcia", email: "maria@mail.com", created_at: "2026-06-02", updated_at: "2026-06-02" },
    { person_id: "p-3", nombre: "Carlos", apellido: "Lopez", email: "carlos@mail.com", created_at: "2026-06-03", updated_at: "2026-06-03" }
  ]
}
```

Usado por: `PersonsView.vue` (tabla de personas).

---

### MOCK_FRAME_DETAIL

Simula `GET /api/frames/{id}`.

```js
{
  frame_id: "a1b2c3d4-e5f6-7890-aaaa-bbbbccccdddd",
  model_id: "yolo11n.pt",
  latitude: -34.6037,
  longitude: -58.3816,
  image_url: "https://picsum.photos/800/600?random=1",
  metadata: { camera_id: "cam-001", source: "web" },
  detections_count: 2,
  status: "processed",
  created_at: "2026-06-28T12:00:00Z",
  detections: [
    { detection_id: "det-1", class_name: "person", confidence: 0.95, bbox: { x_min: 150, y_min: 100, x_max: 450, y_max: 500 } },
    { detection_id: "det-2", class_name: "car", confidence: 0.87, bbox: { x_min: 50, y_min: 300, x_max: 350, y_max: 550 } }
  ]
}
```

Usado por: `FrameDetailView.vue` (detalle del fotograma + overlay).

---

## API real (futura)

El archivo `services/api.js` no existe aun. Cuando se integre con el backend real, debera:

1. Definir una instancia de axios con `baseURL` apuntando a `https://bfts2026.mooo.com/api/` o `http://localhost/api/`
2. Implementar funciones por cada endpoint (getModels, postDetection, getFrame, searchFrames, etc.)
3. Incorporar manejo de tokens JWT de Keycloak en los headers de Authorization
4. Reemplazar el uso directo de `mock.js` en las vistas por llamadas a `api.js`

### Endpoints a consumir

| Metodo | Endpoint | Funcion |
|---|---|---|
| GET | /api/models | Listar modelos disponibles |
| POST | /api/detections | Enviar imagen para procesar |
| GET | /api/frames/{id} | Obtener detalle de fotograma |
| GET | /api/frames/search | Buscar fotogramas con filtros |
| GET | /api/persons | Listar personas |
| POST | /api/persons | Crear persona |
| POST | /api/persons/{id}/embeddings | Subir fotos faciales |
| POST | /api/face-recognition | Reconocimiento facial |
