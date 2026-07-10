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

      <!-- Usuario logueado y logout -->
      <template v-if="authState.authenticated && authState.user">
        <v-chip size="small" variant="tonal" color="primary" class="mr-2">
          <v-icon start size="14">mdi-account-circle</v-icon>
          {{ authState.user.username || authState.user.firstName }}
        </v-chip>
        <v-btn
          icon="mdi-logout"
          variant="text"
          size="small"
          @click="doLogout"
          class="mr-2"
        />
      </template>

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
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <div :key="$route.fullPath">
              <component :is="Component" />
            </div>
          </transition>
        </router-view>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, authService } from './services/auth'

const route = useRoute()
const router = useRouter()

const showAppBar = computed(() => route.name !== 'Login')

function doLogout() {
  authService.logout()
}

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
  { to: '/home', icon: 'mdi-view-dashboard', label: 'Inicio' },
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

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
