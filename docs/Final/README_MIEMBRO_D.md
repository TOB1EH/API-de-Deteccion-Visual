# Miembro D - API Orquestador + CLI

## Que se implemento

### 0.6 - API como orquestador de inferencia

La API ahora puede recibir imagenes **sin detecciones pre-calculadas** y ejecutar
YOLO internamente llamando al inference-server. Esto permite que un frontend web
(subida de foto desde el navegador) funcione sin necesidad de tener YOLO instalado
del lado del cliente.

#### Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/api/schemas/detection.py` | `detections` paso a ser `Optional`. Se agrego campo `confidence` (default 0.25) para el umbral de inferencia |
| `src/api/routes/detections.py` | Nueva funcion `_run_inference()` que llama al inference-server via HTTP multipart. Si el request no incluye `detections`, la API las calcula automaticamente |
| `docker-compose.yml` | Nuevo servicio `inference-server` (YOLO + DeepFace). Variable `INFERENCE_SERVER_URL` en servicio `api` |
| `docker-compose.local.yml` | Mismo cambio que en produccion |
| `.env.example` | Agregada documentacion de `INFERENCE_SERVER_URL` |

#### Flujo nuevo (modo orquestador)

```
Frontend/CLI → POST /api/detections (imagen cruda, sin detecciones)
  → API recibe la imagen
  → API llama a inference-server:8000/infer (YOLO)
  → Inference-server devuelve detecciones
  → API guarda imagen en SeaweedFS
  → API persiste frame + detecciones en PostgreSQL
  → API responde con frame_id, image_url, detections_count
```

#### Flujo legacy (compatibilidad hacia atras)

```
CLI tradicional → POST /api/detections (imagen + detecciones pre-calculadas)
  → API persiste directamente (sin llamar a inference-server)
  → Mismo comportamiento que en la primera entrega
```

### 0.4 - Mejora de errores en CLI

| Archivo | Cambio |
|---|---|
| `client/setup_cliente.py` | `cmd_infer()` ahora captura `HTTPError` y `URLError` con mensajes claros. Si el modelo no existe (404), muestra sugerencias de que hacer |

Antes: mostraba un traceback de Python feo.
Ahora:
```
  -> Error: Modelo 'modelo_inventado.pt' no encontrado en el contenedor local.
  -> Asegurate de haberlo descargado con: python3 setup_cliente.py install
  -> Tambien podes probar con el comando 'process' que usa la API en la nube.
```

### Nuevo comando `process` en CLI

Permite enviar una imagen directamente a la API para que ella haga toda la
inferencia en la nube, sin necesidad de tener el inference-server local.

```bash
python3 setup_cliente.py process foto.jpg --model yolo11n.pt
```

Diferencias con `infer`:

| Aspecto | `infer` | `process` |
|---|---|---|
| Donde corre YOLO | Tu PC (contenedor local) | Servidor en la nube (VM) |
| Requiere Docker local | Si | No |
| Velocidad | Mas rapido (local) | Depende de la VM |
| Uso tipico | Desarrollo, pruebas | Frontend web, produccion |

---

## Que necesita la VM (cambios en el servidor)

### 1. Rebuildear y levantar servicios

```bash
docker compose up -d --build api inference-server
```

Esto va a:
- Descargar la imagen `tfunes/inference-server:latest` (si no existe)
- Crear un volumen `face_weights` para los pesos de DeepFace
- Montar `./models/local/` en `/app/models/` dentro del inference-server
- Conectar `inference-server` a la red `api-detection-net`
- La API va a poder llamar a `http://inference-server:8000/infer`

### 3. Verificar que funciona

```bash
# Health check del inference-server
curl http://localhost:8001/health
# o via Docker
docker exec yolo_inference_server curl http://localhost:8000/health
```

### 4. Modelos YOLO

El inference-server necesita los modelos `.pt` en `./models/local/`. Si ya
estan ahi por montarse en el volumen de la API, tambien estaran disponibles
para el inference-server.

---

## Que se puede probar y como

### Prueba 1: API responde (sin autenticacion, si Keycloak no esta activo)

```bash
curl -X POST https://bfts2026.mooo.com/api/detections \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'$(base64 -w0 ~/foto.jpg)'",
    "model_id": "yolo11n.pt",
    "latitude": -34.6037,
    "longitude": -58.3816,
    "confidence": 0.25,
    "metadata": {
      "camera_id": "test",
      "source": "test-manual"
    }
  }'
```

Respuesta esperada:
```json
{
  "frame_id": "uuid",
  "image_url": "https://...",
  "detections_count": 3,
  "status": "processed",
  "message": "Se procesaron 3 detecciones",
  "timestamp": "..."
}
```

### Prueba 2: CLI modo process

```bash
python3 setup_cliente.py process ~/foto.jpg --model yolo11n.pt
```

### Prueba 3: Compatibilidad hacia atras (CLI modo infer tradicional)

```bash
python3 setup_cliente.py infer ~/foto.jpg --model yolo11n.pt
```

### Prueba 4: Error handling

```bash
python3 setup_cliente.py infer ~/foto.jpg --model modelo_inexistente.pt
```

Debe mostrar mensaje claro, NO traceback.

---

## Dependencias con otros miembros

| Depende de | Por que |
|---|---|
| **Miembro C (Keycloak)** | Si Keycloak esta activo, todas las pruebas via curl requieren token JWT |
| **Miembro B (Frontend)** | El frontend necesita que el endpoint orquestador funcione para poder subir imagenes |
| **Miembro A** | No tiene dependencia directa |

Si Keycloak ya esta implementado, las pruebas con curl requieren:

```bash
# Obtener token
TOKEN=$(curl -s -X POST https://bfts2026.mooo.com/auth/realms/api-detection/protocol/openid-connect/token \
  -d "client_id=api-backend" \
  -d "username=admin" \
  -d "password=admin123" \
  -d "grant_type=password" | jq -r '.access_token')

# Usar token
curl -X POST https://bfts2026.mooo.com/api/detections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{...}'
```

---

## Resumen de archivos tocados

```
MODIFICADOS:
  src/api/schemas/detection.py       (detections opcional, confidence)
  src/api/routes/detections.py       (_run_inference(), inferencia orquestada)
  docker-compose.yml                 (servicio inference-server + env var)
  docker-compose.local.yml           (servicio inference-server + env var)
  .env.example                       (documentacion INFERENCE_SERVER_URL)
  client/setup_cliente.py            (error handling cmd_infer, comando process)

NUEVOS:
  Ninguno. Solo modificaciones sobre archivos existentes.
```
