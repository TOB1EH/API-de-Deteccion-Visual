<template>
  <!-- Vista de detalle de un modelo de deteccion.
       Muestra informacion como nombre, tamano, tipo y ruta del archivo.
       Accesible desde la lista de modelos en Home o desde resultados de deteccion. -->
  <v-row class="pa-6">
    <v-col cols="12">
      <!-- Boton para volver atras -->
      <v-btn variant="text" class="mb-2 text-none" color="primary" @click="goBack">
        <v-icon start>mdi-arrow-left</v-icon>
        Volver
      </v-btn>
    </v-col>

    <v-col cols="12">
      <v-alert v-if="error" type="error" closable @click:close="error = ''" border="start">
        {{ error }}
      </v-alert>
    </v-col>

    <v-col cols="12" md="8" offset-md="2">
      <v-card v-if="model" :loading="loading">
        <!-- Encabezado con icono del modelo -->
        <div class="pa-6 d-flex align-center ga-4 border-b">
          <v-avatar color="amber" variant="tonal" size="64">
            <v-icon size="32" color="amber">mdi-brain</v-icon>
          </v-avatar>
          <div class="flex-grow-1">
            <div class="text-h5 font-weight-bold">{{ model.name }}</div>
            <div class="text-body-2 text-medium-emphasis">Modelo de deteccion YOLO</div>
          </div>
        </div>

        <!-- Detalles del modelo -->
        <v-list density="compact" class="pa-4">
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="primary" size="20">mdi-file-document</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Nombre del archivo</v-list-item-title>
            <v-list-item-subtitle class="text-body-2 font-family-monospace">{{ model.name }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="secondary" size="20">mdi-weight</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Tamano</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ formatSize(model.size) }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="success" size="20">mdi-code-tags</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Tipo</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ model.type || 'YOLO' }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg">
            <template v-slot:prepend><v-icon color="warning" size="20">mdi-folder</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Ruta</v-list-item-title>
            <v-list-item-subtitle class="text-body-2 font-family-monospace text-caption">{{ model.path }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card>

      <v-card v-else-if="loading" class="pa-12 d-flex justify-center">
        <v-progress-circular indeterminate color="primary" size="48" />
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getModelDetail } from '../services/api'

const route = useRoute()
const router = useRouter()

const model = ref(null)
const loading = ref(true)
const error = ref('')

// Carga los datos del modelo al montar la vista
onMounted(async () => {
  const modelName = route.params.name
  if (!modelName) {
    error.value = 'Nombre de modelo no valido'
    loading.value = false
    return
  }
  try {
    model.value = await getModelDetail(modelName)
  } catch (err) {
    error.value = 'Error al cargar el modelo: ' + (err.response?.data?.detail || err.message)
    console.error('[ModelDetail] Error:', err)
  } finally {
    loading.value = false
  }
})

// Formatea el tamano en bytes a una representacion legible (KB, MB, GB)
function formatSize(bytes) {
  if (!bytes) return '0 B'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i]
}

// Vuelve a la pagina anterior manteniendo el historial del navegador
function goBack() {
  router.back()
}
</script>
