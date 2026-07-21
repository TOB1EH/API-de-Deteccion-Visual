# Guia de Presentacion — Examen Final SOA 2026

## Estructura recomendada (10-15 min)

---

## 1. Introduccion: De donde partimos

**Diapositiva 1 — MVP Entregado (S1 a S5.3)**

Habiamos implementado:
- API REST para deteccion de objetos con YOLO (S2)
- Almacenamiento de frames en SeaweedFS + PostgreSQL (S3, S4)
- CRUD de personas (S5.1)
- Reconocimiento facial basico con DeepFace + OpenCV (S5.2, S5.3)

**Problema critico detectado:** El reconocimiento facial fallaba con fotos de distinto angulo/iluminacion.

---

## 2. Bloque 1 — Mejora del Reconocimiento Facial

**Problema:** DeepFace con `detector_backend="opencv"` (Haar Cascade) solo detectaba rostros frontales. Dos fotos de la misma persona desde angulos distintos producian distancia coseno > 0.99, como si fueran personas diferentes.

**Solucion aplicada (3 cambios):**

| Cambio | Tecnologia | Problema que resuelve |
|---|---|---|
| Detector: opencv -> MTCNN | **MTCNN** (Multi-Task Cascaded CNN) | Detecta rostros en perfiles, angulos, iluminacion variada |
| Normalizacion: base -> Facenet | **Facenet normalization** | Alinea el preprocesamiento con el entrenamiento del modelo |
| Multiples embeddings por persona | **pgvector** + CLI modificado | Subir N fotos por persona -> N puntos de referencia |

**Resultados con Franco Colapinto (4 fotos de referencia):**
- Antes: 0/5 reconocidos
- Despues: 4/5 reconocidos con threshold 0.5
- Mejora: 80% de precision

**Tecnologias:** DeepFace, MTCNN, Facenet, pgvector, YOLO

**Archivos clave:**
- `inference-server/main.py`: detector_backend y normalization
- `client/setup_cliente.py`: `faces embed` ahora acepta directorios
- `src/api/routes/persons.py`: multiples embeddings por persona

---

## 3. Bloque 2 — Autenticacion con Keycloak

**Problema:** La API no tenia control de acceso. Cualquiera con la URL podia detectar objetos, ver frames, modificar personas.

**Solucion:** Keycloak como Identity Provider centralizado.

**Arquitectura implementada:**

```
Request -> Nginx -> FastAPI -> verify_token() -> Keycloak JWKS
                                              -> require_role() -> endpoint
```

**Roles definidos:**
| Rol | Acceso |
|---|---|
| **admin** | CRUD completo: personas, detecciones, embeddings, configuracion |
| **operator** | Subir detecciones, consultar, listar personas (sin modificar) |
| **viewer** | Solo lectura (modelos, frames, detecciones) |

**Tecnologias:** Keycloak 26, OAuth2, JWT, JWKS, RS256, python-jose

**Flujo:**
1. Cliente obtiene token via `/auth/realms/api-detection/protocol/openid-connect/token`
2. Envia token en `Authorization: Bearer <token>`
3. FastAPI valida firma via JWKS de Keycloak (`src/api/services/auth.py`)
4. `require_role()` verifica que el rol tenga permiso

**Archivos clave:**
- `docker-compose.local.yml`: servicio keycloak
- `src/api/services/auth.py`: `verify_token()`, `require_role()`
- `src/api/routes/`: decoradores en cada endpoint

---

## 4. Bloque 3 — Monitoreo (Telegraf + InfluxDB + Grafana)

**Problema:** Sin visibilidad del estado de la API. No se sabia cuantas requests recibia, si estaba caida, ni como respondia.

**Solucion:** Stack completo de monitoreo.

**Arquitectura:**

```
API (Prometheus metrics)  -->  Telegraf (scrape cada 10s)
                                |
                                v
                            InfluxDB (bucket: metrics)
                                |
                                v
                            Grafana (11 paneles)
```

**Que monitorea cada panel:**

| Panel | Metrica | Que mide |
|---|---|---|
| 1 | CPU, RAM, Disco | Estado del servidor |
| 2 | `api_requests_total` | Requests por minuto |
| 3 | `api_requests_total{status=5xx}` | Tasa de errores HTTP |
| 4 | `inference_time_seconds_sum/count` | Tiempo promedio de inferencia YOLO |
| 5 | `detections_total` | Throughput (detecciones/min) |
| 6 | `embedding_time_seconds_sum` | Tiempo de generacion de embeddings |
| 7 | `comparison_time_seconds_sum` | Tiempo de comparacion facial |
| 8 | `face_recognition_total{result=success/failure}` | Reconocimientos exitosos vs fallidos |
| 9 | `inference_server_up` | Estado del nodo local (online/offline) |
| 10 | `process_start_time_seconds` | Uptime del servicio |
| 11 | `face_recognition_total` | Ratio de exito del reconocimiento facial |

**Problemas resueltos durante la implementacion:**
- Oscilacion de contadores por `--workers 2`: solucion con `--workers 1`
- NaN en divisiones post-reinicio: filtro `_value > 0` y guardia `if count > 0`
- Consultas Flux multi-statement no soportadas: refactor a `reduce` de una sola expresion

**Tecnologias:** Prometheus Client, Telegraf, InfluxDB 2.x (Flux), Grafana 11

**Archivos clave:**
- `src/api/routes/metrics.py`: definicion de todas las metricas Prometheus
- `docker/telegraf/telegraf.conf`: configuracion de scrape
- `docker/grafana/provisioning/dashboards/soa_dashboards.json`: dashboard con 11 paneles
- `docker/monitoring/test_monitoring.sh`: 24 tests de integracion

---

## 5. Bloque 4 — Frontend Web

**Problema:** Solo existia un CLI (`setup_cliente.py`). No habia forma de usar el sistema desde el navegador.

**Solucion:** Interfaz web con login, deteccion visual y administracion.

**Funcionalidades:**
- Login con Keycloak OAuth2 (redirect)
- Subir foto para deteccion de objetos con YOLO
- Visualizar resultados con bounding boxes
- Buscar frames por filtros (clase, ubicacion, camara, fecha)
- ABM de personas
- Subir fotos para multiples embeddings
- Reconocimiento facial (subir foto y buscar match)

**Tecnologias:** React (o Vue segun eleccion del equipo), REST API, Keycloak JS adapter

---

## 6. Bloque 5 — Indice IVFFLAT en pgvector

**Problema:** Sin indice, la busqueda de vectores en PostgreSQL escanea toda la tabla secuencialmente. Con miles de embeddings se vuelve lento.

**Solucion:** Indice IVFFLAT (Inverted File with Flat) sobre la columna `embedding`.

**SQL:**
```sql
CREATE INDEX idx_face_embeddings_vector ON face_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Que hace IVFFLAT:** Divide el espacio vectorial en 100 listas (clusters). Al buscar, solo revisa las listas mas cercanas al embedding de consulta, no toda la tabla.

**Trade-off:** Un poco menos de precision (aproximado) a cambio de velocidad O(log N) vs O(N).

---

## 7. Cierre — Stack tecnologico final

```
                    +------------------+
                    |   Frontend UI    |  React/Vue
                    +--------+---------+
                             |
                    +--------v---------+
                    |   Nginx (HTTPS)  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v------+ +----v----+ +-------v------+
     |  FastAPI API  | | pgAdmin | |  SeaweedFS   |
     | + auth.py     | | (Web)   | | (objetos)    |
     +--------+------+ +---------+ +--------------+
              |              |
     +--------v------+ +----v--------+
     |  PostgreSQL   | | InfluxDB    |
     |  + pgvector   | | (metricas)  |
     +---------------+ +-------------+
              |
     +--------v------+
     | inference-srv |  YOLO + DeepFace (Docker local)
     +---------------+
```

**Tecnologias del stack final:**
- **Backend:** Python FastAPI, Uvicorn
- **Deteccion:** Ultralytics YOLO11
- **Reconocimiento facial:** DeepFace (MTCNN + Facenet)
- **Autenticacion:** Keycloak 26 (OAuth2/JWT + RBAC)
- **Base de datos:** PostgreSQL 16 + pgvector (indice IVFFLAT)
- **Almacenamiento:** SeaweedFS (objetos)
- **Monitoreo:** Telegraf + InfluxDB 2.x + Grafana 11
- **Frontend:** React/Vue
- **Proxy:** Nginx + Let's Encrypt SSL
- **Contenedores:** Docker, Docker Compose

---

## Tips para la presentacion

1. **Demo en vivo:** Mostrar el frontend conectado contra la API real. Subir una foto, ver los cuadros de deteccion, buscar una persona, hacer reconocimiento facial.

2. **Antes vs Despues:** Para reconocimiento facial, mostrar la tabla de Franco Colapinto (0/5 -> 4/5). Eso es concreto y entendible.

3. **Monitoreo en accion:** Abrir Grafana mientras se hacen requests desde el frontend. Los paneles se actualizan en vivo.

4. **Keycloak en accion:** Mostrar el login con roles distintos: admin ve boton de crear persona, viewer no.

5. **No mostrar codigo fuente en las diapositivas** a menos que sea una linea clave. Usar diagramas de arquitectura.

6. **Explicar el "por que" de cada decision tecnica**, no solo el "que" hicieron.

7. **Tiempo sugerido por bloque:**
   - Introduccion: 1 min
   - Reconocimiento facial: 3 min
   - Keycloak: 2 min
   - Monitoreo: 3 min
   - Frontend: 2 min
   - Cierre + preguntas: 2-3 min
