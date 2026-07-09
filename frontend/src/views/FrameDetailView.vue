<template>
  <v-row class="pa-6">
    <v-col cols="12">
      <v-btn variant="text" to="/buscar" class="mb-2 text-none" color="primary">
        <v-icon start>mdi-arrow-left</v-icon>
        Volver a busqueda
      </v-btn>
      <h2 class="text-h4 font-weight-bold">Detalle del fotograma</h2>
    </v-col>

    <v-col cols="12">
      <v-alert v-if="error" type="error" closable @click:close="error = ''" border="start">
        {{ error }}
      </v-alert>
    </v-col>

    <v-col cols="12" lg="8">
      <v-card class="pa-2" :loading="!frame">
        <div
          ref="imageContainer"
          class="position-relative rounded-lg overflow-hidden"
          style="background: #1a1a2e;"
        >
          <img
            :src="frame?.image_url"
            alt="Fotograma"
            class="d-block w-100"
            style="max-height: 650px; object-fit: contain;"
            @load="onImageLoad"
          />
          <DetectionOverlay
            v-if="frame && naturalWidth && naturalHeight"
            :detections="frame.detections"
            :width="naturalWidth"
            :height="naturalHeight"
          />
        </div>

        <div class="d-flex ga-2 mt-3 justify-end">
          <v-btn variant="tonal" color="primary" class="text-none" size="small" @click="downloadImage('original')">
            <v-icon start size="16">mdi-download</v-icon>
            Original
          </v-btn>
          <v-btn variant="tonal" class="text-none" size="small" @click="downloadImage('thumbnail')">
            <v-icon start size="16">mdi-image-size-small</v-icon>
            Thumbnail
          </v-btn>
        </div>
      </v-card>
    </v-col>

    <v-col cols="12" lg="4">
      <v-card v-if="frame" class="mb-4">
        <div class="pa-4 d-flex align-center ga-3 border-b">
          <v-avatar color="primary" variant="tonal" size="36">
            <v-icon>mdi-information</v-icon>
          </v-avatar>
          <div>
            <div class="font-weight-medium">Metadatos</div>
            <div class="text-caption text-medium-emphasis">Informacion del fotograma</div>
          </div>
        </div>
        <v-list density="compact" class="pa-2">
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="primary" size="18">mdi-identifier</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Frame ID</v-list-item-title>
            <v-list-item-subtitle class="font-family-monospace text-body-2">{{ frame.frame_id }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="secondary" size="18">mdi-file-code</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Modelo</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ frame.model_id }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="error" size="18">mdi-map-marker</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Ubicacion</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ frame.latitude }}, {{ frame.longitude }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="success" size="18">mdi-counter</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Detecciones</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ frame.detections?.length || 0 }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg">
            <template v-slot:prepend><v-icon color="warning" size="18">mdi-clock-outline</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Fecha</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ new Date(frame.created_at).toLocaleString() }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card>

      <v-card v-if="frame" class="mb-4">
        <div class="pa-4 d-flex align-center ga-3 border-b">
          <v-avatar color="success" variant="tonal" size="36">
            <v-icon>mdi-format-list-bulleted</v-icon>
          </v-avatar>
          <div>
            <div class="font-weight-medium">Detecciones</div>
            <div class="text-caption text-medium-emphasis">{{ frame.detections?.length || 0 }} objetos detectados</div>
          </div>
        </div>
        <v-table density="compact" class="det-table">
          <thead>
            <tr>
              <th class="text-body-2 font-weight-bold">Clase</th>
              <th class="text-body-2 font-weight-bold text-right">Confianza</th>
              <th class="text-body-2 font-weight-bold">Ubicacion (bbox)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="det in frame.detections" :key="det.detection_id" class="det-row">
              <td>
                <v-chip
                  :color="getColor(det.class_name)"
                  size="x-small"
                  text-color="white"
                  class="font-weight-medium"
                >
                  {{ det.class_name }}
                </v-chip>
              </td>
              <td class="text-right font-weight-medium">
                {{ (det.confidence * 100).toFixed(0) }}%
              </td>
              <td class="text-caption font-family-monospace text-medium-emphasis" style="font-size: 11px;">
                [{{ det.bbox.x_min }}, {{ det.bbox.y_min }}, {{ det.bbox.x_max }}, {{ det.bbox.y_max }}]
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getFrame } from '../services/api'
import DetectionOverlay from '../components/DetectionOverlay.vue'

defineProps({ id: String })
const route = useRoute()

const frame = ref(null)
const error = ref('')
const naturalWidth = ref(0)
const naturalHeight = ref(0)

const CLASS_COLORS = {
  person: 'red',
  car: 'blue',
  dog: 'orange',
  bicycle: 'green',
  cat: 'purple',
  default: 'grey'
}

function getColor(className) {
  return CLASS_COLORS[className?.toLowerCase()] || CLASS_COLORS.default
}

function onImageLoad(e) {
  const img = e.target
  naturalWidth.value = img.naturalWidth
  naturalHeight.value = img.naturalHeight
}

onMounted(async () => {
  const frameId = route.params.id
  try {
    const data = await getFrame(frameId)
    frame.value = data
  } catch (err) {
    error.value = 'Error al cargar el fotograma: ' + (err.response?.data?.detail || err.message)
  }
})
</script>

<style scoped>
.position-relative {
  position: relative;
}
.w-100 {
  width: 100%;
}
.det-table th {
  background: rgba(var(--v-theme-primary), 0.04);
}
.det-row {
  transition: background 0.15s;
}
.det-row:hover {
  background: rgba(var(--v-theme-primary), 0.03);
}
</style>
