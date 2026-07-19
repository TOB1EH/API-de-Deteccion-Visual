export const LOCAL_INFER_URL = 'http://localhost:8001'

export async function checkLocalServer() {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 3000)
    const res = await fetch(`${LOCAL_INFER_URL}/health`, { signal: controller.signal })
    clearTimeout(timeoutId)
    return res.ok
  } catch (err) {
    console.debug('[checkLocalServer] No se pudo conectar al servidor local:', err.message)
    return false
  }
}

export async function localFaceRecognize(imageBlob, threshold = 0.5) {
  const form = new FormData()
  form.append('image', imageBlob)
  form.append('threshold', String(threshold))
  const res = await fetch(`${LOCAL_INFER_URL}/face/recognize`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Face recognize error: ${res.status}`)
  return res.json()
}

export async function localFaceEmbed(personId, imageBlob, token) {
  const form = new FormData()
  form.append('person_id', personId)
  form.append('image', imageBlob)
  if (token) form.append('token', token)
  const res = await fetch(`${LOCAL_INFER_URL}/face/embed`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Face embed error: ${res.status}`)
  return res.json()
}

export async function localFaceDetect(imageBlob) {
  const form = new FormData()
  form.append('image', imageBlob)
  const res = await fetch(`${LOCAL_INFER_URL}/face/detect`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Face detect error: ${res.status}`)
  }
  return res.json()
}
