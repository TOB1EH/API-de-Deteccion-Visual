// Servicio central de autenticacion con Keycloak (keycloak-js).
// Gestiona el estado de autenticacion global (authState), login OAuth2 con
// Keycloak, modo demo local y extraccion de roles/permisos desde el token JWT.
// El estado es reactivo (vue reactive) para que toda la app se entere cuando
// cambia la sesion. El init se ejecuta antes de montar la app (ver main.js).

import Keycloak from 'keycloak-js'
import { reactive } from 'vue'
import axios from 'axios'

// Estado reactivo global
export const authState = reactive({
  authenticated: false,
  isDemoMode: false,
  token: null,
  user: null,
  loading: true,
  faceVerified: false  // Se pone true despues de pasar la verificacion facial 2FA
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
    const roles = payload.realm_access?.roles || []
    console.log('[Auth Debug] extractUserFromToken roles:', roles, 'username:', payload.preferred_username)
    return {
      username: payload.preferred_username || payload.sub,
      email: payload.email || null,
      firstName: payload.given_name || payload.preferred_username,
      lastName: payload.family_name || '',
      roles: roles,
    }
  } catch {
    console.warn('[Auth Debug] extractUserFromToken: error decodificando token')
    return { username: 'unknown', roles: [] }
  }
}

async function createPersonIfMissing(token, user) {
  const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  const baseURL = isLocalDev ? 'http://localhost:8000/api/' : 'https://bfts2026.mooo.com/api/'

  try {
    const resp = await axios.get(`${baseURL}persons/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (resp.data?.person_id) {
      console.log('[Auth] Persona ya vinculada:', resp.data.person_id)
      return
    }
  } catch (err) {
    if (err.response?.status !== 404) {
      console.warn('[Auth] Error al verificar persona:', err.message)
      return
    }
  }

  try {
    const nombre = user.firstName || user.username?.split('@')[0] || 'Usuario'
    const apellido = user.lastName || ''
    const email = user.email || ''
    console.log('[Auth] Creando persona automatica:', nombre, apellido)
    await axios.post(
      `${baseURL}persons/me`,
      { nombre, apellido, email },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    console.log('[Auth] Persona creada exitosamente')
  } catch (err) {
    console.warn('[Auth] No se pudo crear persona:', err.response?.data?.detail || err.message)
  }
}

export const authService = {
  async init() {
     try {
       authState.loading = true
       if (window.location.hash && !window.location.hash.includes('code=') && !window.location.hash.includes('access_token=')) {
         history.replaceState(null, '', window.location.pathname)
       }
       const initOptions = isLocalDev
         ? {}
         : {
             onLoad: 'check-sso',
             checkLoginIframe: false,
             silentCheckSsoFallback: true,
             silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html'
           }
       const authenticated = await keycloak.init(initOptions)
      console.log('[Keycloak] init result - authenticated:', authenticated)
      if (authenticated) {
        authState.token = keycloak.token
        authState.user = extractUserFromToken(keycloak.token)
        authState.authenticated = true
        authState.loading = false
        console.log('[Keycloak] user from token:', authState.user)
        console.log('[Auth Debug] Keycloak hasOperator:', authState.user.roles.includes('operator'))
        console.log('[Auth Debug] Keycloak hasAnyRole admin/operator:', authState.user.roles.includes('admin') || authState.user.roles.includes('operator'))
        if (!authState.user.roles.includes('operator')) {
          console.warn('[Auth Debug] ATENCION: Token Keycloak NO tiene rol operator!')
          try {
            const full = JSON.parse(atob(keycloak.token.split('.')[1]))
            console.log('[Auth Debug] Token completo realm_access:', JSON.stringify(full.realm_access))
          } catch(e) {}
        }
        if (localStorage.getItem('facial_token')) {
          console.log('[Auth Debug] Limpiando facial_token obsoleto')
          localStorage.removeItem('facial_token')
        }
        createPersonIfMissing(keycloak.token, authState.user)
        return
      }
    } catch (err) {
      console.error('[Keycloak] init fallo, revisando token facial:', err.message)
    }
    const storedToken = localStorage.getItem('facial_token')
    if (storedToken) {
      console.log('[Auth Debug] Usando facial_token de localStorage')
      try {
        const payload = JSON.parse(atob(storedToken.split('.')[1]))
        if (payload.exp * 1000 > Date.now()) {
          const expiresIn = payload.exp * 1000 - Date.now()
          if (expiresIn < 5 * 60 * 1000 && expiresIn > 0) {
            console.log('[Auth Debug] facial_token por expirar, redirigiendo a login facial para refrescar')
            localStorage.removeItem('facial_token')
            authState.authenticated = false
            authState.loading = false
            window.location.href = '/login-facial'
            return
          }
          authState.token = storedToken
          authState.user = extractUserFromToken(storedToken)
          authState.authenticated = true
          authState.loading = false
          console.log('[Auth Debug] facial_token roles:', authState.user.roles)
          console.log('[Auth Debug] facial_token hasOperator:', authState.user.roles.includes('operator'))
          return
        }
        console.log('[Auth Debug] facial_token expirado, eliminando')
        localStorage.removeItem('facial_token')
      } catch {
        localStorage.removeItem('facial_token')
      }
    }
    authState.authenticated = false
    authState.loading = false
  },

  login() {
    keycloak.login({ redirectUri: window.location.origin + '/home' })
  },

  // Inicia sesion con un Identity Provider externo (Google, GitHub, etc.)
  // keycloak.login({ idpHint: 'google' }) redirige directamente al IdP
  // saltando el formulario de login de Keycloak.
  loginWithIdp(idpAlias) {
    keycloak.login({ redirectUri: window.location.origin + '/home', idpHint: idpAlias })
  },

  setToken(token) {
    localStorage.setItem('facial_token', token)
    authState.token = token
    authState.user = extractUserFromToken(token)
    authState.authenticated = true
    authState.isDemoMode = false
    authState.loading = false
  },

  enableDemoMode() {
    authState.authenticated = true
    authState.isDemoMode = true
    authState.token = 'mock-token-desarrollador'
    authState.user = { firstName: 'Developer', lastName: 'Demo' }
  },

  logout() {
    const wasDemo = authState.isDemoMode
    const wasFacial = !!localStorage.getItem('facial_token')
    authState.authenticated = false
    authState.isDemoMode = false
    authState.token = null
    authState.user = null
    localStorage.removeItem('facial_token')
    if (wasFacial) {
      window.location.href = '/login'
      return
    }
    if (!wasDemo) {
      keycloak.logout({ redirectUri: window.location.origin + '/login' })
    }
  }
}
