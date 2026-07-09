# Agregar Nuevas Metricas Custom

## 1. Definir la metrica en `src/api/routes/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge

# Contador: cuenta eventos
DB_QUERY_TIME = Histogram(
    "db_query_time_seconds",
    "Tiempo de consultas a la base de datos",
    ["query_type"],  # label: select, insert, update, delete
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0],
)

# Gauge: valor que sube y baja
ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Conexiones activas actuales",
)

# Contador simple (sin labels)
PROCESSED_IMAGES = Counter(
    "processed_images_total",
    "Total de imagenes procesadas",
)
```

## 2. Usar la metrica en el codigo

```python
# En tu ruta o servicio:
from api.routes.metrics import DB_QUERY_TIME, ACTIVE_CONNECTIONS, PROCESSED_IMAGES

# Histogram: medir tiempo de operacion
with DB_QUERY_TIME.labels(query_type="select").time():
    results = await db.execute(query)

# Gauge: setear valor actual
ACTIVE_CONNECTIONS.set(current_connections)

# Counter: incrementar
PROCESSED_IMAGES.inc()
```

### Tipos de metricas Prometheus

| Tipo | Cuando usarlo | Metodo |
|------|---------------|--------|
| `Counter` | Valores solo crecientes (requests, errores, imagenes) | `.inc()`, `.inc(n)` |
| `Gauge` | Valores que suben y bajan (conexiones, temperatura) | `.set(n)`, `.inc()`, `.dec()` |
| `Histogram` | Distribucion de tiempos/latencias (inferencia, DB queries) | `.observe(n)`, `.time()` |
| `Summary` | Similar a histogram pero con cuantiles calculados del lado del cliente | `.observe(n)` |

## 3. Hacer que aparezca en el dashboard de Grafana

### Opcion A: Agregar panel al dashboard JSON existente

Editar `docker/grafana/provisioning/dashboards/soa_dashboards.json`:

```json
{
  "id": 9,
  "title": "Tiempo de Consultas a BD",
  "type": "timeseries",
  "gridPos": { "h": 8, "w": 12, "x": 0, "y": 26 },
  "datasource": { "type": "influxdb", "uid": "bfhay1m297a4gf" },
  "targets": [
    {
      "query": "from(bucket: \"metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"prometheus\") |> filter(fn: (r) => r._field == \"db_query_time_seconds_bucket\") |> aggregateWindow(every: 1m, fn: mean)",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": { "unit": "s" }
  }
}
```

### Opcion B: Agregar panel desde la UI de Grafana

1. Ir a Dashboards > "API Deteccion Visual - Monitoreo"
2. "Add" > "Visualization"
3. Seleccionar datasource `InfluxDB_SOA`
4. Escribir query Flux, ejemplo para `processed_images_total`:
   ```flux
   from(bucket: "metrics")
     |> range(start: v.timeRangeStart)
     |> filter(fn: (r) => r._measurement == "prometheus")
     |> filter(fn: (r) => r._field == "processed_images_total")
     |> aggregateWindow(every: 1m, fn: sum)
   ```
5. Guardar el dashboard

**Nota:** Los cambios hechos desde la UI se pierden si se recrea el contenedor de Grafana. Para persistencia, exportar el JSON y guardarlo en `docker/grafana/provisioning/dashboards/soa_dashboards.json`.

## 4. Labels - Buenas Practicas

```python
# Bien: labels con cardinalidad acotada
API_REQUESTS = Counter("api_requests_total", "...", ["endpoint", "method", "http_status"])

# Mal: labels con cardinalidad alta (cada request genera una serie nueva)
API_REQUESTS = Counter("api_requests_total", "...", ["request_id"])
```

Cardinalidad alta (>1000 valores distintos de label) puede saturar InfluxDB y Grafana.

## 5. Verificar que la metrica se exporta

```bash
curl -s http://localhost:8000/metrics | grep processed_images
```

## 6. Flujo completo de una metrica nueva

```
Codigo (metrics.py)  →  Endpoint /metrics  →  Telegraf scrapea cada 10s
  →  InfluxDB (bucket: metrics)  →  Grafana query Flux  →  Dashboard panel
```
