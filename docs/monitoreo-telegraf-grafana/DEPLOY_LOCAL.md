# Guia Rapida Local

## Prerrequisitos

- Docker y Docker Compose (plugin v2) instalados
- Git
- Puerto 80, 5432, 8080, 8086, 3000, 9333 libres en el host

## Pasos

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd API-de-Deteccion-Visual

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Revisar .env (opcional)
# Valores por defecto funcionan para entorno local

# 4. Crear directorios de volumenes
mkdir -p volumes/postgres volumes/seaweed volumes/influxdb volumes/grafana

# 5. Levantar todos los servicios
docker compose -f docker-compose.local.yml up -d

# 6. Verificar que todo este funcionando
docker compose -f docker-compose.local.yml ps

# 7. Ejecutar tests de monitoreo
bash docker/monitoring/test_monitoring.sh

# 8. Probar health check de la API
curl http://localhost/api/health
```

## Acceso a Servicios

| Servicio | URL Local | Credenciales |
|----------|-----------|--------------|
| API (Swagger) | http://localhost/api/docs | - |
| API (Health) | http://localhost/api/health | - |
| API Metrics | http://localhost:8000/metrics | - |
| Grafana | http://localhost/grafana/ | admin / admin123 |
| Grafana (directo) | http://localhost:3000/ | admin / admin123 |
| InfluxDB | http://localhost:8086/ | admin / admin123 |
| pgAdmin | http://localhost/pgadmin/ | admin@bfts2026.mooo.com / bfts2026. |
| SeaweedFS Master | http://localhost:9333/ | - |
| SeaweedFS Volume | http://localhost:8080/ | - |

## Comandos Utiles

```bash
# Ver logs de un servicio
docker compose -f docker-compose.local.yml logs -f api

# Solo servicios de monitoreo
docker compose -f docker-compose.local.yml ps influxdb telegraf grafana

# Detener todo
docker compose -f docker-compose.local.yml down

# Detener y borrar volumenes (ADVERTENCIA: pierde datos)
docker compose -f docker-compose.local.yml down -v

# Reconstruir imagen de la API tras cambios
docker compose -f docker-compose.local.yml build api

# Entrar a un contenedor
docker exec -it api_detection_api_local bash
```

## Estructura de Directorios

```
.
├── docker-compose.local.yml   # Orquestacion local
├── docker/
│   ├── nginx.local.conf        # Proxy reverso local
│   ├── telegraf.conf           # Config Telegraf
│   └── grafana/provisioning/   # Dashboards auto
├── src/api/                    # Codigo fuente API
├── models/                     # Modelos YOLO
└── docs/                       # Documentacion
```
