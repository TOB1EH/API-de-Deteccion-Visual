// Capa de servicios para comunicacion con la API backend.
// Cada funcion intenta llamar a la API real primero.
// Si la API no responde (servidor caido, error de red), usa datos mock como fallback.
// Asi el frontend funciona siempre, con o sin conexion al servidor remoto.

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
import { authState } from './auth'

// En local (npm run dev) apunta a la API local en puerto 8000
// En produccion apunta al servidor remoto via Nginx
const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

const api = axios.create({
  baseURL: isLocalDev ? 'http://localhost:8000/api/' : 'https://bfts2026.mooo.com/api/',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor de request: agrega token JWT de Keycloak a cada llamada
api.interceptors.request.use((config) => {
  if (authState.token) {
    config.headers.Authorization = `Bearer ${authState.token}`
  }
  return config
})

// Interceptor de response: si da 401, redirige al login SOLO en produccion
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !authState.isDemoMode && !isLocalDev) {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Intenta llamar a la API real, si falla ejecuta el fallback mock
async function withFallback(apiCall, mockFn) {
  try {
    const result = await apiCall()
    return result
  } catch {
    // Si hay error de red o servidor caido, usa datos mock
    return mockFn()
  }
}

// --- Modelos ---

// GET /api/models - Lista modelos de deteccion disponibles
export async function getModels() {
  return withFallback(
    async () => {
      const { data } = await api.get('/models')
      return data
    },
    async () => {
      await delay(300)
      return MOCK_MODELS
    }
  )
}

// --- Detecciones ---

// POST /api/detections - Envia una imagen para procesar
export async function postDetection({ image_base64, model_id, latitude, longitude, confidence, metadata }) {
  return withFallback(
    async () => {
      const { data } = await api.post('/detections', {
        image_base64, model_id, latitude, longitude, confidence, metadata
      })
      return {
        ...data,
        timestamp: new Date().toLocaleString()
      }
    },
    async () => {
      await delay(1500)
      return {
        ...MOCK_FRAME_RESULT,
        timestamp: new Date().toLocaleString()
      }
    }
  )
}

// --- Frames ---

// GET /api/frames/{frameId}/detail - Detalle de un fotograma (JSON con metadatos + detecciones)
// El endpoint /api/frames/{id} devuelve la imagen binaria, no JSON. Por eso existe /detail.
export async function getFrame(frameId) {
  return withFallback(
    async () => {
      const { data } = await api.get(`/frames/${frameId}/detail`)
      return data
    },
    async () => {
      await delay(300)
      return { ...MOCK_FRAME_DETAIL, frame_id: frameId }
    }
  )
}

// GET /api/frames/{frameId}?thumbnail=true - Miniatura de un fotograma
export async function getFrameThumbnail(frameId) {
  return withFallback(
    async () => {
      const { data } = await api.get(`/frames/${frameId}`, {
        params: { thumbnail: true },
        responseType: 'blob'
      })
      return URL.createObjectURL(data)
    },
    async () => {
      await delay(200)
      return MOCK_FRAME_DETAIL.image_url
    }
  )
}

// GET /api/frames/search - Busca fotogramas con filtros
export async function searchFrames({ clases, lat_min, lat_max, lon_min, lon_max, limit, offset } = {}) {
  return withFallback(
    async () => {
      const { data } = await api.get('/frames/search', {
        params: { clases, lat_min, lat_max, lon_min, lon_max, limit, offset }
      })
      return data
    },
    async () => {
      await delay(400)
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
  )
}

// --- Personas ---

// GET /api/persons - Lista personas registradas
export async function getPersons() {
  return withFallback(
    async () => {
      const { data } = await api.get('/persons')
      return data
    },
    async () => {
      await delay(300)
      return MOCK_PERSONS
    }
  )
}

// POST /api/persons - Crea una nueva persona
export async function createPerson(personData) {
  return withFallback(
    async () => {
      const { data } = await api.post('/persons', personData)
      return data
    },
    async () => {
      await delay(500)
      return {
        person_id: `p-${Date.now()}`,
        ...personData,
        created_at: new Date().toISOString().split('T')[0],
        updated_at: new Date().toISOString().split('T')[0]
      }
    }
  )
}

// POST /api/persons/{personId}/embeddings - Sube fotos faciales
export async function postEmbeddings(personId, formData) {
  return withFallback(
    async () => {
      const { data } = await api.post(`/persons/${personId}/embeddings`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      return data
    },
    async () => {
      await delay(1000)
      return { person_id: personId, processed_images: 2, valid_embeddings: 1, rejected_images: 0 }
    }
  )
}

// --- Reconocimiento facial ---

// POST /api/face-recognition - Reconoce un rostro
// La API real espera un embedding (vector), no imagen. Mientras el pipeline
// de embeddings no este integrado, siempre usa mock.
export async function recognizeFace({ image_base64, threshold }) {
  await delay(1500)
  const isMatch = Math.random() > 0.4
  if (isMatch) {
    return { ...MOCK_RECOGNITION, confidence: Math.min(threshold + Math.random() * 0.15, 0.99) }
  }
  return { ...MOCK_RECOGNITION_FAIL, confidence: Math.max(threshold - Math.random() * 0.3, 0.1) }
}

// --- Utilidades ---

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// Convierte un File (imagen) a base64 (sin prefijo data:image/...)
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
