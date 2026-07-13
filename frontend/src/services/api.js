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

// GET /api/models/{modelName} - Obtiene detalle de un modelo especifico
// Se usa para ver informacion detallada de un modelo (tamano, tipo, ruta)
export async function getModelDetail(modelName) {
  return withFallback(
    async () => {
      const { data } = await api.get(`/models/${encodeURIComponent(modelName)}`)
      return data
    },
    async () => {
      await delay(300)
      const mockModel = MOCK_MODELS.models.find(m => m.name === modelName)
      return mockModel || { name: modelName, size: 0, type: 'yolo', path: `models/local/${modelName}` }
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
// Soporta filtros por clases, ubicacion (lat/lon), camera_id, source,
// mas parametros de paginacion (limit/offset)
// Solo envia parametros con valor para evitar que FastAPI reciba strings
// vacios que fallarian al parsear como float (ver Tarea 0.4)
export async function searchFrames({ clases, lat_min, lat_max, lon_min, lon_max, camera_id, source, limit, offset } = {}) {
  return withFallback(
    async () => {
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
      if (camera_id) {
        frames = frames.filter(f => f.metadata?.camera_id === camera_id)
      }
      if (source) {
        frames = frames.filter(f => f.metadata?.source === source)
      }
      return { total: frames.length, frames }
    }
  )
}

// --- Personas ---

// GET /api/persons/{personId} - Obtiene detalle de una persona por su ID
// Se usa en la vista de detalle de persona
export async function getPerson(personId) {
  return withFallback(
    async () => {
      const { data } = await api.get(`/persons/${personId}`)
      return data
    },
    async () => {
      await delay(300)
      const mockPerson = MOCK_PERSONS.persons.find(p => p.person_id === personId)
      return mockPerson || { person_id: personId, nombre: 'N/A', apellido: '', email: '', created_at: '', updated_at: '' }
    }
  )
}

// PUT /api/persons/{personId} - Actualiza los datos de una persona
// Retorna la persona actualizada
export async function updatePerson(personId, personData) {
  return withFallback(
    async () => {
      const { data } = await api.put(`/persons/${personId}`, personData)
      return data
    },
    async () => {
      await delay(500)
      return { person_id: personId, ...personData, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }
    }
  )
}

// DELETE /api/persons/{personId} - Elimina una persona
// Retorna true si se elimino correctamente
export async function deletePerson(personId) {
  return withFallback(
    async () => {
      await api.delete(`/persons/${personId}`)
      return true
    },
    async () => {
      await delay(400)
      return true
    }
  )
}

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

// POST /api/persons/{personId}/face-embed - Sube foto facial y genera embedding
// Envia imagen en base64, la API la envia al inference-server (DeepFace)
// y persiste embedding + imagen en BD + SeaweedFS
export async function postFaceEmbed(personId, { image_base64, confidence }) {
  return withFallback(
    async () => {
      const { data } = await api.post(`/persons/${personId}/face-embed`, {
        image_base64, confidence
      })
      return data
    },
    async () => {
      await delay(1500)
      return { person_id: personId, valid_embeddings: 1, embedding_id: `mock-${Date.now()}`, image_url: '' }
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

// Construye la URL para obtener la imagen de un frame desde el backend.
// Si thumbnail=true, el backend redimensiona la imagen a 300px.
// Esto es necesario porque el thumbnail solo funciona a traves del endpoint
// de la API (GET /api/frames/{frameId}?thumbnail=true), no desde SeaweedFS directo.
export function getFrameImageUrl(frameId, thumbnail = false) {
  const baseURL = isLocalDev
    ? 'http://localhost:8000/api/'
    : 'https://bfts2026.mooo.com/api/'
  const url = `${baseURL}frames/${frameId}`
  return thumbnail ? `${url}?thumbnail=true` : url
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
