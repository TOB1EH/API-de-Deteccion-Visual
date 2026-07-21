export const LOCAL_INFER_URL = 'http://localhost:8001'

export async function checkLocalServer() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 3000)
  try {
    await fetch(`${LOCAL_INFER_URL}/health`, {
      mode: 'no-cors',
      signal: controller.signal
    })
    clearTimeout(timeoutId)
    return true
  } catch (err) {
    clearTimeout(timeoutId)
    return false
  }
}

export async function localFaceRecognize(imageBlob, threshold = 0.5) {
  const form = new FormData()
  form.append('image', imageBlob)
  form.append('threshold', String(threshold))
  const res = await fetch(`${LOCAL_INFER_URL}/face/recognize`, { method: 'POST', body: form })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = body.detail || ''
    } catch {}
    throw new Error(`Face recognize error: ${res.status}${detail ? ` - ${detail}` : ''}`)
  }
  return res.json()
}

export async function localFaceEmbed(personId, imageBlob, token) {
  const form = new FormData()
  form.append('person_id', personId)
  form.append('image', imageBlob)
  if (token) form.append('token', token)
  const res = await fetch(`${LOCAL_INFER_URL}/face/embed`, { method: 'POST', body: form })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = body.detail || ''
    } catch {}
    throw new Error(`Face embed error: ${res.status}${detail ? ` - ${detail}` : ''}`)
  }
  return res.json()
}
