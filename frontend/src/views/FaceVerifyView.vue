<template>
  <v-row class="pa-6" align="center" justify="center">
    <v-col cols="12" sm="8" md="6" lg="5">
      <v-card variant="outlined" class="pa-6">
        <div class="text-center mb-6">
          <v-avatar color="cyan-accent-3" variant="tonal" size="64" class="mb-3">
            <v-icon size="32" color="cyan-accent-3">mdi-face-recognition</v-icon>
          </v-avatar>
          <h2 class="text-h5 font-weight-bold">Verificacion facial</h2>
          <p class="text-body-2 text-medium-emphasis mt-1">
            Como segundo factor de seguridad, tomate una foto para verificar tu identidad
          </p>
          <v-chip v-if="person" size="small" color="primary" variant="tonal" class="mt-2">
            Verificando: {{ person.nombre }} {{ person.apellido }}
          </v-chip>
        </div>

        <v-alert v-if="error" type="error" closable @click:close="error = ''" border="start" class="mb-4">
          {{ error }}
        </v-alert>

        <!-- Zona de captura de foto -->
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
            capture="user"
            @change="onInputChange"
            style="display: none"
          />
          <v-icon v-if="!previewUrl" size="48" :color="isDragging ? 'primary' : 'grey'">
            {{ isDragging ? 'mdi-cloud-upload' : 'mdi-camera-plus' }}
          </v-icon>
          <p v-if="!previewUrl" class="text-body-1 mt-3 font-weight-medium">
            {{ isDragging ? 'Solta la foto aqui' : 'Tocá para tomar o seleccionar una foto' }}
          </p>
          <p v-if="!previewUrl" class="text-caption text-medium-emphasis mt-1">
            Se usará para verificar tu identidad contra los rostros registrados
          </p>
          <v-img v-if="previewUrl" :src="previewUrl" max-height="280" contain class="rounded-lg" />
        </div>

        <!-- Slider de threshold -->
        <v-slider
          v-model="threshold"
          label="Umbral de confianza"
          min="0"
          max="1"
          step="0.05"
          thumb-label
          :disabled="loading"
          color="primary"
          track-color="grey"
          class="mt-4 mb-2"
        >
          <template v-slot:append>
            <v-chip variant="tonal" size="small" class="font-weight-medium">
              {{ (threshold * 100).toFixed(0) }}%
            </v-chip>
          </template>
        </v-slider>

        <!-- Botones -->
        <div class="d-flex ga-2 mt-4">
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
            @click="verifyFace"
            elevation="3"
          >
            <v-icon start size="24">mdi-face-recognition</v-icon>
            Verificar identidad
          </v-btn>
        </div>
      </v-card>

      <!-- Resultado -->
      <v-card v-if="result" :color="result.verified ? 'green-accent-3' : 'error'" variant="outlined" class="pa-5 mt-4">
        <div class="d-flex align-center">
          <v-icon size="36" :color="result.verified ? 'green-accent-3' : 'error'" class="mr-3">
            {{ result.verified ? 'mdi-check-circle' : 'mdi-alert-circle' }}
          </v-icon>
          <div>
            <div class="text-h6 font-weight-bold">
              {{ result.verified ? 'Identidad verificada' : 'Verificacion fallida' }}
            </div>
            <div class="text-body-2 mt-1">
              <template v-if="result.verified">
                Bienvenido, {{ result.nombre }} {{ result.apellido }}.
                Confianza: {{ (result.confidence * 100).toFixed(1) }}%
              </template>
              <template v-else>
                El rostro no coincide con la persona registrada.
                Confianza: {{ (result.confidence * 100).toFixed(1) }}%
                (minimo requerido: {{ (threshold * 100).toFixed(0) }}%)
              </template>
            </div>
          </div>
          <v-spacer />
          <v-btn
            v-if="result.verified"
            color="green-accent-3"
            variant="tonal"
            class="text-none"
            @click="goHome"
          >
            <v-icon start>mdi-arrow-right</v-icon>
            Ingresar
          </v-btn>
          <v-btn
            v-else
            variant="tonal"
            class="text-none"
            @click="clearFile"
          >
            <v-icon start>mdi-refresh</v-icon>
            Reintentar
          </v-btn>
        </div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fileToBase64, getFrameImageUrl } from '../services/api'
import { authState } from '../services/auth'
import axios from 'axios'

const router = useRouter()
const fileInput = ref(null)
const imageFile = ref(null)
const previewUrl = ref(null)
const isDragging = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref(null)
const threshold = ref(0.8)
const person = ref(null)

// Obtener la persona vinculada al usuario actual
onMounted(async () => {
  try {
    const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const baseURL = isLocalDev ? 'http://localhost:8000/api/' : 'https://bfts2026.mooo.com/api/'
    const resp = await axios.get(`${baseURL}persons/me`, {
      headers: { Authorization: `Bearer ${authState.token}` }
    })
    person.value = resp.data
    if (!resp.data.has_faces) {
      error.value = 'No tenes rostros registrados. Un administrador debe cargar fotos faciales primero.'
    }
  } catch (e) {
    if (e.response?.status === 404) {
      error.value = 'No hay persona vinculada a tu usuario. Un administrador debe crearla primero.'
    } else {
      error.value = 'Error al verificar tu identidad: ' + (e.response?.data?.detail || e.message)
    }
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
  result.value = null
  if (fileInput.value) fileInput.value.value = ''
}

async function verifyFace() {
  if (!imageFile.value) return
  loading.value = true
  error.value = ''
  result.value = null

  try {
    const image_base64 = await fileToBase64(imageFile.value)
    // Enviar la foto al backend para verificacion facial
    const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const baseURL = isLocalDev ? 'http://localhost:8000/api/' : 'https://bfts2026.mooo.com/api/'

    const resp = await axios.post(
      `${baseURL}auth/verify-face`,
      { image_base64: `data:image/jpeg;base64,${image_base64}`, threshold: threshold.value },
      { headers: { Authorization: `Bearer ${authState.token}` } }
    )
    result.value = resp.data
    if (resp.data.verified) {
      authState.faceVerified = true
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Error al verificar la identidad'
  } finally {
    loading.value = false
  }
}

function goHome() {
  router.push('/home')
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
</style>
