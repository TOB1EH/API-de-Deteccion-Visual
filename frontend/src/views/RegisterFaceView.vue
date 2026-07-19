<template>
  <v-row align="center" justify="center" class="fill-height ma-0 bg-gradient">
    <v-col cols="12" sm="10" md="8" lg="6">
      <v-card variant="outlined" elevation="24" class="pa-8 glass-card border-cyber">
        <div class="text-center mb-6">
          <v-avatar size="72" color="cyan-accent-3" class="mb-4" variant="tonal">
            <v-icon size="36" color="cyan-accent-3">mdi-face-recognition</v-icon>
          </v-avatar>
          <h1 class="text-h5 font-weight-bold tracking-wide text-white">
            Registro <span class="text-cyan-accent-3">Facial</span>
          </h1>
          <p class="text-grey-lighten-1 text-subtitle-2 mt-1">
            Completa tus datos y sube al menos 4 fotos de tu rostro desde distintos angulos
          </p>
        </div>

        <v-alert v-if="errorMsg" type="error" variant="tonal" closable class="mb-4" @click:close="errorMsg = ''">
          <v-icon start>mdi-alert</v-icon>
          {{ errorMsg }}
        </v-alert>

        <v-alert v-if="successMsg" type="success" variant="tonal" closable class="mb-4" @click:close="successMsg = ''">
          <v-icon start>mdi-check-circle</v-icon>
          {{ successMsg }}
        </v-alert>

        <v-form @submit.prevent="handleRegister">
          <v-row>
            <v-col cols="6">
              <v-text-field v-model="form.nombre" label="Nombre *" prepend-inner-icon="mdi-account"
                :rules="[v => !!v || 'Obligatorio']" required />
            </v-col>
            <v-col cols="6">
              <v-text-field v-model="form.apellido" label="Apellido *" prepend-inner-icon="mdi-account"
                :rules="[v => !!v || 'Obligatorio']" required />
            </v-col>
          </v-row>
          <v-text-field v-model="form.email" label="Email *" type="email" prepend-inner-icon="mdi-email"
            :rules="[v => !!v || 'Obligatorio', v => /.+@.+/.test(v) || 'Email invalido']" required class="mb-2" />
          <v-text-field v-model="form.password" label="Contrasena *" type="password" prepend-inner-icon="mdi-lock"
            :rules="[v => !!v || 'Obligatorio', v => v.length >= 6 || 'Minimo 6 caracteres']" required class="mb-4" />

          <v-divider class="mb-4" />

          <div class="d-flex align-center mb-2">
            <span class="text-body-2 font-weight-bold text-white">Fotos del rostro (min. 4)</span>
            <v-spacer />
            <v-btn size="small" variant="tonal" color="primary" @click="triggerUpload" :disabled="photos.length >= 10">
              <v-icon start>mdi-camera-plus</v-icon>
              Agregar fotos
            </v-btn>
          </div>

          <div v-if="photos.length === 0" class="text-center pa-6 border-dashed rounded mb-4">
            <v-icon size="48" color="grey" class="mb-2">mdi-image-plus</v-icon>
            <p class="text-body-2 text-medium-emphasis">Selecciona al menos 4 fotos de tu rostro desde distintos angulos</p>
          </div>

          <v-row v-else class="mb-4">
            <v-col v-for="(photo, idx) in photos" :key="idx" cols="3">
              <v-card class="pa-1 text-center" variant="tonal">
                <v-img :src="photo.url" height="100" cover class="rounded mb-1" />
                <v-btn density="compact" variant="plain" size="x-small" color="error"
                  @click="photos.splice(idx, 1)">
                  <v-icon size="16">mdi-close</v-icon>
                </v-btn>
              </v-card>
            </v-col>
          </v-row>

          <input ref="fileInput" type="file" accept="image/*" multiple style="display: none" @change="onFilesSelected" />

          <v-btn color="cyan-accent-3" block size="large" class="text-none py-5 mt-2" elevation="6"
            :loading="loading" type="submit"
            :disabled="photos.length < 4 || !form.nombre || !form.apellido || !form.email || !form.password">
            <v-icon start>mdi-account-plus</v-icon>
            Registrarse
          </v-btn>
        </v-form>

        <div class="text-center mt-4">
          <span class="text-caption text-grey">Ya tenes cuenta? </span>
          <router-link to="/login" class="text-cyan-accent-3 text-caption">Inicia sesion</router-link>
        </div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { registerFace } from '../services/api'
import { localFaceDetect, checkLocalServer } from '../services/inference'

const router = useRouter()
const fileInput = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const photos = ref([])

const form = reactive({
  nombre: '',
  apellido: '',
  email: '',
  password: ''
})

function triggerUpload() {
  fileInput.value?.click()
}

async function onFilesSelected(e) {
  const files = Array.from(e.target.files || [])
  for (const file of files) {
    if (photos.value.length >= 10) break
    const url = URL.createObjectURL(file)
    const b64 = await fileToBase64Raw(file)
    photos.value.push({ file, url, b64, embedding: null })
  }
  e.target.value = ''
}

function fileToBase64Raw(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result.split(',')[1])
    reader.onerror = () => reject(new Error('Error al leer la imagen'))
    reader.readAsDataURL(file)
  })
}

async function handleRegister() {
  loading.value = true
  errorMsg.value = ''
  successMsg.value = ''

  try {
    const localOk = await checkLocalServer()
    if (!localOk) {
      throw new Error('El servidor de reconocimiento facial local no esta corriendo en http://localhost:8001')
    }

    const embeddings = []
    for (let idx = 0; idx < photos.value.length; idx++) {
      const photo = photos.value[idx]
      const blob = await fetch(photo.url).then(r => r.blob())
      const result = await localFaceDetect(blob)
      if (!result.embedding) {
        throw new Error(`Foto ${idx + 1}: no se detecto un rostro. Asegurate de que todas las fotos muestren tu rostro claramente.`)
      }
      embeddings.push(result.embedding)
    }

    const result = await registerFace({
      nombre: form.nombre,
      apellido: form.apellido,
      email: form.email,
      password: form.password,
      images: photos.value.map(p => p.b64),
      embeddings: embeddings
    })
    successMsg.value = result.message || 'Registro exitoso!'
    setTimeout(() => router.push('/login'), 2000)
  } catch (err) {
    const detail = err.response?.data?.detail
    if (err.response?.status === 409) {
      errorMsg.value = 'El email ya esta registrado. Inicia sesion o usa otro email.'
    } else if (err.response?.status === 400 && Array.isArray(detail)) {
      errorMsg.value = detail.map(d => d.msg).join(', ')
    } else {
      errorMsg.value = detail || err.message || 'Error al registrarse'
    }
  } finally {
    loading.value = false
  }
}
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
.border-dashed {
  border: 2px dashed rgba(255, 255, 255, 0.15);
}
.fill-height {
  min-height: 100vh;
}
</style>