<template>
  <v-row align="center" justify="center" class="fill-height ma-0 bg-gradient">
    <v-col cols="12" sm="8" md="5" lg="4">
      <v-card
        variant="outlined"
        elevation="24"
        max-width="450"
        class="pa-8 glass-card border-cyber"
      >
        <!-- Cabecera -->
        <div class="text-center mb-6">
          <v-avatar size="72" color="cyan-accent-3" class="mb-4" variant="tonal">
            <v-icon size="36" color="cyan-accent-3">mdi-shield-eye</v-icon>
          </v-avatar>
          <h1 class="text-h5 font-weight-bold tracking-wide text-white">
            <span class="text-cyan-accent-3">API</span> Deteccion Visual
          </h1>
          <p class="text-grey-lighten-1 text-subtitle-2 mt-1">
            Plataforma de Reconocimiento y Analisis de Fotogramas
          </p>
        </div>

        <!-- Boton Keycloak real -->
        <v-btn
          color="indigo-darken-2"
          block
          size="large"
          class="text-none py-5 mb-2"
          elevation="6"
          :loading="keycloakLoading"
          @click="handleKeycloakLogin"
        >
          <v-icon start size="22">mdi-key-variant</v-icon>
          Iniciar sesion con Keycloak
        </v-btn>

        <p class="text-caption text-grey mt-1 mb-4 text-center">
          Autenticacion corporativa OAuth2 con Keycloak
        </p>

        <!-- Boton de Google (Social Login via Keycloak IdP) -->
        <v-btn
          color="red-darken-2"
          block
          size="large"
          class="text-none py-5 mb-2"
          elevation="4"
          :loading="keycloakLoading"
          @click="handleGoogleLogin"
        >
          <v-icon start size="22">mdi-google</v-icon>
          Iniciar sesion con Google
        </v-btn>

        <p class="text-caption text-grey mt-1 mb-4 text-center">
          Requiere configurar credenciales de Google OAuth en Keycloak admin
        </p>

        <v-divider class="my-4" />

        <p class="text-caption text-grey mb-3 text-center font-weight-bold">
          <v-icon size="14" class="mr-1">mdi-face-recognition</v-icon>
          AUTENTICACION FACIAL
        </p>

        <v-btn
          color="cyan-accent-3"
          block
          size="large"
          class="text-none py-5 mb-2"
          elevation="6"
          @click="router.push('/login-facial')"
        >
          <v-icon start size="22">mdi-face-recognition</v-icon>
          Iniciar sesion con rostro
        </v-btn>

        <v-divider class="my-4" />

        <!-- Footer badges -->
        <div class="text-center mt-6">
          <div class="d-flex justify-center ga-4 text-grey-lighten-2">
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
        </div>
      </v-card>
    </v-col>

    <!-- Snackbar para errores de Keycloak -->
    <v-snackbar
      v-model="showError"
      color="error"
      timeout="5000"
      location="top"
    >
      <v-icon start size="18">mdi-alert-circle</v-icon>
      {{ errorMessage }}
      <template v-slot:actions>
        <v-btn color="white" variant="text" @click="showError = false">Cerrar</v-btn>
      </template>
    </v-snackbar>
  </v-row>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/auth'

const router = useRouter()
const keycloakLoading = ref(false)
const showError = ref(false)
const errorMessage = ref('')

// Keycloak login con timeout de seguridad
// keycloak.login() redirige el navegador. Si el servidor esta caido o
// no inicializado, la redireccion nunca ocurre. El timeout detecta eso.
function handleKeycloakLogin() {
  keycloakLoading.value = true
  authService.login()
  // Si Keycloak no redirige en 5 segundos, mostramos error
  setTimeout(() => {
    if (keycloakLoading.value) {
      keycloakLoading.value = false
      errorMessage.value = 'No se pudo conectar con el servidor de autenticacion. Verifique su red.'
      showError.value = true
    }
  }, 5000)
}

// Login con Google (Social Login via Keycloak Identity Provider)
// keycloak.login({ idpHint: 'google' }) redirige directamente a la pantalla
// de autenticacion de Google, omitiendo el formulario de Keycloak.
// Requiere que el IdP de Google este configurado en Keycloak (realm JSON).
function handleGoogleLogin() {
  keycloakLoading.value = true
  try {
    // idpHint le indica a Keycloak que use el proveedor de identidad "google"
    authService.loginWithIdp('google')
  } catch (e) {
    keycloakLoading.value = false
    errorMessage.value = 'Error al iniciar login con Google: ' + e.message
    showError.value = true
  }
  // Timeout de seguridad igual que el login normal
  setTimeout(() => {
    if (keycloakLoading.value) {
      keycloakLoading.value = false
      errorMessage.value = 'No se pudo conectar con Google. Verifique su red.'
      showError.value = true
    }
  }, 5000)
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

.v-theme--dark .glass-card {
  background: rgba(18, 26, 40, 0.85) !important;
}

.fill-height {
  min-height: 100vh;
}
</style>
