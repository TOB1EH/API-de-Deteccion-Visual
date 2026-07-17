# Paneles de Monitoreo - Grafana

## Stack de Monitoreo

| Componente | Tecnologia | Proposito |
|---|---|---|
| InfluxDB | 2.8 | Base de datos de series temporales |
| Telegraf | 1.38 | Recolector de metricas (scrapea Prometheus + sistema) |
| Grafana | última | Visualizacion y dashboards |
| Prometheus Client | Python | Expone metricas via endpoint `/metrics` |

## Arquitectura

```
API (uvicorn) ──expone──> /metrics (Prometheus)
                            │
                     Telegraf scrapea cada 10s
                            │
                            v
                        InfluxDB (bucket: "metrics")
                            │
                     Grafana consulta via Flux
                            │
                            v
                     Paneles del dashboard
```

## Dataset de metricas

La API expone las siguientes metricas en `/metrics`:

| Metrica | Tipo | Labels | Descripcion |
|---|---|---|---|
| `api_requests_total` | Counter | endpoint, method, http_status | Total de requests HTTP |
| `inference_time_seconds` | Histogram | (none) | Tiempo de inferencia YOLO |
| `face_recognition_total` | Counter | result (success/failure) | Total de reconocimientos faciales |
| `detections_total` | Counter | (none) | Total de detecciones ejecutadas |
| `embedding_time_seconds` | Histogram | (none) | Tiempo de generacion de embeddings |
| `comparison_time_seconds` | Histogram | (none) | Tiempo de comparacion facial |
| `inference_server_up` | Gauge | (none) | Estado del nodo de inferencia (1=online, 0=offline) |

Ademas, Telegraf recolecta metricas del sistema:
- `cpu`: uso de CPU
- `mem`: uso de memoria
- `disk`: uso de disco
- `system`: uptime del sistema
- `inference_health`: health check del inference-server

## Descripcion de los 11 paneles

### 1. Uso de Recursos (Gauge)

Muestra el uso actual de CPU, memoria y disco en porcentaje.

**Query CPU:**
```flux
from(bucket: "metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "cpu" and r._field == "usage_idle" and r.cpu == "cpu-total")
  |> last()
  |> map(fn: (r) => ({ r with _value: 100.0 - r._value }))
  |> keep(columns: ["_value"])
  |> rename(columns: {_value: "CPU"})
  |> yield(name: "CPU")
```

Usa `last()` para obtener el valor mas reciente. Calcula el uso activo como `100 - idle`.

### 2. Requests por Minuto (Timeseries)

Muestra la tasa de requests HTTP por minuto, sumando todos los endpoints.

**Problema resuelto:** Con `--workers 2` los contadores Prometheus oscilaban porque cada worker tenia su propia memoria. `aggregateWindow(fn: last)` tomaba valores de workers distintos, y `difference()` producia valores negativos (-50 a 50).

**Solucion:** Usar `workers 1` y `fn: max` en vez de `fn: last`. `max()` siempre elige el valor mas alto, dando diferencias positivas estables. Ademas se agrupan todos los tag combos (endpoint+method+status) en una sola serie via `group + aggregateWindow(fn: sum)`.

```flux
from(bucket: "metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "prometheus" and r._field == "api_requests_total")
  |> aggregateWindow(every: 1m, fn: max, createEmpty: false)
  |> difference(columns: ["_value"])
  |> map(fn: (r) => ({ r with _value: if r._value < 0.0 then 0.0 else r._value }))
  |> truncateTimeColumn(unit: 1m)
  |> group(columns: ["_field", "_measurement"])
  |> aggregateWindow(every: 1m, fn: sum, createEmpty: false)
  |> yield(name: "requests")
```

Un piso de ~6-12/min es normal (scraping de Telegraf a `/metrics` y `/health`). Picos mayores son requests reales.

### 3. Tasa de Errores (HTTP 5xx/min) (Timeseries)

Igual que Requests por Minuto pero filtrando solo `http_status` que empiece con "5". Muestra errores del servidor por minuto.

```flux
from(bucket: "metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "prometheus" and r._field == "api_requests_total" and r.http_status =~ /^5/)
  |> aggregateWindow(every: 1m, fn: max, createEmpty: false)
  |> difference(columns: ["_value"])
  |> map(fn: (r) => ({ r with _value: if r._value < 0.0 then 0.0 else r._value }))
  |> truncateTimeColumn(unit: 1m)
  |> group(columns: ["_field", "_measurement"])
  |> aggregateWindow(every: 1m, fn: sum, createEmpty: false)
  |> yield(name: "errores")
```

Valor normal: 0. Cualquier pico > 0 indica un error 500.

### 4. Tiempo Promedio de Inferencia (Stat)

Promedio del histograma `inference_time_seconds` (sum / count). Usa `reduce` para combinar los campos `_sum` y `_count` del histograma.

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus" and (r._field == "inference_time_seconds_sum" or r._field == "inference_time_seconds_count"))
  |> filter(fn: (r) => r._value > 0)
  |> last()
  |> group()
  |> reduce(
      fn: (r, accumulator) => ({
        sum: accumulator.sum + (if r._field == "inference_time_seconds_sum" then r._value else 0.0),
        count: accumulator.count + (if r._field == "inference_time_seconds_count" then r._value else 0.0)
      }),
      identity: {sum: 0.0, count: 0.0}
    )
  |> map(fn: (r) => ({ r with _value: if r.count > 0.0 then r.sum / r.count else 0.0 }))
  |> keep(columns: ["_value"])
```

**Nota:** `filter(r._value > 0)` evita que el reseteo del contador al reiniciar el container genere NaN. La proteccion `if r.count > 0.0` evita division por cero.

### 5. Throughput (Imagenes Procesadas) (Stat)

Valor acumulado de `detections_total`. Muestra cuantas detecciones se procesaron desde el ultimo reinicio.

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus")
  |> filter(fn: (r) => r._field == "detections_total")
  |> filter(fn: (r) => r._value > 0)
  |> last()
  |> yield(name: "total")
```

### 6. Tiempo de Generacion de Embeddings (Timeseries)

Serie temporal del histograma `embedding_time_seconds_sum`. Muestra la evolucion del tiempo acumulado de generacion de embeddings faciales.

```flux
from(bucket: "metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "prometheus")
  |> filter(fn: (r) => r._field == "embedding_time_seconds_sum")
  |> aggregateWindow(every: 1m, fn: last, createEmpty: false)
  |> yield(name: "embedding")
```

### 7. Tiempo de Comparacion Facial (Timeseries)

Serie temporal del histograma `comparison_time_seconds_sum`. Muestra la evolucion del tiempo acumulado de comparacion facial.

```flux
from(bucket: "metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "prometheus")
  |> filter(fn: (r) => r._field == "comparison_time_seconds_sum")
  |> aggregateWindow(every: 1m, fn: last, createEmpty: false)
  |> yield(name: "comparison")
```

### 8. Reconocimientos Exitosos vs Fallidos (Stat)

Muestra dos valores: la cantidad de reconocimientos faciales exitosos y fallidos.

```flux
Exitosos:
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus" and r._field == "face_recognition_total" and r.result == "success")
  |> last()
  |> yield(name: "exitosos")

Fallidos:
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus" and r._field == "face_recognition_total" and r.result == "failure")
  |> last()
  |> yield(name: "fallidos")
```

### 9. Estado del Nodo de Inferencia (Stat)

Muestra ONLINE (1) u OFFLINE (0) segun el healthcheck periodico al inference-server.

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "inference_health" and r._field == "estado_binario")
  |> last()
  |> group()
  |> last()
  |> yield(name: "estado")
```

El `group() |> last()` colapsa multiples filas (cuando hay resultados con distintos tags) en una sola, mostrando siempre el valor mas reciente.

### 10. Uptime del Sistema (Stat)

Tiempo que lleva el sistema corriendo, obtenido de la metrica `system` de Telegraf.

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "system")
  |> filter(fn: (r) => r._field == "uptime")
  |> last()
  |> yield(name: "uptime")
```

### 11. Ratio de Reconocimiento Exitoso (Stat)

Porcentaje de reconocimientos faciales exitosos sobre el total.

```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus" and r._field == "face_recognition_total" and (r.result == "success" or r.result == "failure"))
  |> last()
  |> group()
  |> reduce(
      fn: (r, accumulator) => ({
        success: accumulator.success + (if r.result == "success" then r._value else 0.0),
        total: accumulator.total + r._value
      }),
      identity: {success: 0.0, total: 0.0}
    )
  |> map(fn: (r) => ({ r with _value: (r.success / r.total) * 100.0 }))
  |> keep(columns: ["_value"])
```

Usa `reduce` para sumar exitos y total, calculando el porcentaje. Si no hay reconocimientos, muestra 0.

## Problemas Conocidos y Soluciones

### Oscilacion de contadores con --workers 2

**Sintoma:** Requests por minuto oscila entre valores positivos y negativos (-50 a 50).

**Causa:** Uvicorn con `--workers 2` crea dos procesos independientes. Cada worker tiene su propio contador Prometheus en memoria. Telegraf scrapea `/metrics` y alterna entre workers, obteniendo valores diferentes. `aggregateWindow(fn: last)` toma el ultimo valor de cada ventana, que puede pertenecer a cualquier worker. `difference()` entre ventanas consecutivas produce valores negativos cuando el worker "ganador" cambia.

**Solucion:** 
- Reducir a `--workers 1` (contador unico y monotono)
- Usar `aggregateWindow(fn: max)` en vez de `fn: last` como capa extra de seguridad

### NaN en paneles Stat

**Causa:** Al reiniciar el container, los contadores Prometheus se复位 a 0. Si `last()` toma estos ceros y luego se divide (sum/count), el resultado es NaN.

**Solucion:** 
- `filter(r._value > 0)` antes de `last()` para ignorar contadores reiniciados
- Guardas condicionales: `if r.count > 0.0 then r.sum / r.count else 0.0`

### Multiples filas en paneles Stat

**Causa:** Cuando hay multiples tags (ej: diferentes resultados de healthcheck), `last()` devuelve una fila por cada combinacion unica de tags.

**Solucion:** `group() |> last()` colapsa todas las filas en una sola tabla y toma la mas reciente.

## Referencias

- Dashboard provisionado: `docker/grafana/provisioning/dashboards/soa_dashboards.json`
- Metricas de la API: `src/api/routes/metrics.py`
- Healthcheck loop: `src/api/main.py`
- Telegraf config: `docker/telegraf.conf`
- Datasource Grafana: `docker/grafana/provisioning/datasources/`
- Docker compose local: `docker-compose.local.yml`
- Docker compose remoto: `docker-compose.yml`
