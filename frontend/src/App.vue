<template>
  <v-app :theme="theme">
    <v-app-bar
      v-if="showAppBar"
      color="surface"
      elevation="0"
      class="border-b"
    >
      <v-app-bar-title class="font-weight-bold">
        <v-icon class="mr-2" color="primary">mdi-cctv</v-icon>
        <span class="text-primary">API</span>
        <span class="text-medium-emphasis"> Deteccion Visual</span>
      </v-app-bar-title>

      <v-spacer />

      <v-btn
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        :variant="isActive(item.to) ? 'tonal' : 'text'"
        class="text-none mx-1"
        :class="{ 'font-weight-medium': isActive(item.to) }"
        color="primary"
        size="small"
      >
        <v-icon start size="20">{{ item.icon }}</v-icon>
        {{ item.label }}
      </v-btn>

      <v-divider vertical class="mx-2" />

      <v-btn
        :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
        variant="text"
        size="small"
        @click="toggleTheme"
      />
    </v-app-bar>

    <v-main>
      <v-container fluid class="pa-0" style="min-height: calc(100vh - 64px);">
        <router-view v-slot="{ Component, route }">
          <v-fade-transition hide-on-leave>
            <keep-alive>
              <component :is="Component" :key="route.name" />
            </keep-alive>
          </v-fade-transition>
        </router-view>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const showAppBar = computed(() => route.name !== 'Login')

const stored = localStorage.getItem('theme')
const isDark = ref(stored !== 'light')
const theme = computed(() => isDark.value ? 'dark' : 'light')

watch(isDark, (val) => {
  localStorage.setItem('theme', val ? 'dark' : 'light')
})

function toggleTheme() {
  isDark.value = !isDark.value
}

const navItems = [
  { to: '/cargar', icon: 'mdi-cloud-upload', label: 'Cargar' },
  { to: '/buscar', icon: 'mdi-magnify', label: 'Buscar' },
  { to: '/personas', icon: 'mdi-account-group', label: 'Personas' },
  { to: '/facial', icon: 'mdi-face-recognition', label: 'Facial' }
]

function isActive(to) {
  return route.path.startsWith(to)
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* { font-family: 'Inter', sans-serif; }

html {
  overflow-y: auto;
  scroll-behavior: smooth;
}

.v-application {
  font-family: 'Inter', sans-serif !important;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(100, 100, 100, 0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(100, 100, 100, 0.5); }
</style>
