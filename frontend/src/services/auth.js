// Servicio de autenticacion contra Keycloak via OAuth2 (direct grant)
// Usa el endpoint token de Keycloak con flujo password (directAccessGrants)
// El token JWT se almacena en localStorage y se usa en cada llamada a la API

import axios from 'axios'

const KEYCLOAK_URL = 'https://bfts2026.mooo.com/auth'
const REALM = 'api-detection'
const CLIENT_ID = 'api-backend'

// Intenta autenticar contra Keycloak con usuario y contrasena
// Retorna { username, roles, email } si es exitoso
// Lanza error si las credenciales son invalidas o Keycloak no responde
export async function loginWithKeycloak(username, password) {
  const params = new URLSearchParams()
  params.append('client_id', CLIENT_ID)
  params.append('username', username)
  params.append('password', password)
  params.append('grant_type', 'password')

  const { data } = await axios.post(
    `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`,
    params,
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      timeout: 10000
    }
  )

  // Guarda los tokens en localStorage
  localStorage.setItem('auth_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  localStorage.setItem('token_expires_at', String(Date.now() + data.expires_in * 1000))

  // Decodifica el JWT (parte del medio) para obtener datos del usuario
  const payload = JSON.parse(atob(data.access_token.split('.')[1]))

  return {
    token: data.access_token,
    username: payload.preferred_username || username,
    roles: payload.realm_roles || [],
    email: payload.email || ''
  }
}

// Refresca el token usando el refresh_token almacenado
export async function refreshToken() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return null

  try {
    const params = new URLSearchParams()
    params.append('client_id', CLIENT_ID)
    params.append('refresh_token', refresh)
    params.append('grant_type', 'refresh_token')

    const { data } = await axios.post(
      `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`,
      params,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        timeout: 10000
      }
    )

    localStorage.setItem('auth_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('token_expires_at', String(Date.now() + data.expires_in * 1000))

    return data.access_token
  } catch {
    // Si falla el refresh, limpia la sesion
    logout()
    return null
  }
}

// Cierra sesion: limpia tokens del localStorage
export function logout() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('token_expires_at')
  localStorage.removeItem('auth_user')
}

// Verifica si hay un token valido (no expirado)
export function isAuthenticated() {
  const token = localStorage.getItem('auth_token')
  if (!token) return false
  const expiresAt = parseInt(localStorage.getItem('token_expires_at') || '0')
  // Considera valido si falta mas de 30 seg para expirar
  return Date.now() < expiresAt - 30000
}

// Obtiene el token actual, lo refresca si es necesario
export async function getValidToken() {
  if (isAuthenticated()) {
    return localStorage.getItem('auth_token')
  }
  // Intenta refresh si expiro
  return await refreshToken()
}

// Devuelve el usuario almacenado o null
export function getStoredUser() {
  const stored = localStorage.getItem('auth_user')
  return stored ? JSON.parse(stored) : null
}

// Guarda los datos del usuario en localStorage
export function storeUser(user) {
  localStorage.setItem('auth_user', JSON.stringify(user))
}
