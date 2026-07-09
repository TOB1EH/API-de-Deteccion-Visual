#!/usr/bin/env bash
set -Eeuo pipefail

REMOTE_USER="iwei4a2o25"
REMOTE_HOST="bfts2026.mooo.com"
REMOTE_DIR="/home/${REMOTE_USER}/API-de-Deteccion-Visual"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

VERDE='\033[0;32m'
ROJO='\033[0;31m'
AZUL='\033[0;34m'
NC='\033[0m'

echo "${AZUL}[1/6]${NC} Construyendo imagen API local..."
cd "$LOCAL_DIR"
docker compose -f docker-compose.local.yml build api

echo "${AZUL}[2/6]${NC} Subiendo archivos al remoto..."
rsync -avz --progress \
  docker-compose.yml \
  Dockerfile.api \
  requirements.txt \
  docker/nginx.conf \
  docker/telegraf.conf \
  docker/grafana/ \
  src/ \
  models/ \
  client/ \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

echo "${AZUL}[3/6]${NC} Subiendo .env actualizado (sin keycloak, con influx/grafana)..."
rsync -avz --progress .env "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/.env"

echo "${AZUL}[4/6]${NC} Creando directorios de volumenes y provisionamiento en remoto..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
  mkdir -p ${REMOTE_DIR}/volumes/influxdb2_data
  mkdir -p ${REMOTE_DIR}/volumes/influxdb2_config
  mkdir -p ${REMOTE_DIR}/volumes/grafana_data
"

echo "${AZUL}[5/6]${NC} Reconstruyendo API y levantando servicios de monitoreo en remoto..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
  cd ${REMOTE_DIR}
  docker compose -f docker-compose.yml build api
  docker compose -f docker-compose.yml up -d influxdb telegraf grafana
  docker compose -f docker-compose.yml up -d nginx
"

echo "${AZUL}[6/6]${NC} Esperando 15s y ejecutando tests remotos..."
sleep 15
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
  cd ${REMOTE_DIR}
  # Tests basicos remotos
  echo '--- Test: /metrics responde ---'
  curl -s -o /dev/null -w '%{http_code}' http://api:8000/metrics

  echo ''
  echo '--- Test: influxdb ping ---'
  docker exec api_detection_influxdb influx ping --host http://localhost:8086 --skip-verify

  echo ''
  echo '--- Test: bucket metrics existe ---'
  docker exec api_detection_influxdb influx bucket list --token soa-token --org soa | grep metrics

  echo ''
  echo '--- Test: datos prometheus ---'
  docker exec api_detection_influxdb influx query 'from(bucket:\"metrics\") |> range(start: -3m) |> filter(fn: (r) => r._measurement == \"prometheus\") |> limit(n: 1)' --token soa-token --org soa

  echo ''
  echo '--- Test: grafana responde ---'
  curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/

  echo ''
  echo '--- Test: nginx sirve /grafana/ ---'
  curl -s -o /dev/null -w '%{http_code}' https://bfts2026.mooo.com/grafana/
"

echo ""
printf "${VERDE}Deploy completado.${NC}\n"
echo "Grafana remoto: https://bfts2026.mooo.com/grafana/"
echo "User: admin / Pass: admin123"
