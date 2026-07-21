<template>
  <v-row class="pa-6">
    <v-col cols="12">
      <div class="d-flex align-center mb-6">
        <div>
          <h2 class="text-h4 font-weight-bold text-cyan-accent-2">Reconocimiento facial</h2>
          <p class="text-body-2 text-cyan-lighten-4 mt-1">
            Subi una foto para identificar a la persona contra la base de datos
          </p>
        </div>
        <v-spacer />
        <v-chip color="cyan-accent-3" variant="tonal" prepend-icon="mdi-face-recognition" size="small">
          threshold: {{ threshold.toFixed(2) }}
        </v-chip>
      </div>
    </v-col>

    <v-col cols="12" lg="6">
      <!-- Zona de upload de foto -->
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
            {{ isDragging ? 'mdi-cloud-upload' : 'mdi-face-recognition' }}
          </v-icon>
          <p v-if="!previewUrl" class="text-body-1 mt-3 font-weight-medium">
            {{ isDragging ? 'Solta la imagen aqui' : 'Arrastra una foto o haz click para seleccionar' }}
          </p>
          <p v-if="!previewUrl" class="text-caption text-medium-emphasis mt-1">
            JPG, PNG, WebP
          </p>
          <v-img
            v-if="previewUrl"
            :src="previewUrl"
            max-height="300"
            contain
            class="rounded-lg"
          />
        </div>

        <v-divider class="my-5" />

        <!-- Slider de threshold -->
        <v-slider
          v-model="threshold"
          label="Threshold de confianza"
          min="0"
          max="1"
          step="0.05"
          thumb-label
          :disabled="loading"
          color="primary"
          track-color="grey"
          class="mb-4"
        >
          <template v-slot:append>
            <v-chip variant="tonal" size="small" class="font-weight-medium">
              {{ (threshold * 100).toFixed(0) }}%
            </v-chip>
          </template>
        </v-slider>

        <!-- Botones -->
        <div class="d-flex ga-2">
          <v-btn
            v-if="imageFile"
            variant="tonal"
            color="error"
            class="text-none"
            @click="clearFile"
            :disabled="loading"
          >
            <v-icon start>mdi-close</v-icon>
            Limpiar
          </v-btn>
          <v-btn
            color="primary"
            class="text-none flex-grow-1"
            :loading="loading"
            :disabled="!imageFile"
            @click="recognizeFace"
            elevation="3"
          >
            <v-icon start>mdi-face-recognition</v-icon>
            Reconocer rostro
          </v-btn>
        </div>
      </v-card>

      <v-alert v-if="error" type="error" class="mt-4" closable @click:close="error = ''" border="start">
        <template v-slot:title>Error</template>
        {{ error }}
      </v-alert>
    </v-col>

    <!-- Columna de resultado -->
    <v-col cols="12" lg="6">
      <v-card v-if="result" variant="outlined" color="cyan-accent-3" class="pa-6 bg-facial-card">
        <template v-if="result.person_id">
          <!-- MATCH: Coincidencia exitosa -->
          <div class="d-flex align-center mb-4">
            <v-avatar color="green-accent-3" size="48" class="mr-3">
              <v-icon color="black" size="28">mdi-face-recognition</v-icon>
            </v-avatar>
            <div>
              <div class="text-green-accent-3 font-weight-black text-h5">
                {{ result.nombre }} {{ result.apellido }}
              </div>
              <v-chip color="green-accent-3" class="text-black font-weight-bold" size="small">
                <v-icon start size="14">mdi-check-circle</v-icon>
                COINCIDENCIA EXITOSA
              </v-chip>
            </div>
          </div>

          <v-row class="mb-4">
            <v-col cols="6">
              <v-sheet color="#0d1b2a" variant="flat" rounded="lg" class="pa-4 text-center" border>
                <div class="text-h4 font-weight-bold text-green-accent-3">
                  {{ (result.confidence * 100).toFixed(0) }}%
                </div>
                <div class="text-caption text-cyan-lighten-4 font-weight-medium">Similitud</div>
              </v-sheet>
            </v-col>
            <v-col cols="6">
              <v-sheet color="#0d1b2a" variant="flat" rounded="lg" class="pa-4 text-center" border>
                <div class="text-h6 font-weight-bold text-green-accent-3 text-caption text-truncate">
                  {{ result.person_id }}
                </div>
                <div class="text-caption text-cyan-lighten-4 font-weight-medium">ID de Persona</div>
              </v-sheet>
            </v-col>
          </v-row>

          <v-sheet color="#0d1b2a" variant="flat" rounded="lg" class="pa-3 mb-4" border>
            <div class="d-flex justify-space-between py-1">
              <span class="text-cyan-lighten-4 font-weight-medium">Similitud:</span>
              <span class="text-green-accent-3 font-weight-bold">{{ (result.confidence * 100).toFixed(1) }}%</span>
            </div>
            <v-divider class="my-2 border-opacity-25" />
            <div class="d-flex justify-space-between py-1">
              <span class="text-cyan-lighten-4 font-weight-medium">Umbral minimo:</span>
              <span class="text-green-accent-3 font-weight-bold">{{ (threshold * 100).toFixed(0) }}%</span>
            </div>
            <v-divider class="my-2 border-opacity-25" />
            <div class="d-flex justify-space-between py-1">
              <span class="text-cyan-lighten-4 font-weight-medium">ID de Persona:</span>
              <span class="text-green-accent-3 font-weight-bold text-caption text-truncate ms-2" style="max-width: 160px;">{{ result.person_id }}</span>
            </div>
          </v-sheet>

          <v-row class="mb-0">
            <v-col cols="6">
              <v-card variant="outlined" color="cyan-darken-3" class="pa-3 text-center bg-photo-card">
                <div class="text-caption text-cyan-lighten-4 font-weight-medium mb-1">Foto de prueba</div>
                <v-img
                  :src="previewUrl"
                  max-height="120"
                  contain
                  class="rounded-lg"
                />
              </v-card>
            </v-col>
            <v-col cols="6">
              <v-card variant="outlined" color="cyan-darken-3" class="pa-3 text-center bg-photo-card">
                <div class="text-caption text-cyan-lighten-4 font-weight-medium mb-1">Foto registrada</div>
                <v-img
                  :src="result.image_url"
                  max-height="120"
                  contain
                  class="rounded-lg"
                />
              </v-card>
            </v-col>
          </v-row>
        </template>

        <template v-else>
          <!-- NO MATCH: Persona desconocida -->
          <div class="text-center mb-4">
            <v-avatar size="72" color="amber-darken-1" variant="tonal" class="mb-3">
              <v-icon size="44" color="amber-darken-1">mdi-account-question-outline</v-icon>
            </v-avatar>
            <div class="text-amber-darken-1 font-weight-bold text-h5">Sujeto no identificado</div>
            <p class="text-body-2 text-cyan-lighten-4 mt-1">
              No se encontro ninguna coincidencia con la confianza minima requerida
            </p>
            <v-chip color="error" class="text-white font-weight-bold" size="small">
              <v-icon start size="14">mdi-alert-circle</v-icon>
              DESCONOCIDO
            </v-chip>
          </div>

          <v-sheet color="#0d1b2a" variant="flat" rounded="lg" class="pa-3 mb-4" border>
            <div class="d-flex justify-space-between py-1">
              <span class="text-cyan-lighten-4 font-weight-medium">Similitud:</span>
              <span class="text-amber-darken-1 font-weight-bold">{{ (result.confidence * 100).toFixed(1) }}%</span>
            </div>
            <v-divider class="my-2 border-opacity-25" />
            <div class="d-flex justify-space-between py-1">
              <span class="text-cyan-lighten-4 font-weight-medium">Umbral minimo:</span>
              <span class="text-green-accent-3 font-weight-bold">{{ (threshold * 100).toFixed(0) }}%</span>
            </div>
            <v-divider class="my-2 border-opacity-25" />
            <div class="d-flex justify-space-between py-1">
              <span class="text-cyan-lighten-4 font-weight-medium">Estado:</span>
              <span class="text-amber-darken-1 font-weight-bold">Sin coincidencia</span>
            </div>
          </v-sheet>

          <v-row class="mb-0">
            <v-col cols="12">
              <v-card variant="outlined" color="cyan-darken-3" class="pa-3 text-center bg-photo-card">
                <div class="text-caption text-cyan-lighten-4 font-weight-medium mb-1">Foto de prueba</div>
                <v-img
                  :src="previewUrl"
                  max-height="180"
                  contain
                  class="rounded-lg"
                />
              </v-card>
            </v-col>
          </v-row>
        </template>
      </v-card>

      <!-- Estado vacio -->
      <v-card v-else variant="outlined" color="cyan-accent-3" class="pa-12 d-flex flex-column align-center justify-center empty-state bg-facial-card">
        <v-icon size="80" color="cyan-accent-2" class="mb-4">mdi-face-recognition</v-icon>
        <p class="text-h6 text-cyan-lighten-4 text-center">
          Subi una foto facial para comenzar el reconocimiento
        </p>
        <p class="text-caption text-cyan-lighten-4 mt-1 text-center">
          El sistema buscara coincidencias en la base de datos de personas registradas
        </p>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { recognizeFaceFromImage } from '../services/api'
import { checkLocalServer, localFaceRecognize } from '../services/inference'

const fileInput = ref(null)
const imageFile = ref(null)
const previewUrl = ref(null)
const isDragging = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref(null)
const useLocal = ref(false)

const threshold = ref(0.80)

onMounted(async () => {
  useLocal.value = await checkLocalServer()
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

async function recognizeFace() {
  if (!imageFile.value) return
  loading.value = true
  error.value = ''
  result.value = null

  try {
    if (useLocal.value) {
      const data = await localFaceRecognize(imageFile.value, threshold.value)
      result.value = data
    } else {
      const reader = new FileReader()
      reader.onload = async () => {
        try {
          const base64 = reader.result
          const data = await recognizeFaceFromImage(base64, threshold.value)
          result.value = data
        } catch (e) {
          error.value = e.message || 'Error al reconocer rostro'
        } finally {
          loading.value = false
        }
      }
      reader.onerror = () => {
        error.value = 'Error al leer la imagen'
        loading.value = false
      }
      reader.readAsDataURL(imageFile.value)
      return
    }
  } catch (e) {
    error.value = e.message || 'Error al reconocer rostro'
  }
  loading.value = false
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
.empty-state {
  min-height: 380px;
}
.bg-facial-card {
  background-color: #0d1b2a !important;
}
.bg-photo-card {
  background-color: #0a1525 !important;
}
</style>