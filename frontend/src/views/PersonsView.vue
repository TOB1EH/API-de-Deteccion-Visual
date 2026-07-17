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
          <v-btn v-if="isAdmin()" color="primary" @click="openNewDialog" class="text-none" elevation="2">
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
              <td class="text-caption text-medium-emphasis">{{ new Date(p.created_at + 'Z').toLocaleDateString() }}</td>
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
          <div class="d-flex ga-2">
            <!-- Boton para ver detalle completo de la persona -->
            <v-btn
              variant="tonal"
              class="text-none"
              @click="goToPersonDetail(selectedPerson.person_id)"
            >
              <v-icon start>mdi-account-details</v-icon>
              Ver detalle
            </v-btn>
            <!-- Boton para editar datos de la persona (solo admin) -->
            <v-btn
              v-if="isAdmin()"
              color="warning"
              variant="tonal"
              class="text-none"
              @click="openEditDialog(selectedPerson)"
            >
              <v-icon start>mdi-pencil</v-icon>
              Editar
            </v-btn>
            <!-- Boton para eliminar persona con confirmacion (solo admin) -->
            <v-btn
              v-if="isAdmin()"
              color="error"
              variant="tonal"
              class="text-none"
              @click="confirmDelete(selectedPerson)"
            >
              <v-icon start>mdi-delete</v-icon>
              Eliminar
            </v-btn>
            <!-- Boton para subir fotos faciales (solo admin) -->
            <v-btn
              v-if="isAdmin()"
              color="primary"
              class="text-none"
              elevation="3"
              @click="triggerFacesUpload"
            >
              <v-icon start>mdi-camera-plus</v-icon>
              Subir fotos faciales
            </v-btn>
          </div>
          <input
            ref="facesInput"
            type="file"
            accept="image/*"
            multiple
            style="display: none"
            @change="onFacesSelected"
          />
        </div>
        <v-alert
          v-if="uploadMsg"
          :type="uploadError ? 'error' : 'success'"
          density="compact"
          variant="tonal"
          closable
          class="mt-3"
          @click:close="uploadMsg = ''"
        >
          <v-icon start>{{ uploadError ? 'mdi-alert' : 'mdi-check-circle' }}</v-icon>
          <span v-if="uploading">
            <v-progress-circular indeterminate size="16" width="2" class="mr-2" />
            {{ uploadMsg }}
          </span>
          <span v-else>{{ uploadMsg }}</span>
        </v-alert>
      </v-card>
    </v-col>
  </v-row>

  <!-- Dialogo para crear o editar persona -->
  <!-- Se reutiliza PersonForm; si editingPerson tiene datos, se pre-rellena el formulario -->
  <v-dialog v-model="dialog" max-width="480" transition="dialog-top-transition">
    <v-card class="pa-5">
      <div class="d-flex align-center mb-4">
        <v-avatar color="primary" variant="tonal" size="36" class="mr-3">
          <v-icon>{{ editingPerson ? 'mdi-pencil' : 'mdi-account-plus' }}</v-icon>
        </v-avatar>
        <div>
          <div class="text-h6 font-weight-bold">{{ editingPerson ? 'Editar persona' : 'Nueva persona' }}</div>
          <div class="text-caption text-medium-emphasis">{{ editingPerson ? 'Modifica los datos de la persona' : 'Completa los datos para registrar una persona' }}</div>
        </div>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="dialog = false" />
      </div>
      <!-- PersonForm recibe la persona a editar via prop; si es null, crea una nueva -->
      <PersonForm :person="editingPerson" @submit="editingPerson ? updatePersonData(editingPerson.person_id, $event) : savePerson($event)" @cancel="dialog = false" />
    </v-card>
  </v-dialog>

  <!-- Dialogo de confirmacion para eliminar persona -->
  <v-dialog v-model="deleteDialog" max-width="400" transition="dialog-top-transition">
    <v-card class="pa-5">
      <div class="text-center mb-4">
        <v-avatar color="error" size="56" class="mb-3">
          <v-icon size="28" color="white">mdi-alert</v-icon>
        </v-avatar>
        <div class="text-h6 font-weight-bold">Eliminar persona</div>
        <p class="text-body-2 text-medium-emphasis mt-2">
          ¿Estas seguro de eliminar a <strong>{{ deletingPerson?.nombre }} {{ deletingPerson?.apellido }}</strong>?
          <br>Se eliminaran tambien todos sus embeddings faciales asociados.
        </p>
      </div>
      <div class="d-flex ga-2 justify-end">
        <v-btn variant="tonal" @click="deleteDialog = false" class="text-none">Cancelar</v-btn>
        <v-btn color="error" @click="doDelete" :loading="deleting" class="text-none">
          <v-icon start>mdi-delete</v-icon>
          Eliminar
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPersons, createPerson, updatePerson, deletePerson, postFaceEmbed, fileToBase64 } from '../services/api'
import PersonForm from '../components/PersonForm.vue'
import { isAdmin, authState } from '../services/auth'
import { checkLocalServer, localFaceEmbed } from '../services/inference'

const router = useRouter()

const search = ref('')
const persons = ref([])
const dialog = ref(false)
const editingPerson = ref(null)
const selectedPerson = ref(null)
const facesInput = ref(null)
const uploading = ref(false)
const uploadMsg = ref('')
const uploadError = ref(false)
const hasLocalServer = ref(false)

// Estado del dialogo de eliminacion
const deleteDialog = ref(false)
const deletingPerson = ref(null)
const deleting = ref(false)

const filteredPersons = computed(() => {
  if (!search.value) return persons.value
  const q = search.value.toLowerCase()
  return persons.value.filter(p =>
    p.nombre.toLowerCase().includes(q) ||
    p.apellido.toLowerCase().includes(q) ||
    p.email?.toLowerCase().includes(q)
  )
})

// Abre el dialogo de edicion con los datos de la persona seleccionada
function openEditDialog(person) {
  editingPerson.value = { ...person }
  dialog.value = true
}

// Muestra el dialogo de confirmacion para eliminar una persona
function confirmDelete(person) {
  deletingPerson.value = person
  deleteDialog.value = true
}

// Actualiza los datos de una persona via API y refresca la lista
async function updatePersonData(personId, personData) {
  try {
    const updated = await updatePerson(personId, personData)
    const idx = persons.value.findIndex(p => p.person_id === personId)
    if (idx !== -1) {
      persons.value[idx] = updated
    }
    dialog.value = false
    editingPerson.value = null
    selectedPerson.value = updated
  } catch (err) {
    console.error('Error al actualizar persona:', err)
  }
}

// Ejecuta la eliminacion de la persona confirmada
async function doDelete() {
  if (!deletingPerson.value) return
  deleting.value = true
  try {
    await deletePerson(deletingPerson.value.person_id)
    persons.value = persons.value.filter(p => p.person_id !== deletingPerson.value.person_id)
    if (selectedPerson.value?.person_id === deletingPerson.value.person_id) {
      selectedPerson.value = null
    }
    deleteDialog.value = false
    deletingPerson.value = null
  } catch (err) {
    console.error('Error al eliminar persona:', err)
  } finally {
    deleting.value = false
  }
}

// Navega a la vista de detalle completo de la persona
function goToPersonDetail(personId) {
  router.push(`/persona/${personId}`)
}

onMounted(async () => {
  try {
    const data = await getPersons()
    persons.value = data.persons || []
  } catch {
    persons.value = []
  }
  hasLocalServer.value = await checkLocalServer()
})

function openNewDialog() {
  // Al crear una persona nueva, editingPerson debe ser null para que el
  // formulario se muestre vacio y el submit cree un registro nuevo
  editingPerson.value = null
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

async function onFacesSelected(e) {
  const files = e.target.files
  if (!files?.length || !selectedPerson.value) return

  uploading.value = true
  uploadMsg.value = `Subiendo ${files.length} foto(s)...`
  uploadError.value = false

  let successCount = 0
  let failCount = 0

  for (const file of files) {
    try {
      let result
      if (hasLocalServer.value) {
        result = await localFaceEmbed(selectedPerson.value.person_id, file, authState.token)
      } else {
        const image_base64 = await fileToBase64(file)
        result = await postFaceEmbed(selectedPerson.value.person_id, {
          image_base64,
          confidence: 0.8
        })
      }
      if (result.valid_embeddings > 0) {
        successCount++
      } else {
        failCount++
      }
    } catch {
      failCount++
    }
  }

  uploading.value = false
  if (failCount === 0) {
    uploadMsg.value = `${successCount} foto(s) procesada(s) correctamente`
    uploadError.value = false
  } else {
    uploadMsg.value = `${successCount} exitosa(s), ${failCount} fallida(s)`
    uploadError.value = true
  }

  // Limpiar el input para permitir reseleccionar el mismo archivo
  e.target.value = ''
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
