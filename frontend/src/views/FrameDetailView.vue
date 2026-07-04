<template>
  <v-row class="pa-6" align="center" justify="center">
    <v-col cols="12" class="text-center">
      <v-icon size="64" color="primary" class="mb-4">mdi-image</v-icon>
      <h2 class="text-h4 font-weight-bold">Detalle de fotograma</h2>
      <p class="text-body-1 text-medium-emphasis mt-2">Vista en construccion</p>
    </v-col>
  </v-row>
</template>

<script setup>
defineProps({ id: String })
</script>
