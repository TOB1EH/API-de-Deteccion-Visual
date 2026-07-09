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

        <v-alert
          type="info"
          variant="tonal"
          class="mb-6"
          density="compact"
          icon="mdi-information-outline"
          border="start"
        >
          <template v-slot:title>Modo demo</template>
          <span class="text-caption">
            La autenticacion Keycloak estara disponible proximamente.
            Ingresa en modo demo para explorar el sistema.
          </span>
        </v-alert>

        <v-btn
          color="primary"
          block
          size="x-large"
          to="/cargar"
          class="text-none py-5 mb-3"
          elevation="4"
        >
          <v-icon start size="24">mdi-login</v-icon>
          Ingresar en modo demo
        </v-btn>

        <v-btn
          variant="outlined"
          block
          disabled
          class="text-none text-caption mt-2"
          color="grey"
        >
          <v-icon start size="16">mdi-key-variant</v-icon>
          Iniciar sesion con Keycloak (proximamente)
        </v-btn>

        <div class="text-center mt-6">
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
        </div>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
const bgStyle = {
  background: 'linear-gradient(135deg, #1E3A5F 0%, #2563EB 50%, #7C3AED 100%)'
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
