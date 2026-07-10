# Changelog

## [1.4.0] - 2026-07-03

### Agregado
- Monitoreo completo con Telegraf + InfluxDB + Grafana
- Endpoint `/metrics` con metricas Prometheus (requests, inferencia, detecciones, reconocimiento facial)
- Dashboard de Grafana con 8 paneles (carga del sistema, disponibilidad, recursos, requests, inferencia, reconocimientos, uptime)
- Auto-provisioning de datasource y dashboard en Grafana
- Scripts: `test_monitoring.sh` (24 tests locales), `test_monitoring_remoto.sh` (22 tests remotos), `deploy_monitoring_remoto.sh`
- Location `/grafana/` en Nginx

### Cambiado
- Keycloak eliminado completamente del stack
- `auth.py` simplificado sin dependencia JWT
- `python-jose` removido de `requirements.txt`

## [1.3.0] - 2026-06-09

### Agregado
- S5.1: Crear y obtener personas (`POST/GET /api/persons`)
- S5.2: Generar embeddings faciales (`POST /api/persons/{personId}/embeddings`)
- S5.3: Reconocimiento facial con threshold configurable (`POST /api/face-recognition`)
- Búsqueda vectorial con pgvector
- `Dockerfile.face_api` para servicios faciales

## [1.2.0] - 2026-06-02

### Agregado
- S3: Obtener fotogramas con thumbnail (`GET /api/frames/{frameId}`)
- S4: Busqueda y filtrado de fotogramas (`GET /api/frames/search`)
- Almacenamiento en SeaweedFS

## [1.1.0] - 2026-05-26

### Agregado
- S1: Listar modelos disponibles (`GET /api/models`)
- S2: Ejecutar deteccion YOLO (`POST /api/detections`)
- Persistencia en PostgreSQL
- Procesamiento asincrono de detecciones

## [1.0.0] - 2026-05-19

### Agregado
- Infraestructura base con Docker Compose
- PostgreSQL 16 + pgvector
- SeaweedFS (Master + Volume)
- Nginx con HTTPS (Let's Encrypt)
- pgAdmin para gestion de BD
- Red Docker aislada `api-detection-net`
- Certificados SSL con auto-renovacion
- Firewall UFW configurado
- Script de validacion `validate_local.sh`
- Documentacion inicial (FASE1_INFRAESTRUCTURA.md, PRIMERA_ENTREGA.md)
