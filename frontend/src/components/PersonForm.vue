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
      label="Email"
      type="email"
      prepend-inner-icon="mdi-email"
      :rules="[
        v => !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || 'Email invalido'
      ]"
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
  email: ''
})

watch(() => props.person, (val) => {
  if (val) {
    form.nombre = val.nombre || ''
    form.apellido = val.apellido || ''
    form.email = val.email || ''
  } else {
    form.nombre = ''
    form.apellido = ''
    form.email = ''
  }
}, { immediate: true })

function onSubmit() {
  emit('submit', { ...form })
}
</script>
