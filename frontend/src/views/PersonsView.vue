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
      <v-alert v-if="errorMsg" type="error" variant="tonal" closable class="mb-4" @click:close="errorMsg = ''">
        {{ errorMsg }}
      </v-alert>
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
          <v-avatar color="primary" size="56" class="mr-4" @click="triggerProfileUpload">
            <v-img
              v-if="selectedPerson.profile_image_url"
              :src="selectedPerson.profile_image_url"
              class="cursor-pointer"
              style="cursor: pointer;"
            />
            <span v-else class="text-h5 font-weight-bold text-white cursor-pointer">
              {{ selectedPerson.nombre?.charAt(0) }}{{ selectedPerson.apellido?.charAt(0) }}
            </span>
            <v-icon
              v-if="isAdmin()"
              class="profile-overlay"
              size="20"
              color="white"
            >mdi-camera</v-icon>
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
          <input
            ref="profileInput"
            type="file"
            accept="image/*"
            style="display: none"
            @change="onProfileSelected"
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

  <!-- Dialogo de password temporal para el usuario creado -->
  <v-dialog v-model="tempPasswordDialog" max-width="480" transition="dialog-top-transition">
    <v-card class="pa-6 text-center">
      <v-avatar color="success" size="56" class="mb-3">
        <v-icon size="28" color="white">mdi-key</v-icon>
      </v-avatar>
      <div class="text-h6 font-weight-bold mb-1">Usuario creado exitosamente</div>
      <p class="text-body-2 text-medium-emphasis mb-4">
        Comparte esta contrasena temporal con el usuario. Podra cambiarla al iniciar sesion.
      </p>
      <v-sheet color="grey-darken-4" rounded="lg" class="pa-4 mb-4 mx-auto" max-width="360">
        <div class="text-caption text-medium-emphasis mb-1">Email</div>
        <div class="text-body-1 font-weight-bold text-success">{{ tempPasswordEmail }}</div>
        <v-divider class="my-3" />
        <div class="text-caption text-medium-emphasis mb-1">Contrasena temporal</div>
        <div class="d-flex align-center justify-center ga-2">
          <code class="text-h6 font-weight-bold text-cyan-accent-3" style="font-size: 1.1rem; letter-spacing: 1px;">{{ tempPasswordValue }}</code>
          <v-btn icon="mdi-content-copy" size="small" variant="tonal" color="cyan-accent-3" @click="copyTempPassword" />
        </div>
      </v-sheet>
      <v-btn color="primary" @click="tempPasswordDialog = false" class="text-none">
        Entendido
      </v-btn>
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
const profileInput = ref(null)
const uploading = ref(false)
const uploadMsg = ref('')
const uploadError = ref(false)
const hasLocalServer = ref(false)

// Estado del dialogo de eliminacion
const deleteDialog = ref(false)
const deletingPerson = ref(null)
const deleting = ref(false)

// Estado del dialogo de password temporal
const tempPasswordDialog = ref(false)
const tempPasswordValue = ref('')
const tempPasswordEmail = ref('')
const errorMsg = ref('')

function copyTempPassword() {
  navigator.clipboard.writeText(tempPasswordValue.value)
}

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
    const { password, ...cleanData } = personData
  if (!cleanData.role) delete cleanData.role
    const updated = await updatePerson(personId, cleanData)
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
  errorMsg.value = ''
  try {
    const newPerson = await createPerson(personData)
    persons.value.unshift(newPerson)
    dialog.value = false
    selectedPerson.value = newPerson
    if (newPerson.temporary_password) {
      tempPasswordValue.value = newPerson.temporary_password
      tempPasswordEmail.value = newPerson.email || ''
      tempPasswordDialog.value = true
    }
  } catch (err) {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    if (status === 409) {
      errorMsg.value = detail || 'El email ya esta registrado en Keycloak'
    } else {
      errorMsg.value = detail || err.message || 'Error al crear persona'
    }
  }
}

function triggerFacesUpload() {
  facesInput.value?.click()
}

function triggerProfileUpload() {
  if (!isAdmin()) return
  profileInput.value?.click()
}

async function onProfileSelected(e) {
  const file = e.target.files?.[0]
  if (!file || !selectedPerson.value) return

  uploading.value = true
  uploadMsg.value = 'Subiendo foto de perfil...'
  uploadError.value = false

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
      uploadMsg.value = 'Foto de perfil establecida correctamente'
      uploadError.value = false
      const updated = await getPersons()
      const found = updated.persons?.find(p => p.person_id === selectedPerson.value.person_id)
      if (found) {
        selectedPerson.value = found
        const idx = persons.value.findIndex(p => p.person_id === found.person_id)
        if (idx !== -1) persons.value[idx] = found
      }
    } else {
      uploadMsg.value = 'No se pudo procesar la imagen'
      uploadError.value = true
    }
  } catch {
    uploadMsg.value = 'Error al subir foto de perfil'
    uploadError.value = true
  }

  uploading.value = false
  e.target.value = ''
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
.v-avatar {
  position: relative;
}
.profile-overlay {
  position: absolute;
  bottom: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  padding: 4px;
}
.cursor-pointer {
  cursor: pointer;
}
</style>
