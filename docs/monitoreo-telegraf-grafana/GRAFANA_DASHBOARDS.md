# Personalizar Dashboards en Grafana

Acceso: `http://localhost/grafana/` (admin / admin123)

## Crear un Nuevo Panel

1. Ir a Dashboards > "API Deteccion Visual - Monitoreo"
2. Click en "Add" > "Visualization"
3. Seleccionar datasource `InfluxDB_SOA`
4. Elegir tipo de visualizacion (timeseries, gauge, stat, bar chart, etc.)
5. Escribir query Flux
6. Configurar ejes, unidades, thresholds
7. Click "Save" > "Save dashboard"

## Queries Flux - Ejemplos

### Requests por endpoint (ultima hora)
```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus")
  |> filter(fn: (r) => r._field == "api_requests_total")
  |> group(columns: ["endpoint"])
  |> aggregateWindow(every: 1m, fn: sum)
```

### Tasa de error (HTTP 5xx vs total)
```flux
errores = from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus")
  |> filter(fn: (r) => r._field == "api_requests_total")
  |> filter(fn: (r) => r.http_status =~ /^5/)
  |> aggregateWindow(every: 1m, fn: sum)

total = from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "prometheus")
  |> filter(fn: (r) => r._field == "api_requests_total")
  |> aggregateWindow(every: 1m, fn: sum)

join(
  tables: {errores: errores, total: total},
  on: ["_time"],
  method: "left"
)
  |> map(fn: (r) => ({ r with _value: float(v: r._value_errores) / float(v: r._value_total) * 100.0 }))
```

### Uso de CPU por nucleo
```flux
from(bucket: "metrics")
  |> range(start: v.timeRangeStart)
  |> filter(fn: (r) => r._measurement == "cpu")
  |> filter(fn: (r) => r._field == "usage_user")
  |> filter(fn: (r) => r.cpu != "cpu-total")
```

## Agregar Alertas

1. Editar panel > "Alert" tab
2. Click "Create alert rule from this panel"
3. Definir condicion (ej: `last() > 80` para CPU)
4. Configurar canal de notificacion (email, Slack, webhook)
5. Guardar

### Canales de notificacion disponibles
- Email (configurar SMTP en `grafana.ini`)
- Slack webhook
- Telegram
- PagerDuty
- Webhook generico

## Compartir un Dashboard

- **Exportar JSON**: Dashboard settings > "JSON Model" > "Copy to Clipboard"
- **Compartir link**: Panel title > "Share" > "Link"
- **Embed**: Panel title > "Share" > "Embed" (iframe HTML)

## Importar un Dashboard desde JSON

1. Dashboards > "New" > "Import"
2. Pegar JSON o subir archivo
3. Seleccionar datasource
4. Click "Import"

## Buenas Practicas

- Usar `v.timeRangeStart` y `v.timeRangeStop` en queries para respetar el selector de tiempo
- Preferir `aggregateWindow` para reducir puntos de datos en rangos largos
- Nombrar paneles descriptivamente para que se entiendan sin contexto
- Usar thresholds con colores (verde/amarillo/rojo) para indicar estado
- Documentar queries complejas como comentarios en el panel
- No superar ~10 paneles por dashboard para mantener rendimiento
