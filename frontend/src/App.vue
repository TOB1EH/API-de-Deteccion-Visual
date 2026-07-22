<template>
  <v-app theme="dark">
    <v-app-bar
      v-if="showAppBar"
      color="surface"
      elevation="0"
      class="border-b"
    >
      <v-app-bar-title class="font-weight-bold" @click="$router.push('/home')" style="cursor: pointer">
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

      <!-- Usuario logueado, rol y logout -->
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

      <LocalServerStatus class="mr-2" />
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

    <!-- Snackbar global para errores de autenticacion/permisos (401/403).
         Se activa desde el interceptor de api.js cuando el backend rechaza
         una peticion por falta de permisos. -->
    <v-snackbar
      v-model="authError.show"
      color="error"
      timeout="5000"
      location="top"
    >
      <v-icon start>mdi-shield-off</v-icon>
      {{ authError.message }}
      <template v-slot:actions>
        <v-btn variant="text" @click="authError.show = false">Cerrar</v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, authService, authError, hasAnyRole, isAdmin } from './services/auth'
import LocalServerStatus from './components/LocalServerStatus.vue'

const route = useRoute()
const router = useRouter()

const showAppBar = computed(() => route.name !== 'Login' && route.name !== 'Landing')

function doLogout() {
  authService.logout()
}

// Items de navegacion con roles requeridos (undefined = cualquier rol autenticado)
const allNavItems = [
  { to: '/home', icon: 'mdi-view-dashboard', label: 'Inicio' },
  { to: '/cargar', icon: 'mdi-cloud-upload', label: 'Cargar', roles: ['admin', 'operator'] },
  { to: '/buscar', icon: 'mdi-magnify', label: 'Buscar' },
  { to: '/personas', icon: 'mdi-account-group', label: 'Personas', roles: ['admin', 'operator'] },
  { to: '/facial', icon: 'mdi-face-recognition', label: 'Facial', roles: ['admin'] },
  { to: '/monitoreo', icon: 'mdi-monitor-dashboard', label: 'NOC', roles: ['admin', 'operator'] }
]

// Filtramos los items de navegacion segun los roles del usuario autenticado:
// Si el item requiere ciertos roles y el usuario no los tiene, se oculta.
const navItems = computed(() => {
  return allNavItems.filter(item => {
    if (!item.roles) return true
    return hasAnyRole(item.roles)
  })
})

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
