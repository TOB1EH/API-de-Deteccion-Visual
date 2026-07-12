<template>
  <v-container fluid class="pa-6">
    <!-- Encabezado NOC -->
    <v-row class="mb-4">
      <v-col cols="12">
        <div class="d-flex align-center flex-wrap ga-3">
          <div class="flex-grow-1">
            <h2 class="text-h4 font-weight-bold">
              <v-icon color="cyan-accent-3" class="mr-2">mdi-monitor-dashboard</v-icon>
              CENTRO DE OPERACIONES Y MONITOREO (NOC)
            </h2>
            <p class="text-body-2 text-medium-emphasis mt-1">
              Monitoreo en tiempo real de infraestructura, base de datos y modelos de IA
            </p>
          </div>
          <v-btn
            variant="outlined"
            color="cyan-accent-3"
            prepend-icon="mdi-refresh"
            size="small"
            :loading="refreshing"
            @click="refreshDashboards"
          >
            Forzar Recarga de Tableros
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Estado de servicios -->
    <v-row class="mb-4">
      <v-col cols="12">
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            color="green-accent-3"
            variant="tonal"
            prepend-icon="mdi-pulse"
            size="small"
          >
            Telegraf: Activo
          </v-chip>
          <v-chip
            color="green-accent-3"
            variant="tonal"
            prepend-icon="mdi-server"
            size="small"
          >
            Grafana Server: Conectado
          </v-chip>
          <v-chip
            color="cyan-accent-3"
            variant="tonal"
            prepend-icon="mdi-brain"
            size="small"
          >
            Inferencia IA: Operando
          </v-chip>
        </div>
      </v-col>
    </v-row>

    <!-- Pestañas de monitoreo -->
    <v-card variant="outlined" class="pa-0">
      <v-tabs
        v-model="tab"
        color="cyan-accent-3"
        class="px-4 pt-2"
      >
        <v-tab value="host" class="text-none">
          <v-icon start size="18">mdi-server</v-icon>
          Infraestructura (Host)
        </v-tab>
        <v-tab value="db" class="text-none">
          <v-icon start size="18">mdi-database</v-icon>
          Base de Datos & API
        </v-tab>
        <v-tab value="yolo" class="text-none">
          <v-icon start size="18">mdi-brain</v-icon>
          Metricas del Modelo YOLO
        </v-tab>
      </v-tabs>

      <v-divider />

      <v-window v-model="tab">
        <v-window-item value="host" class="pa-4">
          <v-card variant="outlined" class="iframe-card">
            <div class="d-flex align-center mb-3">
              <v-icon color="cyan-accent-3" class="mr-2">mdi-chart-line</v-icon>
              <span class="text-body-1 font-weight-medium">Metricas de Infraestructura (CPU, RAM, Red)</span>
            </div>
            <iframe
              v-if="activeTab === 'host'"
              :src="urlHostMetrics"
              :key="'host-' + iframeKey"
              width="100%"
              height="650"
              frameborder="0"
              class="grafana-iframe"
              @load="onIframeLoad('host')"
            />
            <div v-else class="iframe-placeholder">
              <v-icon size="48" color="grey-darken-1" class="mb-3">mdi-monitor-dashboard</v-icon>
              <p class="text-grey">Cargando tablero de infraestructura...</p>
            </div>
          </v-card>
        </v-window-item>

        <v-window-item value="db" class="pa-4">
          <v-card variant="outlined" class="iframe-card">
            <div class="d-flex align-center mb-3">
              <v-icon color="indigo-accent-3" class="mr-2">mdi-chart-bar</v-icon>
              <span class="text-body-1 font-weight-medium">Rendimiento de PostgreSQL y FastAPI</span>
            </div>
            <iframe
              v-if="activeTab === 'db'"
              :src="urlDbMetrics"
              :key="'db-' + iframeKey"
              width="100%"
              height="650"
              frameborder="0"
              class="grafana-iframe"
              @load="onIframeLoad('db')"
            />
            <div v-else class="iframe-placeholder">
              <v-icon size="48" color="grey-darken-1" class="mb-3">mdi-database</v-icon>
              <p class="text-grey">Cargando tablero de base de datos...</p>
            </div>
          </v-card>
        </v-window-item>

        <v-window-item value="yolo" class="pa-4">
          <v-card variant="outlined" class="iframe-card">
            <div class="d-flex align-center mb-3">
              <v-icon color="green-accent-3" class="mr-2">mdi-chart-bell-curve</v-icon>
              <span class="text-body-1 font-weight-medium">Estado de Frames y Tiempos de Inferencia YOLO</span>
            </div>
            <iframe
              v-if="activeTab === 'yolo'"
              :src="urlYoloMetrics"
              :key="'yolo-' + iframeKey"
              width="100%"
              height="650"
              frameborder="0"
              class="grafana-iframe"
              @load="onIframeLoad('yolo')"
            />
            <div v-else class="iframe-placeholder">
              <v-icon size="48" color="grey-darken-1" class="mb-3">mdi-brain</v-icon>
              <p class="text-grey">Cargando tablero de metricas YOLO...</p>
            </div>
          </v-card>
        </v-window-item>
      </v-window>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'

const tab = ref('host')
const refreshing = ref(false)
const iframeKey = ref(0)

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
const GRAFANA_BASE = isLocalDev ? 'http://localhost:3001' : 'https://bfts2026.mooo.com/grafana'
const GRAFANA_DS = 'api_monitoring/api-deteccion-visual-monitoreo'

const urlHostMetrics = ref(`${GRAFANA_BASE}/d/${GRAFANA_DS}?orgId=1&kiosk=tv&from=now-6h&to=now`)
const urlDbMetrics = ref(`${GRAFANA_BASE}/d/${GRAFANA_DS}?orgId=1&kiosk=tv&from=now-6h&to=now`)
const urlYoloMetrics = ref(`${GRAFANA_BASE}/d/${GRAFANA_DS}?orgId=1&kiosk=tv&from=now-6h&to=now`)

// Fuerza recarga limpiando la key del iframe
function refreshDashboards() {
  refreshing.value = true
  iframeKey.value++
  setTimeout(() => {
    refreshing.value = false
  }, 1000)
}

function onIframeLoad(name) {
  console.log(`[Monitoreo] Tablero "${name}" cargado`)
}

// Computed para activar carga perezosa del iframe (solo renderiza el activo)
const activeTab = computed(() => tab.value)
</script>

<style scoped>
.iframe-card {
  background: rgba(18, 18, 18, 0.85) !important;
  border: 1px solid rgba(0, 229, 255, 0.2) !important;
  padding: 16px;
}

.grafana-iframe {
  border-radius: 8px;
  background: #0a0e1a;
}

.iframe-placeholder {
  height: 650px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(10, 14, 26, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(0, 229, 255, 0.08);
}

.v-tabs {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.v-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
