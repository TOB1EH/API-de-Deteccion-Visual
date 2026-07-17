<template>
  <v-chip :color="statusColor" variant="tonal" size="small" :loading="checking">
    <v-icon start :icon="statusIcon" size="16" />
    Nodo local: {{ statusText }}
  </v-chip>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { checkLocalServer } from '../services/inference'

const connected = ref(false)
const checking = ref(true)

const statusColor = computed(() => connected.value ? 'success' : 'error')
const statusText = computed(() => connected.value ? 'conectado' : 'desconectado')
const statusIcon = computed(() => connected.value ? 'mdi-check-circle' : 'mdi-alert-circle')

let intervalId = null

async function check() {
  checking.value = true
  connected.value = await checkLocalServer()
  checking.value = false
}

onMounted(() => {
  check()
  intervalId = setInterval(check, 15000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>
