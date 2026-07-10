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

        <!-- Divisor -->
        <v-divider class="my-6 text-grey">
          O TAMBIEN PODIS
        </v-divider>

        <!-- Modo demo (bypass persistente para desarrollo) -->
        <v-btn
          variant="tonal"
          color="cyan-lighten-3"
          block
          class="text-none mb-3"
          @click="enterAsDemo"
        >
          <v-icon start size="18">mdi-test-tube</v-icon>
          Ingresar en Modo Demo (Bypass)
        </v-btn>

        <v-alert
          variant="outlined"
          density="compact"
          color="amber-darken-2"
          class="mt-2"
          border="start"
          icon="mdi-information-outline"
        >
          Entorno local de desarrollo. Los servicios reales se activaran en la Fase 2.
        </v-alert>

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

// Modo demo: activa el estado demo persistente y navega al dashboard
// Ningun guard ni interceptor puede revertir este estado (isDemoMode=true)
function enterAsDemo() {
  authService.enableDemoMode()
  router.push('/cargar')
}

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
      errorMessage.value = 'No se pudo conectar con el servidor de autenticacion. Verifique su red o use el Modo Demo.'
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
