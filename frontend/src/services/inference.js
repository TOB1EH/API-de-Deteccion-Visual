const LOCAL_INFER_URL = 'http://localhost:8001'

export async function checkLocalServer() {
  try {
    const res = await fetch(`${LOCAL_INFER_URL}/health`, { signal: AbortSignal.timeout(3000) })
    return res.ok
  } catch {
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
