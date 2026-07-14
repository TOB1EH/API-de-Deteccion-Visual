<template>
  <v-row class="pa-6">
    <v-col cols="12">
      <div class="d-flex align-center mb-6">
        <div>
          <h2 class="text-h4 font-weight-bold">Busqueda de fotogramas</h2>
          <p class="text-body-2 text-medium-emphasis mt-1">Filtra por clases detectadas y ubicacion geografica</p>
        </div>
        <v-spacer />
        <v-chip v-if="searched" color="primary" variant="tonal" size="small">
          {{ filteredFrames.length }} resultados
        </v-chip>
      </div>
    </v-col>

    <v-col cols="12">
      <v-card class="pa-4">
        <v-expansion-panels variant="accordion" flat>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2">
                <v-icon>mdi-filter-variant</v-icon>
                <span class="font-weight-medium">Filtros de busqueda</span>
                <v-chip v-if="hasActiveFilters" size="x-small" color="primary">activos</v-chip>
              </div>
            </v-expansion-panel-title>
                <v-expansion-panel-text>
              <v-row>
                <v-col cols="12" md="6" lg="4">
                  <v-text-field
                    v-model="filters.clases"
                    label="Clases"
                    placeholder="person, car, dog"
                    clearable
                    prepend-inner-icon="mdi-shape"
                    hint="Separadas por coma"
                    persistent-hint
                  />
                </v-col>
                <v-col cols="6" md="3" lg="2">
                  <v-text-field
                    v-model="filters.lat_min"
                    label="Latitud min"
                    type="number"
                    placeholder="-34.7"
                    prepend-inner-icon="mdi-arrow-down-bold"
                  />
                </v-col>
                <v-col cols="6" md="3" lg="2">
                  <v-text-field
                    v-model="filters.lat_max"
                    label="Latitud max"
                    type="number"
                    placeholder="-34.5"
                    prepend-inner-icon="mdi-arrow-up-bold"
                  />
                </v-col>
                <v-col cols="6" md="3" lg="2">
                  <v-text-field
                    v-model="filters.lon_min"
                    label="Longitud min"
                    type="number"
                    placeholder="-58.5"
                    prepend-inner-icon="mdi-arrow-left-bold"
                  />
                </v-col>
                <v-col cols="6" md="3" lg="2">
                  <v-text-field
                    v-model="filters.lon_max"
                    label="Longitud max"
                    type="number"
                    placeholder="-58.3"
                    prepend-inner-icon="mdi-arrow-right-bold"
                  />
                </v-col>
                <!-- Filtro por ID de camara (camera_id): permite buscar fotogramas
                     capturados por una camara especifica (ej: cam-001, cam-002).
                     El backend filtra por coincidencia exacta. -->
                <v-col cols="6" md="3" lg="2">
                  <v-text-field
                    v-model="filters.camera_id"
                    label="Camara ID"
                    placeholder="cam-001"
                    clearable
                    prepend-inner-icon="mdi-cctv"
                  />
                </v-col>
                <!-- Filtro por fuente de origen (source): permite buscar fotogramas
                     segun su procedencia (web, camara, mobile, upload).
                     Usa un v-select con opciones predefinidas. -->
                <v-col cols="6" md="3" lg="2">
                  <v-select
                    v-model="filters.source"
                    label="Fuente"
                    :items="['', 'web', 'camara', 'mobile', 'upload']"
                    clearable
                    prepend-inner-icon="mdi-source-branch"
                    hint="Origen de la imagen"
                    persistent-hint
                  />
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <div class="d-flex ga-2 mt-4">
          <v-btn
            color="primary"
            size="large"
            :loading="loading"
            @click="doSearch"
            class="text-none flex-grow-1"
            elevation="2"
          >
            <v-icon start>mdi-magnify</v-icon>
            Buscar
          </v-btn>
          <v-btn
            variant="tonal"
            size="large"
            @click="resetFilters"
            class="text-none"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
      </v-card>
    </v-col>

    <v-col cols="12">
      <v-alert v-if="error" type="error" closable @click:close="error = ''" border="start">
        {{ error }}
      </v-alert>
    </v-col>

    <v-col v-if="searched && filteredFrames.length > 0" cols="12">
      <div class="d-flex align-center mb-4">
        <span class="text-body-1 text-medium-emphasis">
          <strong class="text-primary">{{ filteredFrames.length }}</strong> fotogramas encontrados
        </span>
        <v-spacer />
        <v-select
          v-model="itemsPerPage"
          :items="[6, 12, 24, 48]"
          label="Por pagina"
          variant="outlined"
          density="compact"
          hide-details
          class="max-w-120"
          @update:model-value="page = 1"
        />
      </div>

      <v-row>
        <v-col
          v-for="frame in paginatedFrames"
          :key="frame.frame_id"
          cols="12"
          sm="6"
          lg="4"
          xl="3"
        >
          <FrameCard :frame="frame" />
        </v-col>
      </v-row>

      <div class="d-flex justify-center mt-4">
        <v-pagination
          v-model="page"
          :length="totalPages"
          :total-visible="5"
          rounded="circle"
          color="primary"
        />
      </div>
    </v-col>

    <v-col v-else-if="searched && filteredFrames.length === 0 && !loading" cols="12">
      <v-empty-state
        title="Sin resultados"
        text="No se encontraron fotogramas con esos filtros"
        icon="mdi-magnify-close"
      />
    </v-col>

    <v-col v-else-if="!searched && !loading" cols="12">
      <v-card class="pa-12 d-flex flex-column align-center justify-center empty-state">
        <v-icon size="80" color="grey" class="mb-4">mdi-image-search</v-icon>
        <p class="text-h6 text-medium-emphasis">Usa los filtros y presiona Buscar</p>
        <p class="text-caption text-medium-emphasis mt-1">Los resultados apareceran aqui</p>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
// SearchView - Vista de busqueda de fotogramas con filtros.
// Permite buscar por clases detectadas, rango de coordenadas (lat/lon),
// ID de camara (camera_id) y fuente de origen (source).
// Los filtros camera_id y source se agregaron para aprovechar el soporte
// que ya tenia el backend en GET /api/frames/search.
import { ref, reactive, computed } from 'vue'
import { searchFrames } from '../services/api'
import FrameCard from '../components/FrameCard.vue'

const loading = ref(false)
const error = ref('')
const searched = ref(false)
const filteredFrames = ref([])
const page = ref(1)
const itemsPerPage = ref(12)

// Calcula los frames a mostrar segun la pagina actual
const paginatedFrames = computed(() => {
  const start = (page.value - 1) * itemsPerPage.value
  return filteredFrames.value.slice(start, start + itemsPerPage.value)
})

// Calcula el total de paginas disponibles
const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredFrames.value.length / itemsPerPage.value))
)

// Objeto reactivo con todos los filtros de busqueda.
// Los campos camera_id y source se agregaron para permitir filtrar
// por camara especifica y fuente de origen respectivamente.
// El backend (GET /api/frames/search) ya soportaba estos parametros
// pero el frontend no los exponia en el formulario.
const filters = reactive({
  clases: '',
  lat_min: '',
  lat_max: '',
  lon_min: '',
  lon_max: '',
  camera_id: '',
  source: ''
})

// Detecta si hay algun filtro activo para mostrar el chip "activos".
// Incluye los nuevos filtros camera_id y source ademas de los clasicos.
const hasActiveFilters = computed(() =>
  filters.clases || filters.lat_min || filters.lat_max || filters.lon_min || filters.lon_max || filters.camera_id || filters.source
)

function resetFilters() {
  filters.clases = ''
  filters.lat_min = ''
  filters.lat_max = ''
  filters.lon_min = ''
  filters.lon_max = ''
  filters.camera_id = ''
  filters.source = ''
  searched.value = false
  filteredFrames.value = []
}

// Ejecuta la busqueda contra el backend con todos los filtros activos.
// Incluye los nuevos filtros camera_id y source en los parametros enviados.
// El mock de api.js ya filtra localmente estos campos si la API no responde.
async function doSearch() {
  searched.value = true
  loading.value = true
  error.value = ''

  try {
    const data = await searchFrames({
      clases: filters.clases,
      lat_min: filters.lat_min,
      lat_max: filters.lat_max,
      lon_min: filters.lon_min,
      lon_max: filters.lon_max,
      camera_id: filters.camera_id || undefined,
      source: filters.source || undefined
    })
    filteredFrames.value = data.frames || []
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Error al buscar fotogramas'
    filteredFrames.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.empty-state {
  min-height: 300px;
}
.max-w-120 { max-width: 120px; }
</style>
