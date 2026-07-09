<template>
  <v-row class="pa-6">
    <v-col cols="12">
      <div class="d-flex align-center mb-6">
        <div>
          <h2 class="text-h4 font-weight-bold">Gestion de personas</h2>
          <p class="text-body-2 text-medium-emphasis mt-1">Registra personas y asocia sus rostros para reconocimiento facial</p>
        </div>
        <v-spacer />
        <v-chip color="primary" variant="tonal" prepend-icon="mdi-account-group" size="small">
          {{ persons.length }} registros
        </v-chip>
      </div>
    </v-col>

    <v-col cols="12">
      <v-card>
        <div class="pa-4 d-flex align-center border-b">
          <v-text-field
            v-model="search"
            label="Buscar personas..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            class="max-w-300"
          />
          <v-spacer />
          <v-btn color="primary" @click="openNewDialog" class="text-none" elevation="2">
            <v-icon start>mdi-account-plus</v-icon>
            Nueva persona
          </v-btn>
        </div>

        <v-table class="persons-table">
          <thead>
            <tr>
              <th class="text-body-2 font-weight-bold">Nombre</th>
              <th class="text-body-2 font-weight-bold">Apellido</th>
              <th class="text-body-2 font-weight-bold">Email</th>
              <th class="text-body-2 font-weight-bold">Registro</th>
              <th class="text-body-2 font-weight-bold text-center">Rostros</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in filteredPersons"
              :key="p.person_id"
              class="person-row"
              :class="{ 'person-row-selected': selectedPerson?.person_id === p.person_id }"
              @click="selectPerson(p)"
            >
              <td class="font-weight-medium">{{ p.nombre }}</td>
              <td>{{ p.apellido }}</td>
              <td>
                <span class="text-medium-emphasis">{{ p.email || '-' }}</span>
              </td>
              <td class="text-caption text-medium-emphasis">{{ new Date(p.created_at).toLocaleDateString() }}</td>
              <td class="text-center">
                <v-icon color="success" size="small">mdi-check-circle</v-icon>
              </td>
            </tr>
            <tr v-if="filteredPersons.length === 0">
              <td colspan="5" class="text-center pa-8">
                <v-icon size="48" color="grey" class="mb-2">mdi-account-off</v-icon>
                <p class="text-body-1 text-medium-emphasis">No se encontraron personas</p>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>
    </v-col>

    <v-col v-if="selectedPerson" cols="12">
      <v-card class="pa-5" color="primary" variant="tonal" border="start">
        <div class="d-flex align-center">
          <v-avatar color="primary" size="48" class="mr-4">
            <span class="text-h5 font-weight-bold text-white">
              {{ selectedPerson.nombre?.charAt(0) }}{{ selectedPerson.apellido?.charAt(0) }}
            </span>
          </v-avatar>
          <div class="flex-grow-1">
            <div class="text-h6 font-weight-bold">{{ selectedPerson.nombre }} {{ selectedPerson.apellido }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ selectedPerson.email || 'Sin email' }} &middot;
              ID: {{ selectedPerson.person_id }}
            </div>
          </div>
          <v-btn
            color="primary"
            class="text-none"
            elevation="3"
            @click="triggerFacesUpload"
          >
            <v-icon start>mdi-camera-plus</v-icon>
            Subir fotos faciales
          </v-btn>
          <input
            ref="facesInput"
            type="file"
            accept="image/*"
            multiple
            style="display: none"
            @change="onFacesSelected"
          />
        </div>
      </v-card>
    </v-col>
  </v-row>

  <v-dialog v-model="dialog" max-width="480" transition="dialog-top-transition">
    <v-card class="pa-5">
      <div class="d-flex align-center mb-4">
        <v-avatar color="primary" variant="tonal" size="36" class="mr-3">
          <v-icon>mdi-account-plus</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6 font-weight-bold">Nueva persona</div>
          <div class="text-caption text-medium-emphasis">Completa los datos para registrar una persona</div>
        </div>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="dialog = false" />
      </div>
      <PersonForm @submit="savePerson" @cancel="dialog = false" />
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPersons, createPerson } from '../services/api'
import PersonForm from '../components/PersonForm.vue'

const search = ref('')
const persons = ref([])
const dialog = ref(false)
const selectedPerson = ref(null)
const facesInput = ref(null)

const filteredPersons = computed(() => {
  if (!search.value) return persons.value
  const q = search.value.toLowerCase()
  return persons.value.filter(p =>
    p.nombre.toLowerCase().includes(q) ||
    p.apellido.toLowerCase().includes(q) ||
    p.email?.toLowerCase().includes(q)
  )
})

onMounted(async () => {
  try {
    const data = await getPersons()
    persons.value = data.persons || []
  } catch {
    persons.value = []
  }
})

function openNewDialog() {
  dialog.value = true
}

function selectPerson(p) {
  selectedPerson.value = selectedPerson.value?.person_id === p.person_id ? null : p
}

async function savePerson(personData) {
  try {
    const newPerson = await createPerson(personData)
    persons.value.unshift(newPerson)
    dialog.value = false
    selectedPerson.value = newPerson
  } catch (err) {
    console.error('Error al crear persona:', err)
  }
}

function triggerFacesUpload() {
  facesInput.value?.click()
}

function onFacesSelected(e) {
  const files = e.target.files
  if (files?.length) {
    console.log(`Subiendo ${files.length} foto(s) facial(es) para ${selectedPerson.value?.nombre}`)
  }
}
</script>

<style scoped>
.max-w-300 { max-width: 300px; }
.persons-table th {
  background: rgba(var(--v-theme-primary), 0.04);
}
.person-row {
  cursor: pointer;
  transition: background 0.15s;
}
.person-row:hover {
  background: rgba(var(--v-theme-primary), 0.03);
}
.person-row-selected {
  background: rgba(var(--v-theme-primary), 0.06) !important;
}
</style>
