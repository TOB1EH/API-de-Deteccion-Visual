# Sugerencia de Nuevos Markdowns

Basado en el estado actual del proyecto, estos markdowns adicionales serian de utilidad:

## 1. `DEPLOY_LOCAL.md` - Guia Rapida Local
Un "getting started" de 1 pagina que cubra:
- Clonar repo
- `cp .env.example .env`
- `docker compose -f docker-compose.local.yml up -d`
- Verificar con `bash docker/monitoring/test_monitoring.sh`
- Acceder a servicios (Grafana, API, Swagger)

## 2. `API_REFERENCE.md` - Referencia de Endpoints
Documentar todos los endpoints del API:
- `GET /api/health` - Health check
- `GET /api/models` - Listar modelos (S1)
- `POST /api/detections` - Ejecutar deteccion (S2)
- `GET /api/frames/{frameId}` - Obtener fotograma (S3)
- `GET /api/frames/search` - Buscar fotogramas (S4)
- `POST /api/persons` - Crear persona (S5.1)
- `POST /api/persons/{personId}/embeddings` - Generar embeddings (S5.2)
- `POST /api/face-recognition` - Reconocimiento facial (S5.3)
- `GET /metrics` - Metricas Prometheus
Incluir ejemplos con curl para cada uno.

## 3. `CHANGELOG.md` - Registro de Cambios
Formato de changelog con fechas y descripcion de cada fase completada:
- Fase 1: Infraestructura (PostgreSQL, SeaweedFS, Nginx, SSL)
- Fase 2: Endpoints S1-S2
- Fase 3: Endpoints S3-S4
- Fase 4: Monitoreo (Telegraf, InfluxDB, Grafana)
- Fase 5: Reconocimiento facial

## 4. `ENV_REFERENCE.md` - Referencia Completa de Variables de Entorno
Tabla completa de todas las variables de entorno, su proposito, valores por defecto, y en que servicio se usan. Mas detallada que `.env.example`.

## 5. `GRAFANA_DASHBOARDS.md` - Personalizar Dashboards
Guia de como:
- Crear nuevos paneles en Grafana
- Escribir queries Flux
- Agregar alertas
- Compartir dashboards
- Importar dashboards desde JSON

## 6. `METRICAS_CUSTOM.md` - Agregar Nuevas Metricas
Guia de como extender `metrics.py` con nuevas metricas:
- Contadores custom
- Histogramas con buckets personalizados
- Labels y tagging
- Como hacer que aparezcan en el dashboard de Grafana

## Prioridad Sugerida

1. `DEPLOY_LOCAL.md` - util para cualquier desarrollador nuevo
2. `CHANGELOG.md` - necesario para auditoria/entregas
3. `API_REFERENCE.md` - util para testing con curl/Postman
4. `ENV_REFERENCE.md` - evita confusiones con configuracion
5. Los demas segun necesidad
