# AGENTS.md

## Directivas
- Respuestas en español. Sin emojis.

## Estado del repositorio

### Fase 1: Infraestructura - COMPLETADA ✓

El repo contiene:
- `docker-compose.yml` -- servicios base (PostgreSQL + pgvector, SeaweedFS, Nginx, pgAdmin)
- `docker/nginx.conf` -- proxy reverso HTTPS, locations para `/api/`, `/pgadmin/`, `/seaweed/`, `/seaweed-master/`
- `.env.example` -- plantilla de variables de entorno
- `validate_local.sh` -- script de validación de servicios
- `FASE1_INFRAESTRUCTURA.md` -- guía completa local + remota
- `PRIMERA_ENTREGA.md` -- alcance detallado del MVP (entrega **9/6/2026**)
- `Trabajo Integrador SOA 2026.pdf` -- especificación completa
- `fases_api_deteccion_visual.md` -- plan de fases para implementación

### Infraestructura actual

**Local + Remota (bfts2026.mooo.com):**
- PostgreSQL 16 + pgvector: 5432 ✓
- SeaweedFS Master: 9333 ✓
- SeaweedFS Volume: 8080 ✓
- Nginx (proxy reverso): 80 → 443 (HTTPS) ✓
- pgAdmin: /pgadmin/ ✓
- Red Docker aislada: api-detection-net ✓
- Certificados Let's Encrypt: activos ✓
- Firewall UFW: configurado ✓

### Próxima: Fase 2 - Endpoint S1 (GET `/models`)

## Servicios (endpoints exactos)

| # | Método | Ruta | Descripción | Estado |
|---|--------|------|-------------|--------|
| S1 | GET | `/api/models` | Lista modelos desde carpeta local | Pendiente |
| S2 | POST | `/api/detections` | Ejecuta detección sobre fotograma | Pendiente |
| S3 | GET | `/api/frames/{frameId}?thumbnail=true` | Obtiene fotograma | Pendiente |
| S4 | GET | `/api/frames/search?clases=&lat=&lon=` | Consulta y filtrado | Pendiente |
| S5.1 | POST | `/api/persons` | Crear persona | Pendiente |
| S5.1 | GET | `/api/persons/{personId}` | Obtener persona | Pendiente |
| S5.2 | POST | `/api/persons/{personId}/embeddings` | Generar embeddings faciales | Pendiente |
| S5.3 | POST | `/api/face-recognition` | Reconocimiento facial | Pendiente |

Todos los endpoints se sirven a través de `https://bfts2026.mooo.com/api/` vía Nginx proxy reverso.

## Decisiones técnicas DEFINIDAS

### Infraestructura (Fase 1)
- **Base de datos:** PostgreSQL 16 + pgvector (búsqueda vectorial nativa)
- **Almacenamiento de objetos:** SeaweedFS (distribuido, escalable, auto-replicación)
- **Proxy reverso:** Nginx (puerto 443 HTTPS, redirección de locations)
- **Certificados SSL:** Let's Encrypt con auto-renovación vía Certbot
- **Contenedorización:** Docker Compose v3.9 con red aislada
- **Gestión BD remota:** pgAdmin (accesible en `/pgadmin/` vía HTTPS)

### Decisiones pendientes (definir antes de Fase 2)
- **Lenguaje API:** Python (FastAPI/Flask), Node.js (Express), o Java (Spring Boot)
- **Modelo de detección:** YOLO (yolo11n.pt, yolo11s.pt) u otro
- **Librería reconocimiento facial:** face_recognition, FaceNet, DeepFace, o similar

## Hechos duros (sin cambios)

- **S2 es el núcleo.** Entrada: imagen + lat/lon (obligatorio) + modelId. Persiste: imagen (SeaweedFS), metadatos + detecciones (PostgreSQL). Todo vinculado a un `frameId` único.
- **S5.3:** threshold default `0.8`. Solo retorna persona si confidence > threshold.
- Sin interfaz gráfica. Todo REST. Validar con curl/Postman.
- Identificadores únicos: `frameId`, `personId`, `detectionId`.
- Procesamiento asíncrono en S2: opcional pero valorado.
- Búsqueda vectorial (embeddings): pgvector (PostgreSQL nativo).
- Todos los endpoints detrás de Nginx en `/api/` con HTTPS obligatorio.

## Acceso Remoto desde el Host Local

### pgAdmin (Gestión PostgreSQL)
```
https://bfts2026.mooo.com/pgadmin/
Email: admin@bfts2026.mooo.com
Contraseña: bfts2026.
```

### Health Check API
```
https://bfts2026.mooo.com/
Respuesta: "API Detection Service OK"
```

### SeaweedFS (Storage)
```
https://bfts2026.mooo.com/seaweed/       (Volume - almacenamiento)
https://bfts2026.mooo.com/seaweed-master/ (Master - estado)
```

## Stack de Desarrollo

| Capa | Tecnología | Versión | Notas |
|---|---|---|---|
| HTTPS | Let's Encrypt | Automático | Certificados instalados en /etc/letsencrypt |
| Proxy | Nginx | 1.31.1 | Redirecciona HTTP 80 → HTTPS 443 |
| API Backend | TBD | - | Escucha en localhost:8000, proxeado en /api/ |
| BD | PostgreSQL + pgvector | 16 | Búsqueda vectorial nativa, volumen persistente |
| Storage | SeaweedFS | Latest | Distribuido, escalable, volumen persistente |
| Gestión BD | pgAdmin | Latest | Interfaz web para PostgreSQL, en /pgadmin/ |
| Contenedores | Docker Compose | 3.9 | Red aislada api-detection-net |
| Firewall | UFW | - | SSH 22, HTTP 80, HTTPS 443, PostgreSQL 5432, SeaweedFS 9333/8080 |

## Próximas Fases (Roadmap)

1. **Fase 2:** Endpoint S1 (GET `/models`) - Listar modelos YOLO disponibles
2. **Fase 3:** Endpoint S2 (POST `/detections`) - Ejecutar detección, persistencia
3. **Fase 4:** Endpoints S3-S4 (GET `/frames/`) - Recuperar y filtrar fotogramas
4. **Fase 5:** Endpoints S5 (personas + reconocimiento facial) - Embeddings, similarity search

## Referencias y Enlaces

- **Docker Compose:** https://docs.docker.com/compose/
- **PostgreSQL + pgvector:** https://github.com/pgvector/pgvector
- **SeaweedFS:** https://github.com/seaweedfs/seaweedfs
- **pgAdmin:** https://www.pgadmin.org/
- **Let's Encrypt + Certbot:** https://letsencrypt.org/
- **Nginx Proxy:** https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- **Especificación del proyecto:** Ver `PRIMERA_ENTREGA.md` y `Trabajo Integrador SOA 2026.pdf`
- **Guía Infraestructura:** Ver `FASE1_INFRAESTRUCTURA.md`
