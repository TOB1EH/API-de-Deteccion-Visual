// Capa de servicios para comunicacion con la API backend
// Cambia USE_MOCKS a false cuando los endpoints reales esten disponibles

import axios from 'axios'
import {
  MOCK_MODELS,
  MOCK_FRAME_RESULT,
  MOCK_SEARCH_RESULTS,
  MOCK_PERSONS,
  MOCK_FRAME_DETAIL,
  MOCK_RECOGNITION,
  MOCK_RECOGNITION_FAIL
} from './mock'
import { getValidToken, logout } from './auth'

// Flag: true usa datos mock local, false hace llamadas HTTP reales
const USE_MOCKS = false

// Instancia de axios configurada con la URL base de la API
const api = axios.create({
  baseURL: 'https://bfts2026.mooo.com/api/',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor de request: agrega token JWT a cada llamada
api.interceptors.request.use(async (config) => {
  const token = await getValidToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor de response: si da 401, intenta refresh automatico
// Si el refresh falla, redirige al login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      logout()
      // Redirige al login si no estamos ya ahi
      if (window.location.hash !== '#/login') {
        window.location.hash = '#/login'
      }
    }
    return Promise.reject(error)
  }
)

// --- Modelos ---

// GET /api/models - Obtiene lista de modelos de deteccion disponibles
export async function getModels() {
  if (USE_MOCKS) {
    // Simula latencia de red
    await delay(300)
    return MOCK_MODELS
  }
  const { data } = await api.get('/models')
  return data
}

// --- Detecciones ---

// POST /api/detections - Envia una imagen para procesar con el modelo
export async function postDetection({ image_base64, model_id, latitude, longitude, confidence, metadata }) {
  if (USE_MOCKS) {
    await delay(1500)
    return {
      ...MOCK_FRAME_RESULT,
      timestamp: new Date().toISOString()
    }
  }
  const { data } = await api.post('/detections', {
    image_base64,
    model_id,
    latitude,
    longitude,
    confidence,
    metadata
  })
  return data
}

// --- Frames ---

// GET /api/frames/{frameId} - Obtiene detalle de un fotograma
export async function getFrame(frameId) {
  if (USE_MOCKS) {
    await delay(300)
    return {
      ...MOCK_FRAME_DETAIL,
      frame_id: frameId
    }
  }
  const { data } = await api.get(`/frames/${frameId}`)
  return data
}

// GET /api/frames/{frameId}?thumbnail=true - Obtiene miniatura de un fotograma (binario)
export async function getFrameThumbnail(frameId) {
  if (USE_MOCKS) {
    await delay(200)
    // Devuelve la misma URL de imagen mock
    return MOCK_FRAME_DETAIL.image_url
  }
  const { data } = await api.get(`/frames/${frameId}`, {
    params: { thumbnail: true },
    responseType: 'blob'
  })
  return URL.createObjectURL(data)
}

// GET /api/frames/search - Busca fotogramas con filtros
export async function searchFrames({ clases, lat_min, lat_max, lon_min, lon_max, limit, offset } = {}) {
  if (USE_MOCKS) {
    await delay(400)
    // Filtra del lado del cliente igual que SearchView
    let frames = [...MOCK_SEARCH_RESULTS.frames]

    if (clases) {
      const clasesBuscadas = clases.split(',').map(c => c.trim().toLowerCase()).filter(Boolean)
      if (clasesBuscadas.length > 0) {
        frames = frames.filter(frame =>
          frame.detections?.some(det =>
            clasesBuscadas.some(c => det.class_name.toLowerCase().includes(c))
          )
        )
      }
    }
    if (lat_min !== undefined && lat_min !== '') {
      frames = frames.filter(f => f.latitude >= parseFloat(lat_min))
    }
    if (lat_max !== undefined && lat_max !== '') {
      frames = frames.filter(f => f.latitude <= parseFloat(lat_max))
    }
    if (lon_min !== undefined && lon_min !== '') {
      frames = frames.filter(f => f.longitude >= parseFloat(lon_min))
    }
    if (lon_max !== undefined && lon_max !== '') {
      frames = frames.filter(f => f.longitude <= parseFloat(lon_max))
    }

    return { total: frames.length, frames }
  }
  const { data } = await api.get('/frames/search', {
    params: { clases, lat_min, lat_max, lon_min, lon_max, limit, offset }
  })
  return data
}

// --- Personas ---

// GET /api/persons - Obtiene lista de personas registradas
export async function getPersons() {
  if (USE_MOCKS) {
    await delay(300)
    return MOCK_PERSONS
  }
  const { data } = await api.get('/persons')
  return data
}

// POST /api/persons - Crea una nueva persona
export async function createPerson(personData) {
  if (USE_MOCKS) {
    await delay(500)
    return {
      person_id: `p-${Date.now()}`,
      ...personData,
      created_at: new Date().toISOString().split('T')[0],
      updated_at: new Date().toISOString().split('T')[0]
    }
  }
  const { data } = await api.post('/persons', personData)
  return data
}

// POST /api/persons/{personId}/embeddings - Sube fotos faciales para una persona
export async function postEmbeddings(personId, formData) {
  if (USE_MOCKS) {
    await delay(1000)
    return {
      person_id: personId,
      processed_images: 2,
      valid_embeddings: 1,
      rejected_images: 0
    }
  }
  const { data } = await api.post(`/persons/${personId}/embeddings`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
}

// --- Reconocimiento facial ---

// POST /api/face-recognition - Reconoce un rostro contra la base de datos
// La API espera un embedding (vector numerico), no una imagen cruda.
// El embedding debe calcularse primero via inference-server (/face/embed).
// Mientras el pipeline de embeddings no este conectado, se usa mock.
export async function recognizeFace({ image_base64, threshold }) {
  if (USE_MOCKS) {
    await delay(1500)
    const isMatch = Math.random() > 0.4
    if (isMatch) {
      return {
        ...MOCK_RECOGNITION,
        confidence: Math.min(threshold + Math.random() * 0.15, 0.99)
      }
    }
    return {
      ...MOCK_RECOGNITION_FAIL,
      confidence: Math.max(threshold - Math.random() * 0.3, 0.1)
    }
  }
  // Cuando el pipeline de embeddings este conectado, enviar:
  // const embedding = await computeEmbedding(image_base64)
  // const { data } = await api.post('/face-recognition', { embedding, threshold })
  throw new Error('Reconocimiento facial real no disponible. Usa modo mock.')
}

// Utilidad: delay para simular latencia de red
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// Convierte un File (imagen) a base64 para enviarlo a la API
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      // Extrae solo la parte base64 (saca el prefijo "data:image/...;base64,")
      const result = reader.result
      const base64 = result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = () => reject(new Error('Error al leer la imagen'))
    reader.readAsDataURL(file)
  })
}

export { USE_MOCKS }
