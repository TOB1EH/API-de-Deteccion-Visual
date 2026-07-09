# Plan de Trabajo -- Frontend (Vue + Vuetify)

## Lo que te toca segun la distribucion

Segun `DISTRIBUCION_TRABAJO.md` sos el **Miembro B** y te encargas de:

| Tarea | Descripcion | Prioridad |
|---|---|---|
| **0.2** | Indice pgvector (ejecutar SQL en BD remota) | Baja, 10 min |
| **0.3** | Limpiar Dockerfile.api (sacar libpq-dev/gcc, poner libgl) | Baja, 10 min |
| **1.2** | Frontend completo con Vue + Vuetify | Alta, esta es tu tarea principal |

Ademas, tu README.md del proyecto te asigna el rol de **ayudar al Integrante 1 (Backend)** el 60% del tiempo, pero como te asignaron especificamente el frontend, enfocate en eso y ayudas a backend si te sobra tiempo.

---

## APIs que consume el frontend

Todas las APIs estan en `https://bfts2026.mooo.com/api/` (o `http://localhost/api/` en local).

| Pantalla | Endpoint | Metodo | Datos que envia | Datos que recibe |
|---|---|---|---|---|
| Login | Keycloak (`/auth/`) | OAuth2 | user+pass | JWT token |
| Dashboard (cargar imagen) | `/api/detections` | POST | `{image_base64, model_id, latitude, longitude, confidence, metadata}` | `{frame_id, image_url, detections_count, status, timestamp}` |
| Ver detecciones | `/api/frames/{frame_id}` | GET | `frame_id` + `?thumbnail=true` | Binario JPEG |
| Buscar fotogramas | `/api/frames/search` | GET | `?clases=&lat_min=&lat_max=&lon_min=&lon_max=&limit=&offset=` | `{total, frames: [{frame_id, image_url, metadata, detections}]}` |
| Listar personas | `/api/persons` | GET | - | `{total, persons: [{person_id, nombre, apellido, email}]}` |
| Crear persona | `/api/persons` | POST | `{nombre, apellido, email}` | `{person_id, nombre, apellido, email, created_at}` |
| Subir fotos faciales | `/api/persons/{id}/embeddings` | POST | `{image_base64, embedding, confidence}` | `{person_id, processed_images, valid_embeddings, rejected_images}` |
| Reconocimiento facial | `/api/face-recognition` | POST | `{embedding, threshold}` | `{person_id, nombre, apellido, confidence}` |
| Listar modelos | `/api/models` | GET | - | `{total, models: [{name, size, type}]}` |

---

## Por que necesitas mocks

Los otros miembros todavia no implementaron:
- **Keycloak (Miembro C):** no hay login OAuth2 real todavia
- **API orquestador (Miembro D, tarea 0.6):** `POST /api/detections` todavia no acepta imagen cruda, solo detecciones pre-computadas
- **face-api (Miembro A):** no esta desplegado, los endpoints faciales no funcionan con DeepFace real

Por eso arrancas con **mockups**: componentes visuales completos que funcionan con datos falsos. Cuando los otros terminen sus partes, solo cambias la capa de servicios (API calls) por las reales.

---

## Stack tecnologico

| Tecnologia | Version | Para que |
|---|---|---|
| Vue 3 | ^3.4 | Framework frontend |
| Vuetify 3 | ^3.5 | Libreria de componentes UI (Material Design) |
| Vite | ^5 | Build tool |
| vue-router | ^4 | Rutas/navegacion |
| pinia | ^2 | Estado global (opcional, para empezar simple) |
| axios | ^1 | Llamadas HTTP a la API |
| keycloak-js | ^25 | Integracion con Keycloak (despues, cuando este listo) |

---

## Estructura de archivos propuesta

```
frontend/
├── Dockerfile                    # Build + Nginx para deploy
├── nginx.conf                    # Config Nginx para SPA
├── package.json
├── vite.config.js
├── index.html
├── src/
│   ├── main.js                   # Entry point, setup Vuetify + Router
│   ├── App.vue                   # Componente raiz
│   ├── plugins/
│   │   └── vuetify.js            # Configuracion de Vuetify
│   ├── router/
│   │   └── index.js              # Definicion de rutas
│   ├── services/
│   │   ├── api.js                # Cliente axios con base URL
│   │   └── mock.js               # Datos mock para desarrollo
│   ├── views/
│   │   ├── LoginView.vue         # Login (redirige a Keycloak)
│   │   ├── DashboardView.vue     # Carga de imagen + resultados
│   │   ├── SearchView.vue        # Busqueda de fotogramas
│   │   ├── FrameDetailView.vue   # Ver detecciones de un frame
│   │   ├── PersonsView.vue       # CRUD de personas
│   │   └── FaceRecognitionView.vue # Reconocimiento facial
│   └── components/
│       ├── AppBar.vue            # Barra superior
│       ├── DetectionOverlay.vue  # Overlay de bounding boxes
│       ├── FrameCard.vue         # Tarjeta de resultado
│       └── PersonForm.vue        # Formulario de persona
```

---

## Orden de implementacion (semana a semana)

### Semana 1: Setup + Mockups de vistas principales

| Dia | Que hacer | Archivos |
|---|---|---|
| Lunes | Tareas 0.2 y 0.3 (son rapidas). Setup del proyecto Vue + Vuetify + Vite. Router con vistas vacias | `Dockerfile.api`, `frontend/` completo |
| Martes | Mockup de **DashboardView**: formulario de carga con campos (imagen, modelo, lat, lon, metadata), mostrar resultado mockeado | `DashboardView.vue`, `mock.js` |
| Miercoles | Mockup de **SearchView**: formulario de filtros (clases, rango lat/lon), tabla de resultados mockeados | `SearchView.vue`, `FrameCard.vue`, `mock.js` |
| Jueves | Mockup de **FrameDetailView**: mostrar imagen + bounding boxes overlay sobre la imagen | `FrameDetailView.vue`, `DetectionOverlay.vue` |
| Viernes | Mockup de **PersonsView**: tabla de personas, formulario crear persona, listado | `PersonsView.vue`, `PersonForm.vue`, `mock.js` |

### Semana 2: Reconocimiento facial + Login + Integracion real

| Dia | Que hacer | Archivos |
|---|---|---|
| Lunes | Mockup de **FaceRecognitionView**: subir foto, mostrar resultado (reconocido/no reconocido) | `FaceRecognitionView.vue`, `mock.js` |
| Martes | Conectar servicios reales (api.js) para las APIs que ya funcionen | `api.js` |
| Miercoles | Integrar Keycloak (keycloak-js) cuando Miembro C lo tenga listo | `LoginView.vue`, `services/auth.js` |
| Jueves | Probar flujo completo contra backend real. Pulir UI | Varios |
| Viernes | Build Docker, deploy, pruebas finales | `Dockerfile`, `nginx.conf` |

---

## Mock data

Mientras los otros miembros no terminan, usa datos mock en `src/services/mock.js`. Ejemplo:

```javascript
// src/services/mock.js
export const MOCK_MODELS = {
  total: 2,
  models: [
    { name: "yolo11n.pt", size: 4712345, type: "yolo", path: "models/local/yolo11n.pt" },
    { name: "yolo11s.pt", size: 18123456, type: "yolo", path: "models/local/yolo11s.pt" }
  ]
}

export const MOCK_DETECTIONS = [
  { class_name: "person", class_id: 0, confidence: 0.95, bbox: { x_min: 100, y_min: 200, x_max: 300, y_max: 400 } },
  { class_name: "car", class_id: 2, confidence: 0.87, bbox: { x_min: 50, y_min: 150, x_max: 200, y_max: 300 } }
]

export const MOCK_FRAME_RESULT = {
  frame_id: "a1b2c3d4-e5f6-7890-aaaa-bbbbccccdddd",
  image_url: "https://via.placeholder.com/800x600",
  detections_count: 2,
  status: "processed",
  timestamp: new Date().toISOString()
}

export const MOCK_SEARCH_RESULTS = {
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
        { detection_id: "det-1", class_name: "person", class_id: 0, confidence: 0.95, bbox: { x_min: 100, y_min: 200, x_max: 300, y_max: 400 } },
        { detection_id: "det-2", class_name: "car", class_id: 2, confidence: 0.87, bbox: { x_min: 50, y_min: 150, x_max: 200, y_max: 300 } }
      ]
    },
    {
      frame_id: "uuid-2",
      model_id: "yolo11s.pt",
      latitude: -34.6137,
      longitude: -58.3716,
      image_url: "https://via.placeholder.com/400x300?text=Frame+2",
      metadata: { camera_id: "cam-002", source: "mobile" },
      detections_count: 1,
      created_at: "2026-06-28T13:00:00Z",
      detections: [
        { detection_id: "det-3", class_name: "dog", class_id: 16, confidence: 0.92, bbox: { x_min: 200, y_min: 100, x_max: 400, y_max: 350 } }
      ]
    }
  ]
}

export const MOCK_PERSONS = {
  total: 3,
  persons: [
    { person_id: "p-1", nombre: "Juan", apellido: "Perez", email: "juan@mail.com", created_at: "2026-06-01", updated_at: "2026-06-01" },
    { person_id: "p-2", nombre: "Maria", apellido: "Garcia", email: "maria@mail.com", created_at: "2026-06-02", updated_at: "2026-06-02" },
    { person_id: "p-3", nombre: "Carlos", apellido: "Lopez", email: "carlos@mail.com", created_at: "2026-06-03", updated_at: "2026-06-03" }
  ]
}

export const MOCK_RECOGNITION = {
  person_id: "p-1",
  nombre: "Juan",
  apellido: "Perez",
  confidence: 0.87
}

export const MOCK_RECOGNITION_FAIL = {
  person_id: null,
  confidence: 0.45
}
```

El servicio `api.js` debe tener un flag `USE_MOCKS = true` que, mientras este activo, devuelva estos datos en vez de hacer llamadas HTTP reales.

---

## Tareas administrativas (0.2 y 0.3)

### 0.2 -- Indice pgvector (10 min)

Solo ejecutar este SQL en la BD remota via pgAdmin o psql:

```sql
CREATE INDEX IF NOT EXISTS idx_face_embeddings_vector
ON face_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

- Acceso pgAdmin: https://bfts2026.mooo.com/pgadmin/ (admin@bfts2026.mooo.com / bfts2026.)
- Servidor: `db` puerto `5432`, DB `detections_db`, user `detections_user`

### 0.3 -- Limpiar Dockerfile.api (10 min)

En `Dockerfile.api`, reemplazar:

```dockerfile
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
```

Por:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*
```

---

## Mockups visuales (lo que tenes que dibujar primero)

Antes de codificar, defini estas 6 vistas. Aca va una descripcion de cada una:

### 1. LoginView
- Pagina simple con boton "Iniciar sesion con Keycloak"
- Mientras Keycloak no existe, un mensaje "Autenticacion no disponible modo demo"
- Link para entrar en modo demo (sin autenticacion)

### 2. DashboardView (carga de imagen)
- Formulario con:
  - Upload de imagen (drag & drop o file picker)
  - Select de modelo (cargado desde `/api/models`)
  - Campos de latitud / longitud
  - Campo opcional: camara ID, source
  - Slider de confidence threshold (0-1)
- Boton "Procesar"
- Resultado: card con frame_id, image_url, detections_count
- Boton "Ver detecciones" que navega a FrameDetailView

### 3. SearchView (busqueda)
- Formulario de filtros:
  - Campo de clases (separadas por coma)
  - Rango de latitud (min/max)
  - Rango de longitud (min/max)
  - Paginacion (limit/offset)
- Tabla de resultados con:
  - frame_id, modelo, lat/lon, fecha, cantidad de detecciones
  - Thumbnail de la imagen
  - Click para ir al detalle
- Paginador

### 4. FrameDetailView (detalle de fotograma)
- Imagen grande con bounding boxes overlay
- Colores por clase de objeto
- Tooltip al hacer hover: nombre, confianza
- Tabla de detecciones debajo
- Botones: descargar original, descargar thumbnail

### 5. PersonsView (gestion de personas)
- Tabla con todas las personas (nombre, apellido, email)
- Boton "Nueva persona" -> dialog/modal con formulario
- Click en persona -> ver detalle + opcion de subir fotos faciales
- Boton "Subir fotos" que abre selector de archivos

### 6. FaceRecognitionView
- Upload de foto
- Select de threshold (slider 0-1, default 0.8)
- Boton "Reconocer"
- Resultado:
  - Si reconocido: card verde con foto, nombre, apellido, confidence
  - Si no reconocido: card roja con "Persona no identificada" y confidence

---

## Checklist de avance

- [ ] **Setup:** Vue 3 + Vuetify 3 + Vite + Router funcionando
- [ ] **Mockup LoginView:** pagina de login con modo demo
- [ ] **Mockup DashboardView:** formulario de carga con datos mockeados
- [ ] **Mockup SearchView:** filtros + tabla de resultados mockeados
- [ ] **Mockup FrameDetailView:** imagen con bounding boxes overlay
- [ ] **Mockup PersonsView:** CRUD de personas con datos mockeados
- [ ] **Mockup FaceRecognitionView:** reconocimiento con respuesta mockeada
- [ ] **Servicios:** api.js conectado a endpoints reales (USE_MOCKS = false)
- [ ] **Login real:** integracion con keycloak-js
- [ ] **Docker:** Dockerfile + nginx.conf funcionando
- [ ] **Tarea 0.2:** Indice pgvector creado en BD remota
- [ ] **Tarea 0.3:** Dockerfile.api limpio
