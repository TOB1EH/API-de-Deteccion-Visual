// Servicio central de autenticacion con Keycloak (keycloak-js)
// keycloak.js maneja el flujo OAuth2 completo (redirect, tokens, refresh)

import Keycloak from 'keycloak-js'
import { reactive } from 'vue'

// Estado reactivo global accesible desde cualquier componente o guard
export const authState = reactive({
  authenticated: false,
  token: null,
  user: null,
  loading: true
})

// Configuracion del cliente Keycloak
const keycloak = new Keycloak({
  url: 'https://bfts2026.mooo.com/auth',
  realm: 'detections-realm',
  clientId: 'frontend-client'
})

async function handleInit(authenticated) {
  if (authenticated) {
    authState.token = keycloak.token
    try {
      const profile = await keycloak.loadUserProfile()
      authState.user = {
        username: profile.username,
        email: profile.email,
        firstName: profile.firstName,
        lastName: profile.lastName,
        roles: keycloak.realmAccess?.roles || []
      }
    } catch {
      authState.user = { username: 'unknown', roles: [] }
    }
  }
  authState.authenticated = authenticated
  authState.loading = false
}

export const authService = {
  // Inicializa Keycloak en segundo plano (check-sso, sin redirect inmediato)
  async init() {
    try {
      authState.loading = true
      const authenticated = await keycloak.init({
        onLoad: 'check-sso',
        checkLoginIframe: false
      })
      await handleInit(authenticated)
    } catch {
      // Keycloak no disponible: modo offline, se puede acceder via demo
      authState.loading = false
      authState.authenticated = false
    }
  },

  // Redirige al usuario al formulario de login de Keycloak
  login() {
    keycloak.login({ redirectUri: window.location.origin + '/cargar' })
  },

  // Cierra sesion y redirige al login
  logout() {
    authState.authenticated = false
    authState.token = null
    authState.user = null
    keycloak.logout({ redirectUri: window.location.origin + '/login' })
  }
}
