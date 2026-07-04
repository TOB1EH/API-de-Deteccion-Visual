<template>
  <v-row class="pa-6">
    <v-col cols="12">
      <div class="d-flex align-center mb-6">
        <div>
          <h2 class="text-h4 font-weight-bold">Busqueda de fotogramas</h2>
          <p class="text-body-2 text-medium-emphasis mt-1">Filtra por clases detectadas y ubicacion geografica</p>
        </div>
        <v-spacer />
        <v-chip v-if="result" color="primary" variant="tonal" size="small">
          {{ result.total }} resultados
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
                <v-col cols="6" md="3" lg="2">
                  <v-text-field
                    v-model="filters.limit"
                    label="Por pagina"
                    type="number"
                    :min="1"
                    :max="200"
                    prepend-inner-icon="mdi-page-last"
                    hide-details
                  />
                </v-col>
                <v-col cols="6" md="3" lg="2">
                  <v-text-field
                    v-model="filters.offset"
                    label="Offset"
                    type="number"
                    :min="0"
                    prepend-inner-icon="mdi-page-first"
                    hide-details
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

    <v-col v-if="result" cols="12">
      <div class="d-flex align-center mb-4">
        <span class="text-body-1 text-medium-emphasis">
          <strong class="text-primary">{{ result.total }}</strong> fotogramas encontrados
        </span>
        <v-spacer />
        <v-pagination
          v-if="totalPages > 1"
          v-model="currentPage"
          :length="totalPages"
          :total-visible="5"
          size="small"
          @update:model-value="onPageChange"
        />
      </div>

      <v-row>
        <v-col
          v-for="frame in result.frames"
          :key="frame.frame_id"
          cols="12"
          sm="6"
          lg="4"
          xl="3"
        >
          <FrameCard :frame="frame" />
        </v-col>
      </v-row>

      <div class="d-flex align-center justify-center mt-4">
        <v-pagination
          v-if="totalPages > 1"
          v-model="currentPage"
          :length="totalPages"
          :total-visible="7"
          @update:model-value="onPageChange"
        />
      </div>
    </v-col>

    <v-col v-else-if="!loading" cols="12">
      <v-card class="pa-12 d-flex flex-column align-center justify-center empty-state">
        <v-icon size="80" color="grey" class="mb-4">mdi-image-search</v-icon>
        <p class="text-h6 text-medium-emphasis">Usa los filtros y presiona Buscar</p>
        <p class="text-caption text-medium-emphasis mt-1">Los resultados apareceran aqui</p>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { MOCK_SEARCH_RESULTS } from '../services/mock'
import FrameCard from '../components/FrameCard.vue'

const loading = ref(false)
const error = ref('')
const result = ref(null)
const currentPage = ref(1)

const filters = reactive({
  clases: '',
  lat_min: '',
  lat_max: '',
  lon_min: '',
  lon_max: '',
  limit: 50,
  offset: 0
})

const hasActiveFilters = computed(() =>
  filters.clases || filters.lat_min || filters.lat_max || filters.lon_min || filters.lon_max
)

const totalPages = computed(() => {
  if (!result.value) return 0
  const limit = parseInt(filters.limit) || 50
  return Math.ceil(result.value.total / limit)
})

function resetFilters() {
  filters.clases = ''
  filters.lat_min = ''
  filters.lat_max = ''
  filters.lon_min = ''
  filters.lon_max = ''
  filters.limit = 50
  filters.offset = 0
  currentPage.value = 1
  result.value = null
}

function onPageChange(page) {
  filters.offset = (page - 1) * (parseInt(filters.limit) || 50)
  doSearch()
}

function doSearch() {
  loading.value = true
  error.value = ''
  result.value = null

  setTimeout(() => {
    result.value = {
      ...MOCK_SEARCH_RESULTS,
      total: MOCK_SEARCH_RESULTS.total,
      frames: MOCK_SEARCH_RESULTS.frames
    }
    loading.value = false
  }, 600)
}
</script>

<style scoped>
.empty-state {
  min-height: 300px;
}
</style>
