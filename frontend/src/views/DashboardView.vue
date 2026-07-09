<template>
  <v-row class="pa-6">
    <v-col cols="12">
      <div class="d-flex align-center mb-6">
        <div>
          <h2 class="text-h4 font-weight-bold">Carga de fotograma</h2>
          <p class="text-body-2 text-medium-emphasis mt-1">Subi una imagen para procesar con el modelo de deteccion</p>
        </div>
        <v-spacer />
        <v-chip color="primary" variant="tonal" prepend-icon="mdi-information-outline" size="small">
          {{ models.length }} modelos disponibles
        </v-chip>
      </div>
    </v-col>

    <v-col cols="12" lg="7">
      <v-card class="pa-6">
        <div
          class="upload-zone"
          :class="{
            'upload-zone-active': isDragging,
            'upload-zone-has-file': imageFile,
            'upload-zone-disabled': loading
          }"
          @dragenter.prevent="!loading && (isDragging = true)"
          @dragover.prevent="!loading && (isDragging = true)"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="!loading && onDrop($event)"
          @click="!loading && triggerFileInput()"
        >
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            @change="onInputChange"
            style="display: none"
          />
          <v-icon v-if="!previewUrl" size="48" :color="isDragging ? 'primary' : 'grey'">
            {{ isDragging ? 'mdi-cloud-upload' : 'mdi-image-outline' }}
          </v-icon>
          <p v-if="!previewUrl" class="text-body-1 mt-3 font-weight-medium">
            {{ isDragging ? 'Solta la imagen aqui' : 'Arrastra una imagen o haz click para seleccionar' }}
          </p>
          <p v-if="!previewUrl" class="text-caption text-medium-emphasis mt-1">
            JPG, PNG, WebP
          </p>
          <v-img v-if="previewUrl" :src="previewUrl" max-height="300" contain class="rounded-lg" />
        </div>

        <v-divider class="my-5" />

        <v-row>
          <v-col cols="12" md="6">
            <v-select
              v-model="form.model_id"
              :items="models"
              item-title="name"
              item-value="name"
              label="Modelo"
              :disabled="loading"
              prepend-inner-icon="mdi-file-code"
              chips
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-slider
              v-model="form.confidence"
              label="Confianza minima"
              min="0"
              max="1"
              step="0.05"
              thumb-label
              :disabled="loading"
              color="primary"
              track-color="grey"
            />
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-model="form.latitude"
              label="Latitud"
              type="number"
              placeholder="-34.6037"
              prepend-inner-icon="mdi-map-marker"
              :disabled="loading"
            />
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-model="form.longitude"
              label="Longitud"
              type="number"
              placeholder="-58.3816"
              prepend-inner-icon="mdi-map-marker"
              :disabled="loading"
            />
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-model="form.camera_id"
              label="Camara (opcional)"
              prepend-inner-icon="mdi-camera-iris"
              :disabled="loading"
            />
          </v-col>
          <v-col cols="6">
            <v-btn
              v-if="imageFile"
              variant="tonal"
              color="error"
              class="text-none mt-1"
              @click="clearFile"
              :disabled="loading"
              block
            >
              <v-icon start>mdi-close</v-icon>
              Limpiar imagen
            </v-btn>
          </v-col>
        </v-row>

        <v-btn
          color="primary"
          size="x-large"
          block
          class="mt-4 text-none py-5"
          :loading="loading"
          :disabled="!canSubmit"
          @click="submitDetection"
          elevation="3"
        >
          <v-icon start size="24">mdi-cloud-upload</v-icon>
          Procesar fotograma
        </v-btn>
      </v-card>

      <v-alert v-if="error" type="error" class="mt-4" closable @click:close="error = ''" border="start">
        <template v-slot:title>Error</template>
        {{ error }}
      </v-alert>
    </v-col>

    <v-col cols="12" lg="5">
      <v-card v-if="result" class="pa-6" color="success" variant="tonal" border="start">
        <div class="d-flex align-center mb-4">
          <v-avatar color="success" size="40" class="mr-3">
            <v-icon color="white">mdi-check-circle</v-icon>
          </v-avatar>
          <div>
            <div class="font-weight-bold">Fotograma procesado</div>
            <div class="text-caption text-medium-emphasis">{{ result.timestamp }}</div>
          </div>
        </div>

        <v-sheet color="white" rounded="xl" class="pa-4">
          <div class="result-stats d-flex ga-4 mb-4">
            <v-sheet color="success" variant="tonal" rounded="lg" class="pa-3 flex-1-1 text-center">
              <div class="text-h6 font-weight-bold text-success">{{ result.detections_count }}</div>
              <div class="text-caption text-medium-emphasis">Detecciones</div>
            </v-sheet>
            <v-sheet color="success" variant="tonal" rounded="lg" class="pa-3 flex-1-1 text-center">
              <div class="text-h6 font-weight-bold text-success">{{ result.status }}</div>
              <div class="text-caption text-medium-emphasis">Estado</div>
            </v-sheet>
          </div>

          <v-text-field
            :model-value="result.frame_id"
            label="Frame ID"
            readonly
            density="compact"
            variant="outlined"
            hide-details
            class="mb-3"
          >
            <template v-slot:append-inner>
              <v-btn
                icon="mdi-content-copy"
                variant="text"
                size="x-small"
                @click="copyFrameId"
              />
            </template>
          </v-text-field>

          <v-btn
            color="primary"
            variant="flat"
            block
            class="text-none"
            :to="`/frame/${result.frame_id}`"
          >
            <v-icon start>mdi-eye</v-icon>
            Ver detecciones
          </v-btn>
        </v-sheet>
      </v-card>

      <v-card v-else class="pa-12 d-flex flex-column align-center justify-center empty-state">
        <v-icon size="64" color="grey" class="mb-4">mdi-image-search</v-icon>
        <p class="text-body-1 text-medium-emphasis text-center">
          Selecciona una imagen, completa los datos y presiona "Procesar fotograma"
        </p>
        <p class="text-caption text-medium-emphasis mt-2 text-center">
          Los resultados apareceran aqui
        </p>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { MOCK_MODELS, MOCK_FRAME_RESULT } from '../services/mock'

const fileInput = ref(null)
const imageFile = ref(null)
const previewUrl = ref(null)
const isDragging = ref(false)
const models = ref([])
const loading = ref(false)
const error = ref('')
const result = ref(null)

const form = reactive({
  model_id: '',
  latitude: '',
  longitude: '',
  confidence: 0.25,
  camera_id: ''
})

const canSubmit = computed(() =>
  imageFile.value &&
  form.model_id &&
  form.latitude !== '' &&
  form.longitude !== '' &&
  !loading.value
)

onMounted(() => {
  models.value = MOCK_MODELS.models
  if (MOCK_MODELS.models.length > 0) {
    form.model_id = MOCK_MODELS.models[0].name
  }
})

function triggerFileInput() {
  fileInput.value?.click()
}

function onInputChange(e) {
  const file = e.target.files?.[0]
  if (file) handleFile(file)
}

function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

function handleFile(file) {
  if (!file.type.startsWith('image/')) return
  imageFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  error.value = ''
  result.value = null
}

function clearFile() {
  imageFile.value = null
  previewUrl.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function copyFrameId() {
  if (result.value?.frame_id) {
    try {
      await navigator.clipboard.writeText(result.value.frame_id)
    } catch {}
  }
}

function submitDetection() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = ''
  result.value = null

  setTimeout(() => {
    result.value = {
      ...MOCK_FRAME_RESULT,
      timestamp: new Date().toLocaleString()
    }
    loading.value = false
  }, 1500)
}
</script>

<style scoped>
.upload-zone {
  border: 2px dashed rgba(100, 100, 100, 0.3);
  border-radius: 16px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;
}
.upload-zone:hover {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.04);
}
.upload-zone-active {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.08);
  transform: scale(1.01);
}
.upload-zone-has-file {
  border-style: solid;
  border-color: rgb(var(--v-theme-success));
  padding: 8px;
}
.upload-zone-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.upload-zone-disabled:hover {
  border-color: rgba(100, 100, 100, 0.3);
  background: transparent;
  transform: none;
}
.flex-1-1 { flex: 1; }
.empty-state {
  min-height: 380px;
}
</style>
