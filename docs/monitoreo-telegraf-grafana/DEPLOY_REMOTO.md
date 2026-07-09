# Deploy Remoto

Este documento explica como desplegar el stack completo (API + monitoreo) en el servidor remoto `bfts2026.mooo.com`.

## Prerrequisitos

- Acceso SSH configurado al remoto (usuario `iwei4a2o25`)
- Docker y Docker Compose instalados en el remoto
- Directorio `/home/iwei4a2o25/API-de-Deteccion-Visual` existente en el remoto
- `.env` configurado con variables de produccion (NO usar `.env` local tal cual)
- Puerto 22 abierto en el firewall del remoto

## Metodo 1: Script Automatico (Recomendado)

```bash
bash docker/monitoring/deploy_monitoring_remoto.sh
```

### Que hace paso a paso

1. **Build local**: reconstruye `api-de-deteccion-visual-api` con los cambios mas recientes
2. **Rsync**: sube al remoto los archivos necesarios:
   - `docker-compose.yml`
   - `Dockerfile.api`
   - `requirements.txt`
   - `docker/nginx.conf`
   - `docker/telegraf.conf`
   - `docker/grafana/` (provisioning completo: datasource y dashboards)
   - `src/` (codigo de la API)
   - `src/api/routes/metrics.py` (metricas Prometheus)
   - `.env`
3. **Crea volumenes** en el remoto si no existen:
   - `influxdb2_data`
   - `influxdb2_config`
   - `grafana_data`
4. **Reconstruye y levanta servicios** en remoto via `docker compose up -d`
5. **Reinicia nginx** para que tome la location `/grafana/`
6. **Corre tests basicos** via SSH para verificar

### Que esperar

```
[...]
================================================
 Tests de Monitoreo - REMOTO
================================================
...
Total:  22
Pasados: 22
Fallados: 0
================================================
Deploy completado en bfts2026.mooo.com
```

## Metodo 2: Manual paso a paso

Si el script falla o quieres hacerlo manualmente:

```bash
# 1. Buildear imagen localmente
docker compose -f docker-compose.local.yml build api

# 2. Subir archivos al remoto
rsync -avz --delete \
  docker-compose.yml \
  Dockerfile.api \
  requirements.txt \
  docker/nginx.conf \
  docker/telegraf.conf \
  docker/grafana/ \
  src/ \
  .env \
  iwei4a2o25@bfts2026.mooo.com:~/API-de-Deteccion-Visual/

# 3. Conectarse al remoto y desplegar
ssh iwei4a2o25@bfts2026.mooo.com
cd ~/API-de-Deteccion-Visual

# 4. Crear volumenes si no existen
mkdir -p volumes/influxdb2_data volumes/influxdb2_config volumes/grafana_data

# 5. Reconstruir y levantar servicios
docker compose build api
docker compose up -d influxdb telegraf grafana api
docker compose restart nginx

# 6. Verificar
curl -s https://bfts2026.mooo.com/metrics | head -5
curl -s https://bfts2026.mooo.com/grafana/api/health
```

## Verificacion Post-Deploy

```bash
# Test rapido de metricas
curl -s https://bfts2026.mooo.com/metrics | grep api_requests_total

# Health check
curl -s https://bfts2026.mooo.com/api/health

# Grafana responde?
curl -s -o /dev/null -w "%{http_code}" https://bfts2026.mooo.com/grafana/

# Tests completos (ejecutar desde local)
bash docker/monitoring/test_monitoring_remoto.sh
```

## Archivos que se suben al remoto

| Archivo | Proposito |
|---------|-----------|
| `docker-compose.yml` | Orquestacion de servicios (produccion) |
| `Dockerfile.api` | Build de la API |
| `requirements.txt` | Dependencias Python |
| `docker/nginx.conf` | Proxy reverso con location `/grafana/` |
| `docker/telegraf.conf` | Config de Telegraf (scrapea metricas) |
| `docker/grafana/provisioning/datasources/datasource.yml` | Datasource InfluxDB auto-provisionado |
| `docker/grafana/provisioning/dashboards/dashboards.yml` | Auto-provisioning de dashboards |
| `docker/grafana/provisioning/dashboards/soa_dashboards.json` | Dashboard con 8 paneles |
| `src/api/routes/metrics.py` | Endpoint /metrics con metricas Prometheus |
| `.env` | Variables de entorno (produccion) |

## Notas Importantes

- El `.env` del remoto debe tener valores de produccion (passwords fuertes, etc.)
- Los certificados SSL deben estar vigentes (Let's Encrypt se renueva automaticamente)
- El firewall del remoto debe tener puertos 80 y 443 abiertos
- El remoto usa `docker-compose.yml` (sin sufijo `.local`), que NO mapea puertos al host para influxdb/telegraf/grafana — solo se acceden via Nginx
- Grafana en remoto se accede solo por `https://bfts2026.mooo.com/grafana/`, NO por puerto directo
