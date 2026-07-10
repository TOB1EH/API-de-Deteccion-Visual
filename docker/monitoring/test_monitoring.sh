#!/usr/bin/env bash
# =============================================================================
# test_monitoring.sh - Tests de integracion para InfluxDB, Telegraf y Grafana
#
# Uso: ./docker/monitoring/test_monitoring.sh
#
# Prerrequisitos: contenedores del stack de monitoreo corriendo
# =============================================================================

set -Eeuo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BASE_DIR"

VERDE='\033[0;32m'
ROJO='\033[0;31m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m'

PASADOS=0
FALLADOS=0
TOTAL=0

info()    { printf "${AZUL}[INFO]${NC}  %s\n" "$*"; }
ok()      { printf "${VERDE}[OK]${NC}    %s\n" "$*"; }
fail()    { printf "${ROJO}[FAIL]${NC}  %s\n" "$*"; }
warn()    { printf "${AMARILLO}[WARN]${NC} %s\n" "$*"; }

test_start() {
    TOTAL=$((TOTAL + 1))
    info "Test #${TOTAL}: $1"
}

test_pass() {
    PASADOS=$((PASADOS + 1))
    ok "$1"
}

test_fail() {
    FALLADOS=$((FALLADOS + 1))
    fail "$1"
    if [ "${2:-}" ]; then
        warn "  Detalle: $2"
    fi
}

check_exit() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$actual" -eq "$expected" ]; then
        test_pass "$desc"
    else
        test_fail "$desc" "exit_code esperado=$expected, obtenido=$actual"
    fi
}

echo "================================================"
echo " Tests de Monitoreo: InfluxDB + Telegraf + Grafana"
echo " Fecha: $(date)"
echo " Proyecto: $(basename "$BASE_DIR")"
echo "================================================"
echo ""

# =============================================================================
# 1. Contenedores
# =============================================================================
echo "--- 1. Contenedores ---"

test_start "Container influxdb existe y esta corriendo"
if docker ps --format '{{.Names}}' | grep -q '^api_detection_influxdb_local$'; then
    status=$(docker inspect api_detection_influxdb_local --format '{{.State.Status}}')
    health=$(docker inspect api_detection_influxdb_local --format '{{.State.Health.Status}}')
    test_pass "influxdb: status=$status, health=$health"
else
    test_fail "influxdb no encontrado"
fi

test_start "Container telegraf existe y esta corriendo"
if docker ps --format '{{.Names}}' | grep -q '^api_detection_telegraf_local$'; then
    status=$(docker inspect api_detection_telegraf_local --format '{{.State.Status}}')
    test_pass "telegraf: status=$status"
else
    test_fail "telegraf no encontrado"
fi

test_start "Container grafana existe y esta corriendo"
if docker ps --format '{{.Names}}' | grep -q '^api_detection_grafana_local$'; then
    status=$(docker inspect api_detection_grafana_local --format '{{.State.Status}}')
    test_pass "grafana: status=$status"
else
    test_fail "grafana no encontrado"
fi

# =============================================================================
# 2. InfluxDB
# =============================================================================
echo ""
echo "--- 2. InfluxDB ---"

INFLUX_TOKEN="${INFLUXDB_TOKEN:-soa-token}"
INFLUX_ORG="${INFLUXDB_ORG:-soa}"
INFLUX_BUCKET="${INFLUXDB_BUCKET:-metrics}"

test_start "InfluxDB responde ping"
rc=0
docker exec api_detection_influxdb_local influx ping --host http://localhost:8086 --skip-verify 2>/dev/null || rc=$?
check_exit "influx ping" 0 "$rc"

test_start "InfluxDB tiene el bucket 'metrics'"
rc=0
output=$(docker exec api_detection_influxdb_local influx bucket list --token "$INFLUX_TOKEN" --org "$INFLUX_ORG" 2>/dev/null) || rc=$?
if [ "$rc" -eq 0 ]; then
    if echo "$output" | grep -q "$INFLUX_BUCKET"; then
        test_pass "Bucket '${INFLUX_BUCKET}' encontrado"
    else
        test_fail "Bucket '${INFLUX_BUCKET}' no encontrado" "$output"
    fi
else
    test_fail "No se pudo listar buckets"
fi

test_start "Datos prometheus en InfluxDB (ultimos 5 min)"
rc=0
output=$(docker exec api_detection_influxdb_local influx query \
    "from(bucket:\"${INFLUX_BUCKET}\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \"prometheus\") |> limit(n: 1)" \
    --token "$INFLUX_TOKEN" --org "$INFLUX_ORG" 2>/dev/null) || rc=$?
if [ "$rc" -eq 0 ] && [ -n "$output" ]; then
    test_pass "Datos prometheus encontrados"
else
    test_fail "Sin datos prometheus" "Telegraf no ha scrapeado aun?"
fi

test_start "Datos system en InfluxDB (ultimos 5 min)"
rc=0
output=$(docker exec api_detection_influxdb_local influx query \
    "from(bucket:\"${INFLUX_BUCKET}\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \"system\") |> limit(n: 1)" \
    --token "$INFLUX_TOKEN" --org "$INFLUX_ORG" 2>/dev/null) || rc=$?
if [ "$rc" -eq 0 ] && [ -n "$output" ]; then
    test_pass "Datos system encontrados"
else
    test_fail "Sin datos system"
fi

test_start "Datos cpu en InfluxDB (ultimos 5 min)"
rc=0
output=$(docker exec api_detection_influxdb_local influx query \
    "from(bucket:\"${INFLUX_BUCKET}\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \"cpu\") |> limit(n: 1)" \
    --token "$INFLUX_TOKEN" --org "$INFLUX_ORG" 2>/dev/null) || rc=$?
if [ "$rc" -eq 0 ] && [ -n "$output" ]; then
    test_pass "Datos cpu encontrados"
else
    test_fail "Sin datos cpu"
fi

test_start "Datos mem en InfluxDB (ultimos 5 min)"
rc=0
output=$(docker exec api_detection_influxdb_local influx query \
    "from(bucket:\"${INFLUX_BUCKET}\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \"mem\") |> limit(n: 1)" \
    --token "$INFLUX_TOKEN" --org "$INFLUX_ORG" 2>/dev/null) || rc=$?
if [ "$rc" -eq 0 ] && [ -n "$output" ]; then
    test_pass "Datos mem encontrados"
else
    test_fail "Sin datos mem"
fi

# =============================================================================
# 3. Telegraf
# =============================================================================
echo ""
echo "--- 3. Telegraf ---"

test_start "Telegraf: sin errores prometheus scrape (ultimos 30s)"
logs=$(docker logs api_detection_telegraf_local --since 30s 2>&1 || true)
prometheus_errors=$(echo "$logs" | grep -c "inputs.prometheus.*Error" || true)
if [ "$prometheus_errors" -eq 0 ]; then
    test_pass "Sin errores de prometheus scrape"
else
    test_fail "Errores de prometheus scrape: ${prometheus_errors}" "$(echo "$logs" | grep 'inputs.prometheus.*Error' | tail -2)"
fi

test_start "Telegraf: sin errores de http_response"
http_errors=$(echo "$logs" | grep -c "inputs.http_response.*Error" || true)
if [ "$http_errors" -eq 0 ]; then
    test_pass "Sin errores de http_response"
else
    test_fail "Errores de http_response: ${http_errors}"
fi

test_start "Telegraf: sin errores de output a InfluxDB"
output_errors=$(echo "$logs" | grep -ci "outputs.influxdb.*Error\|E!.*output" || true)
if [ "$output_errors" -eq 0 ]; then
    test_pass "Sin errores de output"
else
    test_fail "Errores de output: ${output_errors}"
fi

test_start "Telegraf: conectividad con API"
rc=0
code=$(docker exec api_detection_telegraf_local sh -c "curl -s -o /dev/null -w '%{http_code}' http://api:8000/metrics" 2>/dev/null) || rc=$?
if [ "$code" = "200" ]; then
    test_pass "Conectividad OK (HTTP 200)"
else
    test_fail "Sin conectividad con API" "HTTP code=$code, exit=$rc"
fi

# =============================================================================
# 4. API /metrics
# =============================================================================
echo ""
echo "--- 4. API /metrics ---"

test_start "Endpoint /metrics responde HTTP 200"
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/metrics || true)
if [ "$code" = "200" ]; then
    test_pass "/metrics HTTP 200"
else
    test_fail "/metrics no responde 200" "HTTP $code"
fi

test_start "Metrica api_requests_total en /metrics"
if curl -s http://localhost:8000/metrics | grep -q "^api_requests_total"; then
    test_pass "api_requests_total encontrada"
else
    test_fail "api_requests_total NO encontrada"
fi

test_start "Metrica inference_time_seconds en /metrics"
if curl -s http://localhost:8000/metrics | grep -q "^inference_time_seconds"; then
    test_pass "inference_time_seconds encontrada"
else
    test_fail "inference_time_seconds NO encontrada"
fi

test_start "Metrica detections_total en /metrics"
if curl -s http://localhost:8000/metrics | grep -q "^detections_total"; then
    test_pass "detections_total encontrada"
else
    test_fail "detections_total NO encontrada"
fi

# =============================================================================
# 5. Grafana
# =============================================================================
echo ""
echo "--- 5. Grafana ---"

test_start "Grafana responde en puerto 3000"
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ || true)
if [ "$code" = "302" ] || [ "$code" = "200" ]; then
    test_pass "Grafana responde (HTTP $code)"
else
    test_fail "Grafana no responde" "HTTP $code"
fi

test_start "Grafana responde via nginx /grafana/"
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/grafana/ || true)
if [ "$code" = "302" ] || [ "$code" = "200" ]; then
    test_pass "Grafana via nginx responde (HTTP $code)"
else
    test_fail "Grafana via nginx no responde" "HTTP $code"
fi

test_start "Grafana login page accesible"
code=$(curl -s -o /dev/null -w '%{http_code}' -L http://localhost:3000/ || true)
if [ "$code" = "200" ]; then
    test_pass "Login page accesible (HTTP 200 tras redirect)"
else
    test_fail "Login page no accesible" "HTTP $code"
fi

test_start "Datasource InfluxDB provisionado en Grafana (via archivo)"
if [ -f "${BASE_DIR}/docker/grafana/provisioning/datasources/datasource.yml" ]; then
    if grep -qi "influx" "${BASE_DIR}/docker/grafana/provisioning/datasources/datasource.yml"; then
        test_pass "Datasource InfluxDB encontrado en archivo de provisionamiento"
    else
        test_fail "Datasource no contiene 'influx'" "$(head -20 "${BASE_DIR}/docker/grafana/provisioning/datasources/datasource.yml")"
    fi
else
    test_fail "Archivo datasource.yml no existe"
fi

test_start "Dashboard 'soa_dashboards.json' existe y tiene paneles"
dashboard_file="${BASE_DIR}/docker/grafana/provisioning/dashboards/soa_dashboards.json"
if [ -f "$dashboard_file" ]; then
    panels=$(python3 -c "import json; d=json.load(open('$dashboard_file')); print(len(d.get('panels', [])))" 2>/dev/null || echo "0")
    dashboard_title=$(python3 -c "import json; d=json.load(open('$dashboard_file')); print(d.get('title', 'sin_titulo'))" 2>/dev/null || echo "error")
    if [ "$panels" -gt 0 ]; then
        test_pass "Dashboard '${dashboard_title}' encontrado con ${panels} paneles"
    else
        test_fail "Dashboard sin paneles o JSON invalido"
    fi
else
    test_fail "Archivo soa_dashboards.json no existe"
fi

test_start "Dashboard tiene paneles con queries a InfluxDB"
if [ -f "$dashboard_file" ]; then
    panel_count=$(python3 -c "
import json
d=json.load(open('$dashboard_file'))
panels_con_influx=0
for p in d.get('panels', []):
    targets=p.get('targets',[])
    for t in targets:
        if 'influx' in json.dumps(t).lower() or 'flux' in json.dumps(t).lower() or 'from(bucket' in json.dumps(t):
            panels_con_influx+=1
            break
print(panels_con_influx)
" 2>/dev/null || echo "0")
    if [ "$panel_count" -gt 0 ]; then
        test_pass "${panel_count} paneles con queries a InfluxDB/Flux"
    else
        test_fail "Ningun panel tiene query a InfluxDB" "Revisar targets del dashboard"
    fi
fi

test_start "Datasource apunta a InfluxDB interno y usa token"
ds_file="${BASE_DIR}/docker/grafana/provisioning/datasources/datasource.yml"
if [ -f "$ds_file" ]; then
    url_valida=$(grep -c "url.*http://influxdb:8086" "$ds_file" || true)
    token_valido=$(grep -c "\${\?INFLUXDB_TOKEN}" "$ds_file" || true)
    if [ "$url_valida" -gt 0 ] && [ "$token_valido" -gt 0 ]; then
        test_pass "Datasource apunta a http://influxdb:8086 con INFLUXDB_TOKEN"
    else
        test_fail "Datasource mal configurado" "url_valida=$url_valida token_valido=$token_valido"
    fi
else
    test_fail "Archivo datasource.yml no existe"
fi

# =============================================================================
# Resumen
# =============================================================================
echo ""
echo "================================================"
echo " RESULTADOS"
echo "================================================"
echo " Total:  $TOTAL"
printf " ${VERDE}Pasados:${NC} $PASADOS\n"
if [ "$FALLADOS" -gt 0 ]; then
    printf " ${ROJO}Fallados:${NC} $FALLADOS\n"
fi
echo "================================================"

if [ "$FALLADOS" -gt 0 ]; then
    exit 1
fi
