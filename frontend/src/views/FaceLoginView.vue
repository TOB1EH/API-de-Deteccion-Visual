<template>
  <v-row align="center" justify="center" class="fill-height ma-0 bg-gradient">
    <v-col cols="12" sm="8" md="5" lg="4">
      <v-card variant="outlined" elevation="24" class="pa-8 glass-card border-cyber">
        <div class="text-center mb-6">
          <v-avatar size="72" color="cyan-accent-3" class="mb-4" variant="tonal">
            <v-icon size="36" color="cyan-accent-3">mdi-face-recognition</v-icon>
          </v-avatar>
          <h1 class="text-h5 font-weight-bold tracking-wide text-white">
            Inicio <span class="text-cyan-accent-3">Facial</span>
          </h1>
          <p class="text-grey-lighten-1 text-subtitle-2 mt-1">
            Tomate una foto o subi una para iniciar sesion
          </p>
        </div>

        <v-alert v-if="errorMsg" type="error" variant="tonal" closable class="mb-4" @click:close="errorMsg = ''">
          <v-icon start>mdi-alert</v-icon>
          {{ errorMsg }}
        </v-alert>

        <div class="text-center mb-4">
          <v-img v-if="previewUrl" :src="previewUrl" max-width="250" class="rounded-lg mx-auto mb-3" />
          <v-icon v-else size="96" color="grey" class="mb-3">mdi-account-circle</v-icon>
        </div>

        <div class="d-flex ga-2 mb-4">
          <v-btn variant="tonal" color="primary" block class="text-none" @click="triggerFileUpload">
            <v-icon start>mdi-camera-plus</v-icon>
            Subir foto
          </v-btn>
          <v-btn v-if="!webcamActive" variant="tonal" color="cyan-accent-3" block class="text-none" @click="startWebcam">
            <v-icon start>mdi-webcam</v-icon>
            Usar webcam
          </v-btn>
          <v-btn v-else variant="tonal" color="error" block class="text-none" @click="captureWebcam">
            <v-icon start>mdi-camera</v-icon>
            Capturar
          </v-btn>
        </div>

        <video v-if="webcamActive" ref="videoRef" autoplay playsinline class="webcam-video rounded-lg mb-4" />

        <input ref="fileInput" type="file" accept="image/*" style="display: none" @change="onFileSelected" />

        <v-btn color="cyan-accent-3" block size="large" class="text-none py-5" elevation="6"
          :loading="loading" :disabled="!imageBase64" @click="handleLogin">
          <v-icon start>mdi-login</v-icon>
          Iniciar sesion
        </v-btn>

        <div class="text-center mt-4">
          <span class="text-caption text-grey">No tenes cuenta? </span>
          <router-link to="/registro-facial" class="text-cyan-accent-3 text-caption">Registrate</router-link>
        </div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { facialLogin } from '../services/api'
import { authService } from '../services/auth'

const router = useRouter()
const fileInput = ref(null)
const videoRef = ref(null)
const previewUrl = ref('')
const imageBase64 = ref('')
const loading = ref(false)
const errorMsg = ref('')
const webcamActive = ref(false)
let mediaStream = null

function triggerFileUpload() {
  stopWebcam()
  fileInput.value?.click()
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    imageBase64.value = reader.result
    previewUrl.value = reader.result
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

async function startWebcam() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
    webcamActive.value = true
    await nextTick()
    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream
    }
  } catch {
    errorMsg.value = 'No se pudo acceder a la webcam. Verifica los permisos.'
  }
}

function stopWebcam() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    mediaStream = null
  }
  webcamActive.value = false
}

function captureWebcam() {
  const video = videoRef.value
  if (!video) return
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  imageBase64.value = canvas.toDataURL('image/jpeg')
  previewUrl.value = imageBase64.value
  stopWebcam()
}

async function handleLogin() {
  if (!imageBase64.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    const result = await facialLogin({ image_base64: imageBase64.value })
    const token = result.access_token
    if (token) {
      authService.setToken(token)
      router.push('/home')
    } else {
      errorMsg.value = 'No se recibio un token de autenticacion'
    }
  } catch (err) {
    if (err.response?.status === 401) {
      errorMsg.value = 'Rostro no reconocido. Verifica tus fotos o registrate.'
    } else {
      errorMsg.value = err.response?.data?.detail || err.message || 'Error al iniciar sesion'
    }
  } finally {
    loading.value = false
  }
}

import { nextTick } from 'vue'
</script>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, #0a0e1a 0%, #0f1a2e 40%, #162240 100%) !important;
}
.glass-card {
  background: rgba(18, 26, 40, 0.85) !important;
  backdrop-filter: blur(16px);
}
.border-cyber {
  border: 1px solid rgba(0, 200, 255, 0.25) !important;
}
.webcam-video {
  width: 100%;
  max-width: 320px;
  display: block;
  margin: 0 auto;
  transform: scaleX(-1);
}
.fill-height {
  min-height: 100vh;
}
</style>