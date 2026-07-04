# Fase de Monitoreo: Telegraf + InfluxDB + Grafana

## Arquitectura

```
                        ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
                        │   FastAPI    │────▶│   Telegraf   │────▶│   InfluxDB   │
                        │  /metrics    │     │  scrape 10s  │     │   2.x (v2)   │
                        │  /health     │     │  sistema     │     │  bucket:     │
                        └──────────────┘     │  cpu/mem/disk│     │  "metrics"   │
                                              └──────────────┘     └──────┬───────┘
                                                                          │
                                                                          ▼
                                                              ┌──────────────────┐
                                                              │     Grafana      │
                                                              │  datasource:     │
                                                              │  InfluxDB_SOA    │
                                                              │  dashboard:      │
                                                              │  "API Deteccion  │
                                                              │  Visual -        │
                                                              │  Monitoreo"      │
                                                              │  8 paneles       │
                                                              └──────────────────┘
```

## Flujo de Datos

1. **FastAPI** exporta metricas en `/metrics` (formato Prometheus) usando `prometheus_client`
2. **Telegraf** scrapea `/metrics` cada 10s, tambien recolecta metricas del sistema (cpu, mem, disk, net, system)
3. **Telegraf** escribe todo a **InfluxDB** en el bucket `metrics`
4. **Grafana** lee de InfluxDB y muestra el dashboard "API Deteccion Visual - Monitoreo"

## Servicios Agregados

### InfluxDB 2.8
- Puerto: 8086
- Bucket: `metrics`
- Org: `soa`
- Token: `soa-token` (configurable via `INFLUXDB_TOKEN`)
- Healthcheck: `influx ping` cada 30s
- Volumenes: `influxdb2_data`, `influxdb2_config`

### Telegraf 1.38
- Scrapea `http://api:8000/metrics` cada 10s (metricas Prometheus)
- Healthcheck via `http://api:8000/health` con `inputs.http_response`
- Recolecta: cpu, mem, disk, diskio, net, system, processes
- Escribe a InfluxDB via `outputs.influxdb_v2`
- Usa variable `INFLUXDB_TOKEN` para autenticacion

### Grafana (latest)
- Puerto: 3000
- Accesible via Nginx en `/grafana/`
- User/Password: `admin` / `admin123` (configurable)
- Datasource InfluxDB auto-provisionado
- Dashboard "API Deteccion Visual - Monitoreo" auto-provisionado con 8 paneles

## Metricas Exportadas por la API

Definidas en `src/api/routes/metrics.py`:

| Metrica | Tipo | Labels | Descripcion |
|---------|------|--------|-------------|
| `api_requests_total` | Counter | endpoint, method, http_status | Total de requests HTTP |
| `inference_time_seconds` | Histogram | (ninguno) | Tiempo de inferencia (buckets: 0.05s a 10s) |
| `face_recognition_total` | Counter | result (success/failure) | Total de reconocimientos faciales |
| `detections_total` | Counter | (ninguno) | Total de detecciones ejecutadas |

El middleware `count_requests` en `main.py` incrementa `api_requests_total` en cada request.

## Dashboard de Grafana (8 paneles)

| Panel | Tipo | Descripcion |
|-------|------|-------------|
| Carga del Sistema | Timeseries | Load average (load1) |
| Disponibilidad del Servicio | Gauge | % disponibilidad 24h |
| Estado Actual | Stat | ONLINE / OFFLINE |
| Uso de Recursos | Gauge | CPU, Memoria, Disco (%) |
| Requests por Minuto | Timeseries | Requests totales por minuto |
| Tiempo de Inferencia | Timeseries | Histograma de inferencia |
| Reconocimientos Faciales | Stat | Exitosos vs Fallidos |
| Uptime | Stat | Tiempo de actividad del sistema |

## Archivos de Configuracion

| Archivo | Descripcion |
|---------|-------------|
| `src/api/routes/metrics.py` | Endpoint /metrics y definicion de metricas |
| `docker/telegraf.conf` | Configuracion de Telegraf (inputs + output) |
| `docker/grafana/provisioning/datasources/datasource.yml` | Datasource InfluxDB |
| `docker/grafana/provisioning/dashboards/dashboards.yml` | Auto-provisioning de dashboards |
| `docker/grafana/provisioning/dashboards/soa_dashboards.json` | Dashboard con 8 paneles |
| `docker/monitoring/test_monitoring.sh` | Tests locales (24 tests) |
| `docker/monitoring/test_monitoring_remoto.sh` | Tests remotos via SSH (22 tests) |
| `docker/monitoring/deploy_monitoring_remoto.sh` | Deploy automatico al remoto |

## Nginx

Location `/grafana/` agregada en ambos:
- `docker/nginx.local.conf` (local)
- `docker/nginx.conf` (remoto)

```nginx
location /grafana/ {
    proxy_pass http://grafana:3000/;
}
```

## Docker Compose

Servicios agregados a `docker-compose.yml` (remoto) y `docker-compose.local.yml` (local):

- `influxdb` - almacenamiento de metricas
- `telegraf` - recoleccion de metricas
- `grafana` - visualizacion

Dependencias: telegraf espera a influxdb healthy y api started; grafana espera a influxdb started.

## Variables de Entorno

Definidas en `.env` y `.env.example`:

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `INFLUXDB_USERNAME` | admin | Usuario admin de InfluxDB |
| `INFLUXDB_PASSWORD` | admin123 | Password admin de InfluxDB |
| `INFLUXDB_TOKEN` | soa-token | Token de acceso para Telegraf y Grafana |
| `INFLUXDB_ORG` | soa | Organizacion en InfluxDB |
| `INFLUXDB_BUCKET` | metrics | Bucket de metricas |
| `INFLUXDB_RETENTION` | 30d | Retencion de datos |
| `GRAFANA_USER` | admin | Usuario admin de Grafana |
| `GRAFANA_PASSWORD` | admin123 | Password admin de Grafana |
| `HOSTNAME` | api-detection | Hostname para Telegraf |

## Acceso a Interfaces

### Local
| Servicio | URL |
|----------|-----|
| Grafana | http://localhost:3000/ o http://localhost/grafana/ |
| InfluxDB | http://localhost:8086/ |
| API /metrics | http://localhost:8000/metrics |
| Swagger | http://localhost/api/docs |

### Remoto (bfts2026.mooo.com)
| Servicio | URL |
|----------|-----|
| Grafana | https://bfts2026.mooo.com/grafana/ |
| API /metrics | https://bfts2026.mooo.com/metrics |

## Decisiones Tecnicas

- **prometheus_client** para exportar metricas en formato Prometheus (estandar)
- **Telegraf scrapea en lugar de push**: Telegraf hace pull de `/metrics`, no requiere que la API envie datos
- **InfluxDB 2.x con token auth**: Telegraf escribe con token, Grafana lee con token
- **Grafana auto-provisionado**: datasource y dashboard definidos como archivos YAML/JSON, sobreviven reinicios
- **`/metrics` endpoint publico**: no requiere JWT para que Telegraf pueda scrapear sin token
- **8 paneles en dashboard**: cubren sistema, API, detecciones y reconocimiento facial
