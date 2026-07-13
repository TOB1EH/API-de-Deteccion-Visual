<template>
  <!-- Vista de detalle individual de una persona.
       Muestra toda la informacion registrada: nombre, apellido, email,
       metadatos adicionales, fechas de creacion y actualizacion,
       y permite editar o eliminar desde esta vista. -->
  <v-row class="pa-6">
    <v-col cols="12">
      <!-- Boton para volver a la lista de personas -->
      <v-btn variant="text" to="/personas" class="mb-2 text-none" color="primary">
        <v-icon start>mdi-arrow-left</v-icon>
        Volver a personas
      </v-btn>
    </v-col>

    <v-col cols="12">
      <!-- Alerta de error si falla la carga -->
      <v-alert v-if="error" type="error" closable @click:close="error = ''" border="start">
        {{ error }}
      </v-alert>
    </v-col>

    <v-col cols="12" md="8" offset-md="2">
      <!-- Card principal con los datos de la persona -->
      <v-card v-if="person" :loading="loading">
        <!-- Encabezado con avatar y nombre -->
        <div class="pa-6 d-flex align-center ga-4 border-b">
          <v-avatar color="primary" size="64">
            <span class="text-h4 font-weight-bold text-white">
              {{ person.nombre?.charAt(0) }}{{ person.apellido?.charAt(0) }}
            </span>
          </v-avatar>
          <div class="flex-grow-1">
            <div class="text-h5 font-weight-bold">{{ person.nombre }} {{ person.apellido }}</div>
            <div class="text-body-2 text-medium-emphasis">{{ person.email || 'Sin email' }}</div>
          </div>
          <!-- Botones de accion: editar y eliminar -->
          <div class="d-flex ga-2">
            <v-btn color="warning" variant="tonal" class="text-none" @click="goToEdit">
              <v-icon start>mdi-pencil</v-icon>
              Editar
            </v-btn>
            <v-btn color="error" variant="tonal" class="text-none" @click="confirmDeletePerson">
              <v-icon start>mdi-delete</v-icon>
              Eliminar
            </v-btn>
          </div>
        </div>

        <!-- Cuerpo con detalles estructurados -->
        <v-list density="compact" class="pa-4">
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="primary" size="20">mdi-identifier</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">ID de persona</v-list-item-title>
            <v-list-item-subtitle class="font-family-monospace text-body-2">{{ person.person_id }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="secondary" size="20">mdi-account</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Nombre completo</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ person.nombre }} {{ person.apellido }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="warning" size="20">mdi-email</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Email</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ person.email || '-' }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg mb-1">
            <template v-slot:prepend><v-icon color="success" size="20">mdi-calendar</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Fecha de creacion</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ formatDate(person.created_at) }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item class="rounded-lg">
            <template v-slot:prepend><v-icon color="info" size="20">mdi-calendar-clock</v-icon></template>
            <v-list-item-title class="text-caption text-medium-emphasis">Ultima actualizacion</v-list-item-title>
            <v-list-item-subtitle class="text-body-2">{{ formatDate(person.updated_at) }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <!-- Seccion de metadatos adicionales si existen -->
        <v-expansion-panels v-if="person.metadata && Object.keys(person.metadata).length" variant="accordion" flat class="ma-4">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon start>mdi-json</v-icon>
              <span class="font-weight-medium">Metadatos adicionales</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <pre class="text-caption bg-grey-darken-4 pa-3 rounded">{{ JSON.stringify(person.metadata, null, 2) }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card>

      <!-- Estado de carga -->
      <v-card v-else-if="loading" class="pa-12 d-flex justify-center">
        <v-progress-circular indeterminate color="primary" size="48" />
      </v-card>
    </v-col>
  </v-row>

  <!-- Dialogo de confirmacion para eliminar desde detalle -->
  <v-dialog v-model="deleteDialog" max-width="400" transition="dialog-top-transition">
    <v-card class="pa-5">
      <div class="text-center mb-4">
        <v-avatar color="error" size="56" class="mb-3">
          <v-icon size="28" color="white">mdi-alert</v-icon>
        </v-avatar>
        <div class="text-h6 font-weight-bold">Eliminar persona</div>
        <p class="text-body-2 text-medium-emphasis mt-2">
          ¿Estas seguro de eliminar a <strong>{{ person?.nombre }} {{ person?.apellido }}</strong>?
          <br>Se eliminaran tambien todos sus embeddings faciales asociados.
        </p>
      </div>
      <div class="d-flex ga-2 justify-end">
        <v-btn variant="tonal" @click="deleteDialog = false" class="text-none">Cancelar</v-btn>
        <v-btn color="error" @click="doDeletePerson" :loading="deleting" class="text-none">
          <v-icon start>mdi-delete</v-icon>
          Eliminar
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPerson, deletePerson } from '../services/api'

const route = useRoute()
const router = useRouter()

const person = ref(null)
const loading = ref(true)
const error = ref('')
const deleteDialog = ref(false)
const deleting = ref(false)

// Carga los datos de la persona al montar la vista
onMounted(async () => {
  const personId = route.params.id
  if (!personId) {
    error.value = 'ID de persona no valido'
    loading.value = false
    return
  }
  try {
    person.value = await getPerson(personId)
  } catch (err) {
    error.value = 'Error al cargar la persona: ' + (err.response?.data?.detail || err.message)
    console.error('[PersonDetail] Error:', err)
  } finally {
    loading.value = false
  }
})

// Formatea una fecha ISO a formato local legible
function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('es-AR', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

// Navega a la vista de personas con la persona seleccionada para editar
function goToEdit() {
  router.push('/personas')
}

// Muestra el dialogo de confirmacion de eliminacion
function confirmDeletePerson() {
  deleteDialog.value = true
}

// Ejecuta la eliminacion y redirige a la lista de personas
async function doDeletePerson() {
  if (!person.value) return
  deleting.value = true
  try {
    await deletePerson(person.value.person_id)
    router.push('/personas')
  } catch (err) {
    console.error('Error al eliminar persona:', err)
    error.value = 'Error al eliminar la persona'
  } finally {
    deleting.value = false
    deleteDialog.value = false
  }
}
</script>
