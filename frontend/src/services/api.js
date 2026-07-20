import axios from 'axios'
import { authState, showAuthError } from './auth'

const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

const api = axios.create({
  baseURL: isLocalDev ? 'http://localhost:8000/api/' : 'https://bfts2026.mooo.com/api/',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  if (authState.token) {
    config.headers.Authorization = `Bearer ${authState.token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!authState.isDemoMode && !isLocalDev) {
      if (error.response?.status === 401 && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      if (error.response?.status === 403) {
        console.warn('[API] Acceso denegado (403):', error.config?.url)
        showAuthError('No tenes permisos para realizar esta accion.')
      }
    }
    return Promise.reject(error)
  }
)

export async function getModels() {
  const { data } = await api.get('/models')
  return data
}

export async function getModelDetail(modelName) {
  const { data } = await api.get(`/models/${encodeURIComponent(modelName)}`)
  return data
}

export async function postDetection({ image_base64, model_id, latitude, longitude, confidence, metadata }) {
  const { data } = await api.post('/detections', {
    image_base64, model_id, latitude, longitude, confidence, metadata
  })
  return {
    ...data,
    timestamp: new Date().toLocaleString()
  }
}

export async function getFrame(frameId) {
  const { data } = await api.get(`/frames/${frameId}/detail`)
  return data
}

export async function getFrameThumbnail(frameId) {
  const { data } = await api.get(`/frames/${frameId}`, {
    params: { thumbnail: true },
    responseType: 'blob'
  })
  return URL.createObjectURL(data)
}

export async function searchFrames({ clases, lat_min, lat_max, lon_min, lon_max, camera_id, source, limit, offset } = {}) {
  const params = {}
  if (clases) params.clases = clases
  if (lat_min !== undefined && lat_min !== '') params.lat_min = lat_min
  if (lat_max !== undefined && lat_max !== '') params.lat_max = lat_max
  if (lon_min !== undefined && lon_min !== '') params.lon_min = lon_min
  if (lon_max !== undefined && lon_max !== '') params.lon_max = lon_max
  if (camera_id) params.camera_id = camera_id
  if (source) params.source = source
  if (limit !== undefined) params.limit = limit
  if (offset !== undefined) params.offset = offset
  const { data } = await api.get('/frames/search', { params })
  return data
}

export async function getPerson(personId) {
  const { data } = await api.get(`/persons/${personId}`)
  return data
}

export async function updatePerson(personId, personData) {
  const { data } = await api.put(`/persons/${personId}`, personData)
  return data
}

export async function deletePerson(personId) {
  await api.delete(`/persons/${personId}`)
  return true
}

export async function getPersons() {
  const { data } = await api.get('/persons')
  return data
}

// GET /api/persons/me - Retorna la persona vinculada al token actual
export async function getMyPerson() {
  try {
    const { data } = await api.get('/persons/me')
    return data
  } catch {
    return null
  }
}

// POST /api/persons - Crea una nueva persona
export async function createPerson(personData) {
  const { data } = await api.post('/persons', personData)
  return data
}

export async function postFaceEmbed(personId, { image_base64, confidence }) {
  const { data } = await api.post(`/persons/${personId}/face-embed`, {
    image_base64, confidence
  })
  return data
}

export async function recognizeFaceFromImage(imageBase64, threshold = 0.8) {
  const { data } = await api.post('/face-recognition/image', {
    image_base64: imageBase64,
    threshold
  })
  return data
}

export function getFrameImageUrl(frameId, thumbnail = false) {
  const baseURL = isLocalDev
    ? 'http://localhost:8000/api/'
    : 'https://bfts2026.mooo.com/api/'
  const url = `${baseURL}frames/${frameId}`
  return thumbnail ? `${url}?thumbnail=true` : url
}

export { api }

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = () => reject(new Error('Error al leer la imagen'))
    reader.readAsDataURL(file)
  })
}