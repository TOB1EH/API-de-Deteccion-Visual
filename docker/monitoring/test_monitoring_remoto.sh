#!/usr/bin/env bash
# =============================================================================
# test_monitoring_remoto.sh - Tests de integracion remotos para InfluxDB,
# Telegraf y Grafana via SSH en bfts2026.mooo.com
#
# Uso: ./docker/monitoring/test_monitoring_remoto.sh
#
# Prerrequisitos: servicios de monitoreo corriendo en el remoto
# =============================================================================

set -Eeuo pipefail

REMOTE_USER="iwei4a2o25"
REMOTE_HOST="bfts2026.mooo.com"
REMOTE_DIR="/home/${REMOTE_USER}/API-de-Deteccion-Visual"

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

REMOTE_SCRIPT=$(cat << 'REMOTE_EOF'
set -e

INFLUX_TOKEN="${INFLUXDB_TOKEN:-soa-token}"
INFLUX_ORG="${INFLUXDB_ORG:-soa}"
INFLUX_BUCKET="${INFLUXDB_BUCKET:-metrics}"

p() {
    local num="$1" desc="$2"
    shift 2
    echo "T|${num}|${desc}"
    if "$@" > /dev/null 2>&1; then
        echo "P|${num}|${desc}"
    else
        echo "F|${num}|${desc}"
    fi
}

echo "--- 1. Contenedores ---"

p 1 "Container influxdb existe y esta corriendo" \
  docker ps --format '{{.Names}}' | grep -q '^api_detection_influxdb$'

p 2 "Container telegraf existe y esta corriendo" \
  docker ps --format '{{.Names}}' | grep -q '^api_detection_telegraf$'

p 3 "Container grafana existe y esta corriendo" \
  docker ps --format '{{.Names}}' | grep -q '^api_detection_grafana$'

echo ""
echo "--- 2. InfluxDB ---"

p 4 "InfluxDB responde ping" \
  docker exec api_detection_influxdb influx ping --host http://localhost:8086 --skip-verify

p 5 "InfluxDB tiene bucket metrics" \
  sh -c "docker exec api_detection_influxdb influx bucket list --token ${INFLUX_TOKEN} --org ${INFLUX_ORG} 2>/dev/null | grep -q ${INFLUX_BUCKET}"

p 6 "Datos prometheus en InfluxDB" \
  sh -c "docker exec api_detection_influxdb influx query \"from(bucket:\\\"${INFLUX_BUCKET}\\\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \\\"prometheus\\\") |> limit(n: 1)\" --token ${INFLUX_TOKEN} --org ${INFLUX_ORG} 2>/dev/null | grep -q prometheus"

p 7 "Datos system en InfluxDB" \
  sh -c "docker exec api_detection_influxdb influx query \"from(bucket:\\\"${INFLUX_BUCKET}\\\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \\\"system\\\") |> limit(n: 1)\" --token ${INFLUX_TOKEN} --org ${INFLUX_ORG} 2>/dev/null | grep -q system"

p 8 "Datos cpu en InfluxDB" \
  sh -c "docker exec api_detection_influxdb influx query \"from(bucket:\\\"${INFLUX_BUCKET}\\\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \\\"cpu\\\") |> limit(n: 1)\" --token ${INFLUX_TOKEN} --org ${INFLUX_ORG} 2>/dev/null | grep -q cpu"

p 9 "Datos mem en InfluxDB" \
  sh -c "docker exec api_detection_influxdb influx query \"from(bucket:\\\"${INFLUX_BUCKET}\\\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \\\"mem\\\") |> limit(n: 1)\" --token ${INFLUX_TOKEN} --org ${INFLUX_ORG} 2>/dev/null | grep -q mem"

echo ""
echo "--- 3. Telegraf ---"

p 10 "Telegraf: sin errores prometheus scrape" \
  sh -c "docker logs api_detection_telegraf --since 30s 2>&1 | grep -vc \"inputs.prometheus.*Error\" | grep -q 0" 2>/dev/null || true

p 11 "Telegraf: sin errores http_response" \
  sh -c "docker logs api_detection_telegraf --since 30s 2>&1 | grep -vc \"inputs.http_response.*Error\" | grep -q 0" 2>/dev/null || true

p 12 "Telegraf: sin errores output InfluxDB" \
  sh -c "docker logs api_detection_telegraf --since 30s 2>&1 | grep -vci \"outputs.influxdb.*Error\|E!.*output\" | grep -q 0" 2>/dev/null || true

p 13 "Telegraf: conectividad con API" \
  sh -c "docker exec api_detection_telegraf sh -c \"curl -s -o /dev/null -w '%{http_code}' http://api:8000/metrics\" 2>/dev/null | grep -q 200"

echo ""
echo "--- 4. API /metrics ---"

p 14 "Endpoint /metrics HTTPS responde 200" \
  curl -s -o /dev/null -w '%{http_code}' https://bfts2026.mooo.com/metrics | grep -q 200

p 15 "Metrica api_requests_total en /metrics" \
  curl -s https://bfts2026.mooo.com/metrics | grep -q "^api_requests_total"

p 16 "Metrica inference_time_seconds en /metrics" \
  curl -s https://bfts2026.mooo.com/metrics | grep -q "^inference_time_seconds"

p 17 "Metrica detections_total en /metrics" \
  curl -s https://bfts2026.mooo.com/metrics | grep -q "^detections_total"

echo ""
echo "--- 5. Grafana ---"

p 18 "Grafana responde internamente" \
  curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ | grep -Eq "302|200"

p 19 "Grafana responde via nginx /grafana/" \
  curl -s -o /dev/null -w '%{http_code}' https://bfts2026.mooo.com/grafana/ | grep -Eq "302|200"

p 20 "Grafana login page accesible" \
  curl -s -L -o /dev/null -w '%{http_code}' http://localhost:3000/ | grep -q 200

p 21 "Archivo datasource provisionado" \
  test -f docker/grafana/provisioning/datasources/datasource.yml

p 22 "Archivo dashboard provisionado" \
  test -f docker/grafana/provisioning/dashboards/soa_dashboards.json

echo ""
echo "--- FIN ---"
REMOTE_EOF
)

echo "================================================"
echo " Tests Remotos de Monitoreo: ${REMOTE_HOST}"
echo " Fecha: $(date)"
echo "================================================"
echo ""

OUTPUT=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_DIR} && ${REMOTE_SCRIPT}" 2>&1) || true

while IFS= read -r line; do
  case "$line" in
    T\|*)
      num="${line#T|}"
      desc="${num#*|}"
      num="${num%%|*}"
      TOTAL=$((TOTAL + 1))
      info "Test #${num}: ${desc}"
      ;;
    P\|*)
      PASADOS=$((PASADOS + 1))
      desc="${line#P|}"
      desc="${desc#*|}"
      ok "${desc}"
      ;;
    F\|*)
      FALLADOS=$((FALLADOS + 1))
      desc="${line#F|}"
      desc="${desc#*|}"
      fail "${desc}"
      ;;
    ---*|"")
      echo "$line"
      ;;
    *)
      echo "  $line"
      ;;
  esac
done <<< "$OUTPUT"

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
