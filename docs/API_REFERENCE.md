# Referencia de la API REST

**Base URL:** `https://bfts2026.mooo.com/api`

Todas las rutas usan el prefijo `/api` (proxeado por Nginx). La documentacion interactiva (Swagger UI) esta disponible en `/api/docs`.

---

## Autenticacion

El sistema soporta dos metodos de autenticacion:

### Keycloak OAuth2 (JWT RS256)

- Obtener token via Keycloak password grant o redireccion OAuth2
- Enviar en cada request: `Authorization: Bearer <token>`
- Roles: `admin`, `operator`, `viewer`

### Token Facial (JWT HS256)

- Generado por `POST /api/auth/login/facial` tras reconocimiento biometrico
- Mismo formato de autorizacion: `Authorization: Bearer <token>`
- Incorpora los roles del usuario desde Keycloak si tiene `keycloak_user_id` vinculado

### Permisos por endpoint

| Endpoint | Admin | Operator | Viewer |
|---|---|---|---|
| GET /models | SI | SI | SI |
| POST /detections | SI | SI | NO |
| GET /frames/* | SI | SI | SI |
| GET /frames/search | SI | SI | SI |
| GET /persons | SI | SI | SI |
| POST /persons | SI | NO | NO |
| PUT /persons/{id} | SI | NO | NO |
| DELETE /persons/{id} | SI | NO | NO |
| POST /persons/{id}/embeddings | SI | SI | NO |
| POST /face-recognition | SI | SI | NO |
| POST /auth/register | NO* | NO* | NO* |
| POST /auth/login/facial | NO* | NO* | NO* |

(* Los endpoints de auth no requieren token — son publicos)

---

## Health Check

```
GET /health
```

```bash
curl https://bfts2026.mooo.com/api/health
```

Respuesta: `"API Detection Service OK"`

---

## Autenticacion Facial

### Registro Facial

Registra un nuevo usuario con reconocimiento facial. Crea la persona en BD y el usuario en Keycloak.

```
POST /auth/register
```

```bash
curl -X POST https://bfts2026.mooo.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "apellido": "Perez",
    "email": "juan@example.com",
    "password": "MiPassword123!"
  }'
```

```json
{
  "person_id": "uuid",
  "nombre": "Juan",
  "apellido": "Perez",
  "email": "juan@example.com",
  "message": "Registro exitoso. Enviando fotos faciales al inference-server local.",
  "access_token": "jwt-token-facial",
  "token_type": "bearer"
}
```

**Nota:** Despues del registro, las fotos faciales deben enviarse al **inference-server local** (puerto 8001) via `/face/embed`. El inference-server las reenvia a `POST /api/persons/{person_id}/embeddings`.

### Login Facial

Inicia sesion mediante reconocimiento facial. Requiere que el inference-server local haya identificado a la persona y devuelto su `person_id`.

```
POST /auth/login/facial
```

```bash
curl -X POST https://bfts2026.mooo.com/api/auth/login/facial \
  -H "Content-Type: application/json" \
  -d '{"person_id": "uuid-de-la-persona"}'
```

```json
{
  "access_token": "jwt-token-facial",
  "token_type": "bearer",
  "expires_in": 3600,
  "scope": "openid profile email",
  "person_id": "uuid",
  "nombre": "Juan",
  "apellido": "Perez"
}
```

### Verificacion Facial (2FA)

Verifica un rostro como segundo factor de autenticacion post-login Keycloak.

```
POST /auth/verify-face
```

Requiere `Authorization: Bearer <token>`.

```bash
curl -X POST https://bfts2026.mooo.com/api/auth/verify-face \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"person_id": "uuid"}'
```

---

## S1 - Modelos

### Listar modelos

```
GET /models
```

```bash
curl -H "Authorization: Bearer <token>" https://bfts2026.mooo.com/api/models
```

```json
{
  "models": [
    {
      "name": "yolo11n.pt",
      "size": 47123456,
      "type": "YOLO",
      "path": "/app/models/yolo11n.pt"
    }
  ],
  "total": 1
}
```

### Descargar modelo

```
GET /models/{name}/download
```

Requiere rol `admin` u `operator`.

---

## S2 - Detecciones

### Ejecutar deteccion

Procesa una imagen con el modelo YOLO especificado.

```
POST /detections
```

Requiere rol `admin` u `operator`.

```bash
curl -X POST https://bfts2026.mooo.com/api/detections \
  -H "Authorization: Bearer <token>" \
  -F "image=@foto.jpg" \
  -F "lat=-34.6037" \
  -F "lon=-58.3816" \
  -F "modelId=yolo11n.pt"
```

```json
{
  "frame_id": "uuid",
  "detections": [
    {
      "detection_id": "uuid",
      "class_name": "person",
      "confidence": 0.95,
      "bbox": [100, 200, 300, 400]
    }
  ],
  "image_url": "https://bfts2026.mooo.com/api/frames/uuid"
}
```

### Obtener deteccion por ID

```
GET /detections/{detection_id}
```

---

## S3 - Fotogramas

### Obtener imagen de fotograma

```
GET /frames/{frame_id}
```

Parametros opcionales:
- `thumbnail=true` — devuelve miniatura (mas rapida)

```bash
curl -H "Authorization: Bearer <token>" \
  -o fotograma.jpg \
  "https://bfts2026.mooo.com/api/frames/uuid-del-frame?thumbnail=true"
```

---

## S4 - Busqueda

### Buscar fotogramas

```
GET /frames/search
```

Parametros:
- `clases` (opcional): filtro por clases detectadas (ej: `person,car`)
- `lat`, `lon` (opcional): filtro por ubicacion
- `radius_km` (opcional, default: 10): radio de busqueda en km
- `person_id` (opcional): filtrar por persona reconocida
- `limit` (opcional, default: 50): maximo de resultados
- `offset` (opcional): paginacion

```bash
curl -H "Authorization: Bearer <token>" \
  "https://bfts2026.mooo.com/api/frames/search?clases=person,car&lat=-34.6&lon=-58.38&limit=20"
```

```json
{
  "frames": [
    {
      "frame_id": "uuid",
      "created_at": "2026-07-03T20:00:00",
      "lat": -34.6037,
      "lon": -58.3816,
      "detections_count": 3,
      "detections": [
        {"class_name": "person", "confidence": 0.95}
      ],
      "image_url": "https://bfts2026.mooo.com/api/frames/uuid"
    }
  ],
  "total": 1
}
```

---

## S5 - Personas

### Listar personas

```
GET /persons
```

```bash
curl -H "Authorization: Bearer <token>" \
  https://bfts2026.mooo.com/api/persons
```

```json
{
  "persons": [
    {
      "person_id": "uuid",
      "name": "Juan Perez",
      "email": "juan@example.com",
      "created_at": "2026-07-03T20:00:00",
      "keycloak_user_id": "uuid-kc",
      "embedding_count": 3,
      "keycloak_roles": ["viewer", "operator"]
    }
  ],
  "total": 1
}
```

### Obtener mi persona

```
GET /persons/me
```

Devuelve la persona asociada al token del usuario autenticado.

### Obtener persona por ID

```
GET /persons/{person_id}
```

### Crear persona

```
POST /persons
```

Requiere rol `admin`. Crea persona en BD y usuario en Keycloak. Envia email con credenciales.

```bash
curl -X POST https://bfts2026.mooo.com/api/persons \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "apellido": "Perez",
    "email": "juan@example.com"
  }'
```

```json
{
  "person_id": "uuid",
  "name": "Juan Perez",
  "email": "juan@example.com",
  "created_at": "2026-07-03T20:00:00",
  "keycloak_user_id": "uuid-kc",
  "keycloak_roles": ["viewer"]
}
```

**Nota:** El usuario recibe un email con su contrasena temporal generada aleatoriamente.

### Crear/actualizar mi persona

```
POST /persons/me
```

Crea o actualiza la persona asociada al token actual. No requiere roles especiales.

```bash
curl -X POST https://bfts2026.mooo.com/api/persons/me \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "apellido": "Perez",
    "email": "juan@example.com"
  }'
```

### Actualizar persona

```
PUT /persons/{person_id}
```

Requiere rol `admin`. Sincroniza nombre y email con Keycloak.

### Eliminar persona

```
DELETE /persons/{person_id}
```

Requiere rol `admin`. Tambien elimina el usuario de Keycloak.

### Sincronizar Keycloak

```
POST /persons/sync-keycloak
```

Crea registros de persona para usuarios de Keycloak que no tengan persona asociada.

### Generar embedding facial

```
POST /persons/{person_id}/embeddings
```

Requiere rol `admin` u `operator`. Envia automaticamente email de notificacion al usuario.

```bash
curl -X POST https://bfts2026.mooo.com/api/persons/uuid/embeddings \
  -H "Authorization: Bearer <token>" \
  -F "image=@rostro.jpg"
```

```json
{
  "person_id": "uuid",
  "embedding_id": "uuid",
  "dim": 128,
  "processed": true,
  "message": "Embedding generado exitosamente"
}
```

### Generar embedding desde rostro (face-proxy)

```
POST /persons/{person_id}/face-embed
```

Requiere rol `admin`. Para uso interno del inference-server.

### Listar embeddings de una persona

```
GET /persons/{person_id}/embeddings
```

### Reconocimiento facial

```
POST /face-recognition
```

Requiere rol `admin` u `operator`. Compara un rostro contra todos los embeddings almacenados.

```bash
curl -X POST https://bfts2026.mooo.com/api/face-recognition \
  -H "Authorization: Bearer <token>" \
  -F "image=@rostro.jpg" \
  -F "threshold=0.8"
```

```json
{
  "person_id": "uuid",
  "name": "Juan Perez",
  "confidence": 0.92,
  "match": true
}
```

Si `confidence <= threshold`, retorna `"match": false` y `"person_id": null`.

---

## Script de Cliente Local

El script `setup_cliente.py` configura el inference-server local necesario para reconocimiento facial.

```
GET /setup_cliente.py
```

```bash
curl -O https://bfts2026.mooo.com/setup_cliente.py
python3 setup_cliente.py install
```

Esto inicia un servidor en `http://localhost:8001` con:
- **Health:** `GET /health`
- **Reconocimiento:** `POST /face/recognize`
- **Embedding:** `POST /face/embed`

---

## Metricas

```
GET /metrics
```

Expone metricas en formato Prometheus.

```bash
curl https://bfts2026.mooo.com/api/metrics
```

---

## Codigos de Error

| Codigo | Significado |
|---|---|
| 200 | OK |
| 201 | Creado exitosamente |
| 400 | Bad Request — parametros invalidos |
| 401 | No autenticado — token faltante o invalido |
| 403 | Prohibido — rol insuficiente |
| 404 | Recurso no encontrado |
| 409 | Conflicto — recurso duplicado (ej: email existente) |
| 422 | Unprocessable Entity — validacion de datos fallo |
| 500 | Error interno del servidor |

### Formato de error

```json
{
  "detail": "Descripcion del error"
}
```
