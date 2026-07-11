# Prueba Local de la API Completa

## Requisitos

- Docker instalado
- Node.js 18+
- Puerto 5432, 8000, 8001, 8081, 9333, 8090 libres
- Stack local corriendo (ver [Levantar Stack Local](#levantar-stack-local))

---

## Levantar Stack Local

```bash
cd ~/API-de-Deteccion-Visual

# Asegurar que Keycloak local este corriendo
docker ps --filter name=api_detection_keycloak_local --format "{{.Names}} {{.Status}}"

# Si no esta, iniciarlo:
docker run -d \
  --name api_detection_keycloak_local \
  -p 8081:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin123 \
  -e KC_HOSTNAME=localhost \
  -e KC_HTTP_PORT=8080 \
  -e KC_HTTP_RELATIVE_PATH=/auth \
  -v /home/sofia/API-de-Deteccion-Visual/docker/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro \
  quay.io/keycloak/keycloak:26.6 \
  start-dev --import-realm

# Iniciar el resto de servicios
POSTGRES_USER=detections_user \
POSTGRES_DB=detections_db \
POSTGRES_PASSWORD=bfts2026. \
docker compose -f docker-compose.local.yml up -d db seaweed-master seaweed-volume inference-server api

# Verificar que todos esten corriendo
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Salida esperada:**
```
api_detection_api_local              Up X minutes
api_detection_db_local               Up X minutes (healthy)
seaweed_master_local                 Up X minutes
seaweed_volume_local                 Up X minutes
yolo_inference_server_local          Up X minutes
api_detection_keycloak_local         Up X minutes
```

**Error: API reiniciando:**
```
api_detection_api_local  Restarting (1) X seconds ago
```
→ Reconstruir la imagen: `POSTGRES_USER=detections_user POSTGRES_DB=detections_db POSTGRES_PASSWORD=bfts2026. docker compose -f docker-compose.local.yml build api`

---

## 1. Verificar que todo el stack esta vivo

```bash
# API
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Salida esperada:**
```json
{"status": "healthy", "service": "API Deteccion Visual", "version": "1.0.0"}
```

```bash
# DB - tablas creadas
docker exec api_detection_db_local psql -U detections_user -d detections_db -c "\dt"
```

**Salida esperada:**
```
              List of relations
 Schema |      Name       | Type  |     Owner
--------+-----------------+-------+----------------
 public | detections      | table | detections_user
 public | face_embeddings | table | detections_user
 public | frames          | table | detections_user
 public | persons         | table | detections_user
```

```bash
# Indice pgvector
docker exec api_detection_db_local psql -U detections_user -d detections_db \
  -c "SELECT tablename, indexname FROM pg_indexes WHERE tablename='face_embeddings';"
```

**Salida esperada:**
```
    tablename    |           indexname
-----------------+-------------------------------
 face_embeddings | face_embeddings_pkey
 face_embeddings | idx_face_embeddings_person_id
 face_embeddings | idx_face_embeddings_ivfflat
```

**Error: `role "detections_user" does not exist`:**
→ La BD se inicializo con otro usuario. Limpiar datos y reiniciar:
```bash
docker stop api_detection_db_local && docker rm api_detection_db_local
docker run --rm -v /home/sofia/API-de-Deteccion-Visual/volumes/pg_data_local:/data alpine sh -c "rm -rf /data/* && rm -rf /data/.* 2>/dev/null"
POSTGRES_USER=detections_user POSTGRES_DB=detections_db POSTGRES_PASSWORD=bfts2026. docker compose -f docker-compose.local.yml up -d db
```

---

## 2. Obtener token de Keycloak

```bash
TOKEN=$(curl -s -X POST http://localhost:8081/auth/realms/api-detection/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-backend" \
  -d "username=admin" \
  -d "password=admin123" \
  -d "grant_type=password" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool
```

**Salida esperada:** JSON con `preferred_username: admin` y `realm_access.roles` conteniendo `admin`, `operator`, `viewer`.

**Error:**
```json
{"error":"unauthorized_client","error_description":"Invalid client or Invalid client credentials"}
```
→ Verificar que Keycloak este corriendo en `http://localhost:8081` y que el realm `api-detection` existe.

```bash
# Verificar Keycloak
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/auth/realms/api-detection
# Debe responder 200
```

**Error: Token expiro durante las pruebas:**
El token dura 1 hora. Si expira, repetir el paso 2 para renovarlo.

---

## 3. Subir una deteccion (POST /api/detections)

Preparar imagen de prueba:

```bash
curl -s -o /tmp/test.jpg https://picsum.photos/800/600
ls -la /tmp/test.jpg
```
**Salida esperada:** archivo JPG de ~100KB

Enviar deteccion con modelo `pelotas.pt`:

```bash
curl -s -X POST http://localhost:8000/api/detections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -w0 /tmp/test.jpg)'",
    "model_id": "pelotas.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "confidence": 0.25
  }' | python3 -m json.tool
```

**Salida esperada:**
```json
{
    "frame_id": "3a1f2b8c-9d4e-5f6a-7b8c-9d0e1f2a3b4c",
    "image_url": "http://seaweed-volume:8080/3a1f2b8c-9d4e-5f6a-7b8c-9d0e1f2a3b4c.jpg",
    "detections_count": 3,
    "status": "processed",
    "message": "Se procesaron 3 detecciones",
    "timestamp": "2026-07-11T21:38:47Z"
}
```

**Errores:**
```json
502: {"detail": "Inference server error (500): ..."}
```
→ inference-server no responde. Verificar: `docker logs yolo_inference_server_local`

```json
422: {"detail": [{"msg": "field required", "type": "value_error.missing"}]}
```
→ Faltan campos obligatorios en el payload (`image_base64`, `model_id`, `latitude`, `longitude`)

```json
500: {"detail": "Error procesando detecciones: ..."}
```
→ Error interno. Verificar logs: `docker logs api_detection_api_local`

Guardar el frame_id:

```bash
FRAME_ID="copiar-el-uuid-que-devolvio"
```

---

## 4. Ver detalle del frame (GET /api/frames/{id}/detail)

```bash
curl -s http://localhost:8000/api/frames/$FRAME_ID/detail \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Salida esperada:**
```json
{
    "frame_id": "3a1f2b8c-...",
    "model_id": "pelotas.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "image_url": "http://seaweed-volume:8080/...",
    "detections_count": 3,
    "metadata": {
        "camera_id": null,
        "source": null
    },
    "created_at": "2026-07-11T21:38:47.132045Z",
    "detections": [
        {
            "detection_id": "uuid-det-1",
            "class_name": "pelota",
            "class_id": 0,
            "confidence": 0.92,
            "bbox": {"x_min": 100, "y_min": 200, "x_max": 300, "y_max": 400}
        }
    ]
}
```

**Errores:**
```
404: {"detail": "Frame uuid... no encontrado"}
```
→ El frame_id no existe. Verificar que se uso el mismo frame_id devuelto por el POST.

```
401: {"detail": "Not authenticated"}
```
→ Token invalido o expirado. Obtener uno nuevo (paso 2).

---

## 5. Descargar la imagen del frame

```bash
# Imagen original
curl -s -o /tmp/frame_result.jpg http://localhost:8000/api/frames/$FRAME_ID \
  -H "Authorization: Bearer $TOKEN"
ls -la /tmp/frame_result.jpg
file /tmp/frame_result.jpg
```

**Salida esperada:**
```
-rw-r--r-- 1 user user 123456 Jul 11 18:40 /tmp/frame_result.jpg
/tmp/frame_result.jpg: JPEG image data, JFIF standard 1.01
```

```bash
# Thumbnail (300x300)
curl -s -o /tmp/thumb_result.jpg "http://localhost:8000/api/frames/$FRAME_ID?thumbnail=true" \
  -H "Authorization: Bearer $TOKEN"
ls -la /tmp/thumb_result.jpg
```

**Salida esperada:** Archivo mas chico que el original (~30-50KB).

**Error: Archivo de 0 bytes o 404:**
→ La imagen no se encontro en SeaweedFS. Verificar: `docker logs seaweed_volume_local`

---

## 6. Buscar frames (GET /api/frames/search)

```bash
# Buscar por clase
curl -s "http://localhost:8000/api/frames/search?clases=pelota&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Salida esperada:**
```json
{
    "total": 1,
    "frames": [
        {
            "frame_id": "...",
            "model_id": "pelotas.pt",
            "latitude": -34.6037,
            "longitude": -58.3816,
            "image_url": "http://seaweed-volume:8080/...",
            "detections_count": 3,
            "created_at": "2026-07-11T21:38:47.132045Z",
            "detections": [
                {
                    "detection_id": "...",
                    "class_name": "pelota",
                    "confidence": 0.92,
                    "bbox": {"x_min": 100, "y_min": 200, "x_max": 300, "y_max": 400}
                }
            ]
        }
    ]
}
```

**Filtros disponibles:**
| Parametro | Ejemplo | Descripcion |
|-----------|---------|-------------|
| `clases` | `pelota,person` | Clases separadas por coma |
| `lat_min` | `-34.7` | Latitud minima |
| `lat_max` | `-34.5` | Latitud maxima |
| `lon_min` | `-58.5` | Longitud minima |
| `lon_max` | `-58.3` | Longitud maxima |
| `camera_id` | `cam-001` | ID de camara |
| `source` | `web` | Fuente de la imagen |
| `limit` | `10` | Maximo resultados (default 50, max 200) |
| `offset` | `0` | Paginacion |

**Sin filtros** (devuelve los ultimos 50 frames):
```bash
curl -s "http://localhost:8000/api/frames/search?limit=3" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 7. Ver detecciones de un frame (GET /api/detections/{frame_id})

```bash
curl -s http://localhost:8000/api/detections/$FRAME_ID \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Salida esperada:**
```json
{
    "frame_id": "uuid...",
    "detections_count": 3,
    "detections": [
        {"detection_id": "...", "class_name": "pelota", "confidence": 0.92, ...}
    ]
}
```

---

## 8. CRUD de personas y reconocimiento facial

### Crear persona

```bash
curl -s -X POST http://localhost:8000/api/persons \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Juan", "apellido": "Perez", "email": "juan@mail.com"}' | python3 -m json.tool
```

**Salida esperada:**
```json
{
    "person_id": "uuid-persona",
    "nombre": "Juan",
    "apellido": "Perez",
    "email": "juan@mail.com",
    "metadata": null,
    "created_at": "2026-07-11",
    "updated_at": "2026-07-11"
}
```

Guardar el person_id:

```bash
PERSON_ID="uuid-de-la-persona-creada"
```

### Listar personas

```bash
curl -s http://localhost:8000/api/persons \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Errores:**
```
422: {"detail": [{"msg": "field required", "type": "value_error.missing"}]}
```
→ Falta `nombre` o `apellido` en el POST.

---

## 9. Probar con diferentes modelos

```bash
# Probar con celular.pt
curl -s -X POST http://localhost:8000/api/detections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -w0 /tmp/test.jpg)'",
    "model_id": "celular.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "confidence": 0.25
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Frame: {d['frame_id']}\\nDetecciones: {d['detections_count']}\\nEstado: {d['status']}\")"

# Probar con dados.pt
curl -s -X POST http://localhost:8000/api/detections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -w0 /tmp/test.jpg)'",
    "model_id": "dados.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "confidence": 0.25
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Frame: {d['frame_id']}\\nDetecciones: {d['detections_count']}\\nEstado: {d['status']}\")"

# Probar con mouse.pt
curl -s -X POST http://localhost:8000/api/detections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -w0 /tmp/test.jpg)'",
    "model_id": "mouse.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "confidence": 0.25
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Frame: {d['frame_id']}\\nDetecciones: {d['detections_count']}\\nEstado: {d['status']}\")"
```

---

## 10. Probar con el frontend

```bash
cd ~/API-de-Deteccion-Visual/frontend
npm run dev
```

1. Abri `http://localhost:3000/` en el navegador
2. Login con `admin` / `admin123` (Keycloak local)
3. Anda a `/cargar` y selecciona `pelotas.pt`
4. Subi una imagen, completa lat/lon, presiona "Procesar fotograma"
5. Los resultados son REALES (van a la API local, inference-server procesa, se guarda en BD local)
6. Hace clic en "Ver detecciones" para ver el detalle con bounding boxes

**Que verificar en el frontend:**
- Los modelos disponibles incluyen `pelotas.pt`, `celular.pt`, etc.
- Despues de procesar, el frame_id, detections_count y status se muestran correctamente
- Al hacer clic en "Ver detecciones", la imagen, los bounding boxes y las clases corresponden al modelo usado
- `/buscar` permite filtrar por clase `pelota` y encuentra los frames procesados
- `/personas` permite crear personas y listarlas

---

## Comandos de diagnostico rapido

```bash
# Ver logs de la API
docker logs api_detection_api_local --tail 20

# Ver logs del inference-server
docker logs yolo_inference_server_local --tail 20

# Ver ultimos frames en la BD
docker exec -it api_detection_db_local psql -U detections_user -d detections_db \
  -c "SELECT frame_id, model_id, detections_count, created_at FROM frames ORDER BY created_at DESC LIMIT 5;"

# Contar detecciones por modelo
docker exec -it api_detection_db_local psql -U detections_user -d detections_db \
  -c "SELECT d.class_name, COUNT(*) FROM detections d JOIN frames f ON d.frame_id = f.frame_id WHERE f.model_id = 'pelotas.pt' GROUP BY d.class_name;"

# Verificar indice pgvector
docker exec -it api_detection_db_local psql -U detections_user -d detections_db \
  -c "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE tablename='face_embeddings';"

# Verificar que el inference-server responde
curl -s http://localhost:8001/health 2>&1 || echo "Inference server no responde"

# Ver espacio en SeaweedFS
curl -s http://localhost:9333/cluster/status 2>&1 | python3 -m json.tool
```

---

## Solucion de problemas

### API reiniciando constantemente

```bash
docker logs api_detection_api_local
```

Causas comunes:
- `ModuleNotFoundError: No module named 'prometheus_client'` → Reconstruir: `docker compose -f docker-compose.local.yml build api`
- `connection to server at "db" (xxx) failed` → La BD no esta lista. Esperar o reiniciar: `docker restart api_detection_db_local`

### Inference-server no responde

```bash
docker logs yolo_inference_server_local
```

Causas comunes:
- No encuentra los modelos en `/app/models/` → Verificar que `./models/local/` exista y tenga los .pt
- Error de memoria → Verificar RAM disponible

### Token invalido

```bash
# Obtener token nuevo
TOKEN=$(curl -s -X POST http://localhost:8081/auth/realms/api-detection/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-backend&username=admin&password=admin123&grant_type=password" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Frontend no se conecta a la API local

Verificar que `frontend/src/services/api.js` tenga `baseURL: 'http://localhost:8000/api/'` cuando corre en `localhost:3000`. Si no, actualizar y reiniciar `npm run dev`.

---

## Flujo completo en 1 script

```bash
#!/bin/bash
set -e

echo "=== 1. Obtener token ==="
TOKEN=$(curl -s -X POST http://localhost:8081/auth/realms/api-detection/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=api-backend&username=admin&password=admin123&grant_type=password" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token obtenido"

echo "=== 2. Descargar imagen de prueba ==="
curl -s -o /tmp/test.jpg https://picsum.photos/800/600
echo "Imagen descargada"

echo "=== 3. Subir deteccion con pelotas.pt ==="
RESP=$(curl -s -X POST http://localhost:8000/api/detections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -w0 /tmp/test.jpg)'",
    "model_id": "pelotas.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "confidence": 0.25
  }')
FRAME_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['frame_id'])")
echo "Frame creado: $FRAME_ID"
echo "$RESP" | python3 -m json.tool

echo "=== 4. Ver detalle del frame ==="
curl -s "http://localhost:8000/api/frames/$FRAME_ID/detail" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "=== 5. Descargar imagen ==="
curl -s -o /tmp/frame_$FRAME_ID.jpg "http://localhost:8000/api/frames/$FRAME_ID" \
  -H "Authorization: Bearer $TOKEN"
echo "Imagen descargada ($(wc -c < /tmp/frame_$FRAME_ID.jpg) bytes)"

echo "=== 6. Buscar frames con clase pelota ==="
curl -s "http://localhost:8000/api/frames/search?clases=pelota&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "=== 7. Crear persona ==="
PERSON_ID=$(curl -s -X POST http://localhost:8000/api/persons \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Test", "apellido": "Local", "email": "test@local.com"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['person_id'])")
echo "Persona creada: $PERSON_ID"

echo "=== PRUEBAS COMPLETADAS ==="
echo "Frame ID: $FRAME_ID"
echo "Person ID: $PERSON_ID"
