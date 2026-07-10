# Scripts de Monitoreo

Los 3 scripts estan en `docker/monitoring/`.

## 1. `test_monitoring.sh` - Tests Locales (24 tests)

Ejecuta tests contra el stack de monitoreo local. No requiere parametros.

```bash
bash docker/monitoring/test_monitoring.sh
```

### Que prueba

| Seccion | Tests | Que verifica |
|---------|-------|-------------|
| Contenedores | 3 | influxdb, telegraf, grafana existen y estan running |
| InfluxDB | 6 | ping, bucket metrics, datos de prometheus/system/cpu/mem |
| Telegraf | 4 | sin errores de prometheus scrape, http_response, output; conectividad con API |
| API /metrics | 4 | endpoint HTTP 200, metricas api_requests_total, inference_time_seconds, detections_total |
| Grafana | 7 | responde en :3000 y via nginx, login page, datasource y dashboard provisionados, paneles con queries a InfluxDB, datasource apunta a influxdb:8086 |

### Exit code
- 0: todos los tests pasaron
- 1: uno o mas tests fallaron

## 2. `test_monitoring_remoto.sh` - Tests Remotos (22 tests)

Ejecuta los mismos tests pero contra el servidor remoto `bfts2026.mooo.com` via SSH.

```bash
bash docker/monitoring/test_monitoring_remoto.sh
```

### Prerrequisitos
- Acceso SSH configurado a `iwei4a2o25@bfts2026.mooo.com`
- Stack de monitoreo desplegado en el remoto

### Que prueba
Mismos tests que el local pero:
- Usa `https://bfts2026.mooo.com/metrics` en lugar de `http://localhost:8000/metrics`
- Usa nombres de contenedor remotos (`api_detection_influxdb` sin sufijo `_local`)
- Verifica archivos de provisionamiento en el remoto
- No prueba datos de cpu/mem en InfluxDB (requiere que el remoto haya estado corriendo suficiente tiempo)

## 3. `deploy_monitoring_remoto.sh` - Deploy Remoto

Construye la imagen API, sube archivos y levanta los servicios de monitoreo en el remoto.

```bash
bash docker/monitoring/deploy_monitoring_remoto.sh
```

### Que hace paso a paso

1. **Build**: reconstruye la imagen `api-de-deteccion-visual-api` localmente
2. **Sube archivos via rsync**:
   - `docker-compose.yml`
   - `Dockerfile.api`
   - `requirements.txt`
   - `docker/nginx.conf`
   - `docker/telegraf.conf`
   - `docker/grafana/` (provisioning completo)
   - `src/`, `models/`, `client/`
   - `.env`
3. **Crea directorios** de volumenes en remoto (`influxdb2_data`, `influxdb2_config`, `grafana_data`)
4. **Reconstruye API** y levanta `influxdb`, `telegraf`, `grafana` en remoto
5. **Reinicia nginx** en remoto
6. **Corre tests basicos** via SSH

### Prerrequisitos
- Llave SSH configurada sin password
- Docker y Docker Compose instalados en el remoto
- Directorio `/home/iwei4a2o25/API-de-Deteccion-Visual` existente

## Salida Tipica (todos OK)

```
================================================
 Tests de Monitoreo: InfluxDB + Telegraf + Grafana
 Fecha: vie 03 jul 2026 20:58:47 -03
 Proyecto: API-de-Deteccion-Visual
================================================

--- 1. Contenedores ---
[INFO]  Test #1: ...
[OK]    influxdb: status=running, health=healthy
...

--- 5. Grafana ---
...
================================================
 RESULTADOS
================================================
 Total:  24
 Pasados: 24
 Fallados: 0
================================================
```
