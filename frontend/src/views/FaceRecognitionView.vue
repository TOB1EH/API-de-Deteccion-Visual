<template>
  <v-row class="pa-6">
    <v-col cols="12">
      <div class="d-flex align-center mb-6">
        <div>
          <h2 class="text-h4 font-weight-bold">Reconocimiento facial</h2>
          <p class="text-body-2 text-medium-emphasis mt-1">
            Subi una foto para identificar a la persona contra la base de datos
          </p>
        </div>
        <v-spacer />
        <v-chip color="primary" variant="tonal" prepend-icon="mdi-face-recognition" size="small">
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
            size="x-large"
            block
            class="text-none py-5"
            :loading="loading"
            :disabled="!imageFile"
            @click="recognizeFace"
            elevation="3"
          >
            <v-icon start size="24">mdi-face-recognition</v-icon>
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
      <v-card v-if="result" class="pa-6" border="start">
        <!-- Card verde: reconocido -->
        <template v-if="result.person_id">
          <div class="d-flex align-center mb-4">
            <v-avatar size="64" class="mr-4 elevation-3">
              <v-img :src="result.image_url" alt="Rostro" />
            </v-avatar>
            <div>
              <div class="text-h5 font-weight-bold">
                {{ result.nombre }} {{ result.apellido }}
              </div>
              <v-chip color="success" size="small" class="mt-1 font-weight-medium">
                <v-icon start size="14">mdi-check-circle</v-icon>
                Reconocido
              </v-chip>
            </div>
          </div>

          <v-sheet color="success" variant="tonal" rounded="xl" class="pa-4">
            <v-row>
              <v-col cols="6" class="text-center">
                <div class="text-h5 font-weight-bold text-success">
                  {{ (result.confidence * 100).toFixed(0) }}%
                </div>
                <div class="text-caption text-medium-emphasis">Confianza</div>
              </v-col>
              <v-col cols="6" class="text-center">
                <div class="text-h5 font-weight-bold text-success">
                  {{ result.person_id }}
                </div>
                <div class="text-caption text-medium-emphasis">Persona ID</div>
              </v-col>
            </v-row>
          </v-sheet>
        </template>

        <!-- Card roja: no reconocido -->
        <template v-else>
          <div class="text-center mb-4">
            <v-avatar size="80" color="error" variant="tonal" class="mb-3">
              <v-icon size="48" color="error">mdi-face-recognition</v-icon>
            </v-avatar>
            <div class="text-h5 font-weight-bold">Persona no identificada</div>
            <p class="text-body-2 text-medium-emphasis mt-1">
              No se encontro ninguna coincidencia con la confianza minima requerida
            </p>
          </div>

          <v-sheet color="error" variant="tonal" rounded="xl" class="pa-4">
            <div class="text-center">
              <div class="text-h5 font-weight-bold text-error">
                {{ (result.confidence * 100).toFixed(0) }}%
              </div>
              <div class="text-caption text-medium-emphasis">
                Confianza obtenida (minima requerida: {{ (threshold * 100).toFixed(0) }}%)
              </div>
            </div>
          </v-sheet>
        </template>
      </v-card>

      <!-- Estado vacio -->
      <v-card v-else class="pa-12 d-flex flex-column align-center justify-center empty-state">
        <v-icon size="80" color="grey" class="mb-4">mdi-face-recognition</v-icon>
        <p class="text-h6 text-medium-emphasis text-center">
          Subi una foto facial para comenzar el reconocimiento
        </p>
        <p class="text-caption text-medium-emphasis mt-1 text-center">
          El sistema buscara coincidencias en la base de datos de personas registradas
        </p>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { MOCK_RECOGNITION, MOCK_RECOGNITION_FAIL } from '../services/mock'

const fileInput = ref(null)
const imageFile = ref(null)
const previewUrl = ref(null)
const isDragging = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref(null)

// Threshold de confianza: valor minimo para considerar un reconocimiento valido
const threshold = ref(0.80)

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

function recognizeFace() {
  if (!imageFile.value) return
  loading.value = true
  error.value = ''
  result.value = null

  // Simula el tiempo de procesamiento del reconocimiento facial
  setTimeout(() => {
    // Decide aleatoriamente si el reconocimiento es exitoso o no
    // Simula que la confianza obtenida es mayor o menor al threshold
    const isMatch = Math.random() > 0.4

    if (isMatch) {
      result.value = {
        ...MOCK_RECOGNITION,
        confidence: Math.min(threshold.value + Math.random() * 0.15, 0.99)
      }
    } else {
      result.value = {
        ...MOCK_RECOGNITION_FAIL,
        confidence: Math.max(threshold.value - Math.random() * 0.3, 0.1)
      }
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
.empty-state {
  min-height: 380px;
}
</style>
