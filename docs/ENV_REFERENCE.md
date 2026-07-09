# Referencia Completa de Variables de Entorno

## Base de Datos (PostgreSQL)

| Variable | Default | Descripcion | Usado en |
|----------|---------|-------------|----------|
| `POSTGRES_DB` | api_detection | Nombre de la base de datos | postgres, api |
| `POSTGRES_USER` | api_user | Usuario de BD | postgres, api |
| `POSTGRES_PASSWORD` | api_password | Password de BD | postgres, api |
| `DATABASE_URL` | postgresql+asyncpg://api_user:api_password@postgres:5432/api_detection | URL de conexion (asincrona) | api |
| `POSTGRES_HOST` | postgres | Host del contenedor postgres | api |
| `POSTGRES_PORT` | 5432 | Puerto de postgres | api |

## Almacenamiento (SeaweedFS)

| Variable | Default | Descripcion | Usado en |
|----------|---------|-------------|----------|
| `SEAWEDF_MASTER` | seaweedfs_master:9333 | Host:puerto del master | api, seaweedfs_master |
| `SEAWEDF_VOLUME` | seaweedfs_volume:8080 | Host:puerto del volume server | api, seaweedfs_volume |
| `SEAWEDF_VOLUME_PORT` | 8080 | Puerto del volume | seaweedfs_volume |

## Monitoreo (InfluxDB)

| Variable | Default | Descripcion | Usado en |
|----------|---------|-------------|----------|
| `INFLUXDB_USERNAME` | admin | Usuario admin de InfluxDB | influxdb |
| `INFLUXDB_PASSWORD` | admin123 | Password admin de InfluxDB | influxdb |
| `INFLUXDB_TOKEN` | soa-token | Token de autenticacion para Telegraf y Grafana | influxdb, telegraf, grafana |
| `INFLUXDB_ORG` | soa | Organizacion en InfluxDB | influxdb, telegraf |
| `INFLUXDB_BUCKET` | metrics | Nombre del bucket de metricas | influxdb, telegraf |
| `INFLUXDB_RETENTION` | 30d | Periodo de retencion de datos | influxdb |

## Monitoreo (Grafana)

| Variable | Default | Descripcion | Usado en |
|----------|---------|-------------|----------|
| `GRAFANA_USER` | admin | Usuario admin de Grafana | grafana |
| `GRAFANA_PASSWORD` | admin123 | Password admin de Grafana | grafana |
| `GF_INSTALL_PLUGINS` | (vacio) | Plugins adicionales a instalar | grafana |

## Monitoreo (Telegraf)

| Variable | Default | Descripcion | Usado en |
|----------|---------|-------------|----------|
| `HOSTNAME` | api-detection | Hostname para etiquetar metricas del sistema | telegraf |

## API (FastAPI)

| Variable | Default | Descripcion | Usado en |
|----------|---------|-------------|----------|
| `API_HOST` | 0.0.0.0 | Host donde escucha FastAPI | api |
| `API_PORT` | 8000 | Puerto donde escucha FastAPI | api |
| `MODELS_DIR` | /app/models | Directorio de modelos YOLO | api |
| `UPLOAD_DIR` | /tmp/uploads | Directorio temporal para uploads | api |
| `LOG_LEVEL` | INFO | Nivel de logging (DEBUG, INFO, WARNING, ERROR) | api |

## Nginx

| Variable | Default | Descripcion | Usado en |
|----------|---------|-------------|----------|
| `NGINX_PORT` | 80 | Puerto HTTP | nginx |
| `NGINX_SSL_PORT` | 443 | Puerto HTTPS | nginx |
| `SERVER_NAME` | bfts2026.mooo.com | Nombre del servidor para SSL | nginx |
