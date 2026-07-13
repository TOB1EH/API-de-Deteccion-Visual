// Servicio central de autenticacion con Keycloak (keycloak-js)

import Keycloak from 'keycloak-js'
import { reactive } from 'vue'

// Estado reactivo global
export const authState = reactive({
  authenticated: false,
  isDemoMode: false,
  token: null,
  user: null,
  loading: true
})

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

// En local usa proxy de Vite (mismo origen, sin CORS en token exchange)
const keycloakConfig = isLocalDev
  ? { url: window.location.origin + '/auth', realm: 'api-detection', clientId: 'api-backend' }
  : { url: 'https://bfts2026.mooo.com/auth', realm: 'api-detection', clientId: 'api-backend' }

const keycloak = new Keycloak(keycloakConfig)

function extractUserFromToken(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return {
      username: payload.preferred_username || payload.sub,
      email: payload.email || null,
      firstName: payload.given_name || payload.preferred_username,
      lastName: payload.family_name || '',
      roles: payload.realm_access?.roles || []
    }
  } catch {
    return { username: 'unknown', roles: [] }
  }
}

export const authService = {
  async init() {
    try {
      // Limpiar solo hash viejos que NO contengan un codigo OAuth activo
      if (window.location.hash && !window.location.hash.includes('code=') && !window.location.hash.includes('access_token=')) {
        history.replaceState(null, '', window.location.pathname)
      }
      authState.loading = true
      const authenticated = await keycloak.init({
        onLoad: 'check-sso',
        // Desactiva el iframe de verificacion de 3rd-party cookies porque
        // Keycloak 26.x en localhost causa timeout. El login funciona igual
        // procesando el callback OAuth directamente desde la URL.
        checkLoginIframe: false
      })
      console.log('[Keycloak] init result - authenticated:', authenticated)
      if (authenticated) {
        authState.token = keycloak.token
        authState.user = extractUserFromToken(keycloak.token)
        console.log('[Keycloak] user from token:', authState.user)
      }
      authState.authenticated = authenticated
      authState.loading = false
      console.log('[Keycloak] authState after init:', { ...authState, token: authState.token?.substring(0, 20) + '...' })
    } catch (err) {
      console.error('[Keycloak] Error critico en init:', err)
      authState.loading = false
      authState.authenticated = false
    }
  },

  login() {
    keycloak.login({ redirectUri: window.location.origin + '/home' })
  },

  enableDemoMode() {
    authState.authenticated = true
    authState.isDemoMode = true
    authState.token = 'mock-token-desarrollador'
    authState.user = { firstName: 'Developer', lastName: 'Demo' }
  },

  logout() {
    const wasDemo = authState.isDemoMode
    authState.authenticated = false
    authState.isDemoMode = false
    authState.token = null
    authState.user = null
    if (!wasDemo) {
      keycloak.logout({ redirectUri: window.location.origin + '/login' })
    }
  }
}
