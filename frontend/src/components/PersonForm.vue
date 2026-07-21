<template>
  <v-form @submit.prevent="onSubmit">
    <v-text-field
      v-model="form.nombre"
      label="Nombre *"
      :rules="[v => !!v || 'El nombre es obligatorio']"
      prepend-inner-icon="mdi-account"
      required
      class="mb-3"
    />
    <v-text-field
      v-model="form.apellido"
      label="Apellido *"
      :rules="[v => !!v || 'El apellido es obligatorio']"
      prepend-inner-icon="mdi-account"
      required
      class="mb-3"
    />
    <v-text-field
      v-model="form.email"
      label="Email *"
      type="email"
      prepend-inner-icon="mdi-email"
      :rules="[
        v => !!v || 'El email es obligatorio',
        v => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || 'Email invalido'
      ]"
      hint="Se creara un usuario en Keycloak con este email"
      required
      class="mb-4"
    />
    <v-select
      v-if="person"
      v-model="form.role"
      label="Rol"
      :items="[
        { title: 'Operador', value: 'operator' },
        { title: 'Visitante', value: 'viewer' }
      ]"
      prepend-inner-icon="mdi-shield-account"
      hint="Define los permisos del usuario"
      persistent-hint
      class="mb-4"
    />
    <div class="d-flex ga-2 justify-end">
      <v-btn variant="tonal" @click="$emit('cancel')" class="text-none">
        Cancelar
      </v-btn>
      <v-btn color="primary" type="submit" class="text-none" elevation="2">
        <v-icon start>mdi-check</v-icon>
        Guardar
      </v-btn>
    </div>
  </v-form>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  person: { type: Object, default: null }
})

const emit = defineEmits(['submit', 'cancel'])

const form = reactive({
  nombre: '',
  apellido: '',
  email: '',
  role: null,
})

watch(() => props.person, (val) => {
  if (val) {
    form.nombre = val.nombre || ''
    form.apellido = val.apellido || ''
    form.email = val.email || ''
    form.role = val.role || null
  } else {
    form.nombre = ''
    form.apellido = ''
    form.email = ''
    form.role = null
  }
}, { immediate: true })

function onSubmit() {
  emit('submit', { ...form })
}
</script>
