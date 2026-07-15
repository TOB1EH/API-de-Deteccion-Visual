// Servicio central de autenticacion con Keycloak (keycloak-js).
// Gestiona el estado de autenticacion global (authState), login OAuth2 con
// Keycloak, modo demo local y extraccion de roles/permisos desde el token JWT.
// El estado es reactivo (vue reactive) para que toda la app se entere cuando
// cambia la sesion. El init se ejecuta antes de montar la app (ver main.js).

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

// Estado global para mostrar alertas de error (ej: 403, permisos insuficientes)
export const authError = reactive({
  message: '',
  show: false,
})

// Muestra una alerta de error de autenticacion/autorizacion al usuario.
// Se conecta con el interceptor 403 de api.js y con App.vue para mostrar un snackbar.
export function showAuthError(msg) {
  authError.message = msg
  authError.show = true
  // Oculta automaticamente despues de 5 segundos
  setTimeout(() => {
    authError.show = false
    authError.message = ''
  }, 5000)
}

// ===== FUNCIONES AYUDANTES PARA VERIFICAR ROLES =====
// Los roles se extraen del token JWT de Keycloak (realm_access.roles).
// En modo demo, se asume operador para poder probar las funcionalidades basicas.

// Verifica si el usuario autenticado tiene el rol especificado.
// Retorna true si el usuario es admin, operator, o tiene el rol exacto.
export function hasRole(role) {
  // En modo demo, devolvemos true para roles no restrictivos
  if (authState.isDemoMode) return true
  if (!authState.authenticated || !authState.user) return false
  const roles = authState.user.roles || []
  return roles.includes(role)
}

// Verifica si el usuario tiene ALGUNO de los roles de la lista.
export function hasAnyRole(roles) {
  // En modo demo, devolvemos true
  if (authState.isDemoMode) return true
  if (!authState.authenticated || !authState.user) return false
  const userRoles = authState.user.roles || []
  return roles.some(role => userRoles.includes(role))
}

// Verifica si el usuario es admin (tiene el rol 'admin').
export function isAdmin() {
  return hasRole('admin')
}

// Verifica si el usuario puede escribir/editar datos en el sistema:
// admin siempre puede, operator puede escribir cierto tipo de datos.
export function canWrite() {
  return hasAnyRole(['admin', 'operator'])
}

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
       authState.loading = true
       const authenticated = await keycloak.init({
         onLoad: 'check-sso',
         // Desactiva el iframe de verificacion de 3rd-party cookies porque
         // Keycloak 26.x en localhost causa timeout. El login funciona igual
         // procesando el callback OAuth directamente desde la URL.
         checkLoginIframe: false
       })
       // Despues de que keycloak-js proceso la respuesta (codigo, token o error),
       // limpiamos cualquier hash residual que haya quedado en la URL para que
       // la vista se vea limpia (sin #error=login_required visible).
       if (window.location.hash && !window.location.hash.includes('code=') && !window.location.hash.includes('access_token=')) {
         history.replaceState(null, '', window.location.pathname)
       }
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
