<template>
  <v-row align="center" justify="center" class="fill-height ma-0" :style="bgStyle">
    <v-col cols="12" sm="8" md="5" lg="4">
      <v-card class="pa-8 glass-card" elevation="0">
        <div class="text-center mb-6">
          <v-avatar size="80" color="primary" class="mb-4 elevation-4">
            <v-icon size="40" color="white">mdi-cctv</v-icon>
          </v-avatar>
          <h1 class="text-h4 font-weight-bold mb-1">
            <span class="text-primary">API</span> Deteccion
          </h1>
          <p class="text-body-2 text-medium-emphasis mt-1">
            Sistema de analisis de fotogramas con deteccion y reconocimiento facial
          </p>
        </div>

        <!-- Formulario de login con Keycloak -->
        <v-form @submit.prevent="doLogin">
          <v-text-field
            v-model="username"
            label="Usuario"
            prepend-inner-icon="mdi-account"
            :disabled="loading"
            class="mb-3"
            autocomplete="username"
          />
          <v-text-field
            v-model="password"
            label="Contrasena"
            type="password"
            prepend-inner-icon="mdi-lock"
            :disabled="loading"
            class="mb-4"
            autocomplete="current-password"
          />

          <v-btn
            color="primary"
            block
            size="x-large"
            type="submit"
            class="text-none py-5 mb-3"
            elevation="4"
            :loading="loading"
          >
            <v-icon start size="24">mdi-login</v-icon>
            Iniciar sesion
          </v-btn>
        </v-form>

        <v-alert v-if="loginError" type="error" variant="tonal" class="mb-4" density="compact" border="start">
          {{ loginError }}
        </v-alert>

        <v-divider class="mb-4">
          <span class="text-caption text-medium-emphasis px-2">o</span>
        </v-divider>

        <v-btn
          variant="outlined"
          block
          class="text-none mb-4"
          color="grey"
          :disabled="loading"
          @click="$router.push('/cargar')"
        >
          <v-icon start size="16">mdi-test-tube</v-icon>
          Modo demo (sin autenticacion)
        </v-btn>

        <div class="text-center mt-4">
          <div class="d-flex justify-center ga-4 text-medium-emphasis">
            <span class="text-caption d-flex align-center">
              <v-icon size="14" class="mr-1">mdi-shield-check</v-icon>
              OAuth2
            </span>
            <span class="text-caption d-flex align-center">
              <v-icon size="14" class="mr-1">mdi-account-group</v-icon>
              3 roles
            </span>
            <span class="text-caption d-flex align-center">
              <v-icon size="14" class="mr-1">mdi-face-recognition</v-icon>
              Biometrico
            </span>
          </div>
          <p class="text-caption text-medium-emphasis mt-3">
            Usuarios de prueba: admin/admin123 &middot; viewer1/view123
          </p>
        </div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginWithKeycloak, storeUser } from '../services/auth'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const loginError = ref('')

const bgStyle = {
  background: 'linear-gradient(135deg, #1E3A5F 0%, #2563EB 50%, #7C3AED 100%)'
}

async function doLogin() {
  if (!username.value || !password.value) {
    loginError.value = 'Ingresa usuario y contrasena'
    return
  }

  loading.value = true
  loginError.value = ''

  try {
    const user = await loginWithKeycloak(username.value, password.value)
    storeUser(user)
    router.push('/cargar')
  } catch (err) {
    if (err.response?.status === 401) {
      loginError.value = 'Usuario o contrasena incorrectos'
    } else {
      // Keycloak no disponible: entra como demo con los datos ingresados
      const demoUser = { username: username.value, roles: ['demo'], email: '' }
      storeUser(demoUser)
      router.push('/cargar')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.v-theme--dark .glass-card {
  background: rgba(30, 41, 59, 0.95) !important;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
