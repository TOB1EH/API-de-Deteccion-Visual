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
          <!-- Imagen: usa showThumbnail para alternar entre resolucion completa y miniatura -->
          <img
            :src="currentImageUrl"
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

        <!-- Botonera inferior: toggle thumbnail + descargas -->
        <div class="d-flex ga-2 mt-3 justify-end align-center">
          <!-- Indicador de resolucion actual -->
          <v-chip
            v-if="frame"
            size="x-small"
            :color="showThumbnail ? 'warning' : 'success'"
            variant="tonal"
            class="mr-auto"
          >
            <v-icon start size="14">{{ showThumbnail ? 'mdi-image-size-small' : 'mdi-image' }}</v-icon>
            {{ showThumbnail ? 'Miniatura' : 'Original' }}
          </v-chip>
          <!-- Toggle entre thumbnail y resolucion completa -->
          <v-btn
            v-if="frame"
            variant="tonal"
            class="text-none"
            size="small"
            @click="toggleThumbnail"
          >
            <v-icon start size="16">{{ showThumbnail ? 'mdi-image' : 'mdi-image-size-small' }}</v-icon>
            {{ showThumbnail ? 'Ver original' : 'Ver miniatura' }}
          </v-btn>
          <!-- Descargar resolucion original -->
          <v-btn variant="tonal" color="primary" class="text-none" size="small" @click="downloadImage('original')">
            <v-icon start size="16">mdi-download</v-icon>
            Original
          </v-btn>
          <!-- Descargar miniatura -->
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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getFrame, getFrameImageUrl } from '../services/api'
import DetectionOverlay from '../components/DetectionOverlay.vue'

const route = useRoute()

const frame = ref(null)
const error = ref('')
const naturalWidth = ref(0)
const naturalHeight = ref(0)

// Controla si se muestra la imagen original o la miniatura (thumbnail=true)
const showThumbnail = ref(false)

// URL actual de la imagen segun el toggle thumbnail.
// Usa la URL directa de SeaweedFS para la imagen original,
// y el endpoint de la API con ?thumbnail=true para la miniatura.
const currentImageUrl = computed(() => {
  if (!frame.value) return ''
  const frameId = frame.value.frame_id || route.params.id
  if (showThumbnail.value) {
    return getFrameImageUrl(frameId, true)
  }
  return frame.value.image_url
})

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

// Alterna entre mostrar la imagen original y la miniatura (thumbnail)
function toggleThumbnail() {
  showThumbnail.value = !showThumbnail.value
}

// Descarga la imagen (original o thumbnail) usando un enlace temporal.
// Para thumbnail, agrega el parametro ?thumbnail=true a la URL del backend.
// Para original, descarga la URL completa de SeaweedFS.
async function downloadImage(type) {
  const frameId = frame.value?.frame_id || route.params.id
  if (!frameId) return
  try {
    // Para thumbnail usa el endpoint de la API, para original usa SeaweedFS directo
    const url = type === 'thumbnail'
      ? getFrameImageUrl(frameId, true)
      : frame.value?.image_url
    if (!url) return

    const filename = type === 'thumbnail'
      ? `frame-${frameId}-thumbnail.jpg`
      : `frame-${frameId}.jpg`

    // Crea un enlace temporal para forzar la descarga
    const response = await fetch(url)
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    // Libera la URL creada para evitar memory leaks
    URL.revokeObjectURL(objectUrl)
  } catch (err) {
    console.error('[FrameDetail] Error descargando imagen:', err)
  }
}

onMounted(async () => {
  const frameId = route.params.id
  if (!frameId) {
    error.value = 'ID de fotograma no valido'
    return
  }
  try {
    const data = await getFrame(frameId)
    frame.value = data
  } catch (err) {
    error.value = 'Error al cargar el fotograma: ' + (err.response?.data?.detail || err.message)
    console.error('[FrameDetail] Error:', err)
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
