# Troubleshooting de Monitoreo

## El dashboard de Grafana no muestra datos

**Causas posibles:**
- InfluxDB no esta recibiendo datos de Telegraf
- La query Flux no coincide con los measurements/fields
- El datasource apunta a la URL incorrecta

**Verificar:**
```bash
# 1. Telegraf escribe a InfluxDB?
docker exec api_detection_telegraf_local telegraf --test --input-filter prometheus 2>&1 | head -20

# 2. InfluxDB tiene datos?
docker exec api_detection_influxdb_local influx query '
  from(bucket: "metrics")
  |> range(start: -10m)
  |> limit(n: 5)
' --org soa --token soa-token

# 3. Datasource apunta a influxdb:8086?
docker exec api_detection_grafana_local cat /etc/grafana/provisioning/datasources/datasource.yml
```

## Telegraf no arranca

**Verificar:**
```bash
docker logs api_detection_telegraf_local 2>&1 | tail -30
docker exec api_detection_telegraf_local telegraf --config /etc/telegraf/telegraf.conf --test 2>&1
```

**Posibles causas:**
- Token incorrecto (revisar `INFLUXDB_TOKEN` en `.env`)
- InfluxDB no reachable (revisar red Docker)
- API no responde en `http://api:8000/metrics`

## Grafana no responde en /grafana/

**Verificar:**
```bash
# Grafana escucha?
curl -s http://localhost:3000/api/health

# Nginx proxy correcto?
grep -A5 'location /grafana/' docker/nginx.local.conf

# Logs de nginx
docker logs api_detection_nginx_local 2>&1 | tail -20
```

## InfluxDB no arranca

**Verificar:**
```bash
docker logs api_detection_influxdb_local 2>&1 | tail -20
docker inspect api_detection_influxdb_local --format='{{.State.Status}}'
```

**Posibles causas:**
- Token ya existia en un setup previo (incoherencia)
- Solucion: borrar volumen y recrear
```bash
docker compose -f docker-compose.local.yml down influxdb
docker volume rm api-de-deteccion-visual_influxdb2_data
docker compose -f docker-compose.local.yml up -d influxdb
```

## Metricas de prometheus no aparecen en InfluxDB

**Verificar:**
```bash
# La API exporta metricas?
curl -s http://localhost:8000/metrics | head -20

# Telegraf puede scrapear?
docker exec api_detection_telegraf_local wget -q -O- http://api:8000/metrics 2>&1 | head -5
```

## Puertos ocupados

Si el puerto 3000 (Grafana) o 8086 (InfluxDB) estan ocupados en el host:
- Cambiar el `ports:` mapping en `docker-compose.local.yml`
- Nota: Grafana en el remoto no necesita mapeo de puertos (usa Nginx)

## Tests fallan

**Ejecutar tests en modo verbose:**
```bash
bash -x docker/monitoring/test_monitoring.sh 2>&1 | grep -E '(FAIL|ERROR|Test)'
```

## Reset completo del stack de monitoreo local

```bash
docker compose -f docker-compose.local.yml down influxdb telegraf grafana
docker volume rm api-de-deteccion-visual_influxdb2_data api-de-deteccion-visual_influxdb2_config
docker compose -f docker-compose.local.yml up -d influxdb telegraf grafana
sleep 10
bash docker/monitoring/test_monitoring.sh
```
