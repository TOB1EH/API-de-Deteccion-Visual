<template>
  <v-container fluid class="pa-6">
    <!-- Fila de KPI Cards -->
    <v-row>
      <v-col v-for="kpi in kpis" :key="kpi.title" cols="12" sm="6" lg="3">
        <v-card
          variant="outlined"
          class="kpi-card pa-4"
          :style="{ borderColor: kpi.borderColor }"
          @mouseenter="kpi.hover = true"
          @mouseleave="kpi.hover = false"
        >
          <div class="d-flex align-center mb-3">
            <v-avatar
              :color="kpi.color"
              variant="tonal"
              size="44"
              class="mr-3"
            >
              <v-icon :color="kpi.color">{{ kpi.icon }}</v-icon>
            </v-avatar>
            <div>
              <div class="text-caption text-grey-lighten-1 font-weight-medium">{{ kpi.title }}</div>
              <div class="text-h4 font-weight-bold mt-1" :class="`text-${kpi.color}`">
                {{ kpi.value }}
              </div>
            </div>
          </div>
          <div class="d-flex align-center">
            <v-icon
              :color="kpi.trend >= 0 ? 'green-accent-3' : 'red-accent-3'"
              size="small"
              class="mr-1"
            >
              {{ kpi.trend >= 0 ? 'mdi-trending-up' : 'mdi-trending-down' }}
            </v-icon>
            <span
              class="text-caption"
              :class="kpi.trend >= 0 ? 'text-green-accent-3' : 'text-red-accent-3'"
            >
              {{ Math.abs(kpi.trend) }}% vs mes anterior
            </span>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Cuerpo principal -->
    <v-row class="mt-2">
      <!-- Columna izquierda: Actividad reciente -->
      <v-col cols="12" md="8">
        <v-card variant="outlined" class="pa-4">
          <div class="d-flex align-center mb-4">
            <v-icon color="cyan-accent-3" class="mr-2">mdi-image-multiple</v-icon>
            <h3 class="text-h6 font-weight-bold">Actividad Reciente</h3>
            <v-spacer />
            <v-chip
              variant="tonal"
              color="cyan-accent-3"
              size="x-small"
              class="font-weight-medium"
            >
              {{ recentFrames.length }} fotogramas
            </v-chip>
          </div>

          <v-row v-if="recentFrames.length > 0">
            <v-col
              v-for="frame in recentFrames"
              :key="frame.frame_id"
              cols="12" sm="6"
            >
              <v-card
                variant="outlined"
                class="frame-card"
                @click="goToFrame(frame.frame_id)"
              >
                <div class="frame-thumb-wrapper">
                  <v-img
                    :src="frame.image_url"
                    height="140"
                    cover
                    class="frame-thumb"
                  />
                  <div class="frame-overlay">
                    <v-chip
                      size="x-small"
                      color="cyan-darken-4"
                      class="frame-chip"
                    >
                      {{ frame.detections_count }} detecciones
                    </v-chip>
                  </div>
                </div>
                <v-card-text class="pa-3">
                  <div class="text-caption text-grey-lighten-1 font-weight-medium mb-1">
                    {{ formatDate(frame.created_at) }}
                  </div>
                  <div class="d-flex flex-wrap ga-1">
                    <v-chip
                      v-for="det in (frame.detections || []).slice(0, 3)"
                      :key="det.detection_id"
                      size="x-small"
                      variant="tonal"
                      color="cyan-accent-3"
                    >
                      {{ det.class_name }} {{ Math.round(det.confidence * 100) }}%
                    </v-chip>
                    <v-chip
                      v-if="(frame.detections || []).length > 3"
                      size="x-small"
                      variant="text"
                      color="grey"
                    >
                      +{{ (frame.detections || []).length - 3 }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <v-row v-else>
            <v-col cols="12">
              <v-card variant="outlined" class="pa-8 text-center">
                <v-icon size="48" color="grey-darken-1" class="mb-3">mdi-image-off</v-icon>
                <p class="text-grey">No hay fotogramas procesados aun.</p>
              </v-card>
            </v-col>
          </v-row>
        </v-card>
      </v-col>

      <!-- Columna derecha: Estado del servidor -->
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-4 mb-4">
          <div class="d-flex align-center mb-4">
            <v-icon color="green-accent-3" class="mr-2">mdi-server</v-icon>
            <h3 class="text-h6 font-weight-bold">Estado del Servidor</h3>
          </div>

          <div class="mb-4">
            <div class="d-flex justify-space-between text-caption mb-1">
              <span class="text-grey-lighten-1">CPU Inferencia</span>
              <span class="font-weight-medium">42%</span>
            </div>
            <v-progress-linear
              :model-value="42"
              color="cyan-accent-3"
              height="6"
              rounded
            />
          </div>

          <div class="mb-4">
            <div class="d-flex justify-space-between text-caption mb-1">
              <span class="text-grey-lighten-1">Memoria GPU</span>
              <span class="font-weight-medium">3.2 / 8 GB</span>
            </div>
            <v-progress-linear
              :model-value="40"
              color="indigo-accent-3"
              height="6"
              rounded
            />
          </div>

          <div>
            <div class="d-flex justify-space-between text-caption mb-1">
              <span class="text-grey-lighten-1">Uso de disco (SeaweedFS)</span>
              <span class="font-weight-medium">1.8 / 10 GB</span>
            </div>
            <v-progress-linear
              :model-value="18"
              color="amber"
              height="6"
              rounded
            />
          </div>
        </v-card>

        <v-card variant="outlined" class="pa-4">
          <div class="d-flex align-center mb-4">
            <v-icon color="amber" class="mr-2">mdi-brain</v-icon>
            <h3 class="text-h6 font-weight-bold">Modelos Activos</h3>
          </div>

          <div v-if="models.length > 0">
            <div
              <!-- Las cards de modelos ahora son clickeables (cursor: pointer)
                   y al hacer click navegan a ModelDetailView para ver detalle. -->
              v-for="model in models"
              :key="model.name"
              class="d-flex align-center pa-3 mb-2"
              style="border: 1px solid rgba(0, 229, 255, 0.15); border-radius: 8px; cursor: pointer;"
              @click="goToModel(model.name)"
            >
              <v-icon color="cyan-accent-3" class="mr-3" size="28">mdi-file-document-outline</v-icon>
              <div class="flex-grow-1">
                <div class="text-body-2 font-weight-medium">{{ model.name }}</div>
                <div class="text-caption text-grey-lighten-1">{{ formatSize(model.size) }}</div>
              </div>
              <v-chip
                size="x-small"
                color="green-accent-3"
                variant="tonal"
              >
                Activo
              </v-chip>
            </div>
          </div>

          <div v-else class="text-center pa-4">
            <v-progress-circular indeterminate color="cyan-accent-3" size="32" />
            <p class="text-caption text-grey mt-2">Cargando modelos...</p>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getModels, getPersons, searchFrames } from '../services/api'

const router = useRouter()

const kpis = ref([
  { title: 'Fotogramas Procesados', icon: 'mdi-image-multiple', color: 'cyan-accent-3', value: '0', trend: 0, borderColor: 'rgba(0, 229, 255, 0.3)', hover: false },
  { title: 'Detecciones Totales', icon: 'mdi-target', color: 'indigo-accent-3', value: '0', trend: 0, borderColor: 'rgba(99, 102, 241, 0.3)', hover: false },
  { title: 'Personas Registradas', icon: 'mdi-face-recognition', color: 'green-accent-3', value: '0', trend: 0, borderColor: 'rgba(0, 200, 83, 0.3)', hover: false },
  { title: 'Modelos YOLO Activos', icon: 'mdi-brain', color: 'amber', value: '0', trend: 0, borderColor: 'rgba(255, 193, 7, 0.3)', hover: false }
])

const recentFrames = ref([])
const models = ref([])

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i]
}

function goToFrame(frameId) {
  router.push(`/frame/${frameId}`)
}

// Navega al detalle del modelo seleccionado.
// Los modelos ahora son clickeables: al hacer click se abre la vista
// ModelDetailView con informacion detallada (tamano, tipo, ruta).
function goToModel(modelName) {
  router.push(`/modelo/${encodeURIComponent(modelName)}`)
}

onMounted(async () => {
  try {
    const [modelsData, personsData, framesData] = await Promise.all([
      getModels(),
      getPersons(),
      searchFrames({ limit: 6 })
    ])

    if (modelsData?.models) {
      models.value = modelsData.models
      kpis.value[3].value = String(modelsData.total || modelsData.models.length)
    }

    if (personsData?.persons) {
      kpis.value[2].value = String(personsData.total || personsData.persons.length)
    }

    if (framesData?.frames) {
      recentFrames.value = framesData.frames.slice(0, 6)
      kpis.value[0].value = String(framesData.total || framesData.frames.length)

      const totalDetections = framesData.frames.reduce((sum, f) => sum + (f.detections_count || 0), 0)
      kpis.value[1].value = String(totalDetections)
    }
  } catch (err) {
    console.error('[HomeView] Error cargando datos:', err)
  }
})
</script>

<style scoped>
.kpi-card {
  transition: all 0.25s ease;
  background: rgba(18, 18, 18, 0.8) !important;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 229, 255, 0.08);
}

.frame-card {
  cursor: pointer;
  transition: all 0.25s ease;
  background: rgba(18, 18, 18, 0.8) !important;
  overflow: hidden;
}

.frame-card:hover {
  border-color: rgba(0, 229, 255, 0.4) !important;
  transform: translateY(-2px);
}

.frame-thumb-wrapper {
  position: relative;
  overflow: hidden;
}

.frame-thumb {
  transition: transform 0.3s ease;
}

.frame-card:hover .frame-thumb {
  transform: scale(1.05);
}

.frame-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
}

.frame-chip {
  backdrop-filter: blur(4px);
}

.v-progress-linear {
  opacity: 0.85;
}

.v-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
