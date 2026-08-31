const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readResponse(response) {
  if (response.ok) return response.json()
  let message = `Request failed with status ${response.status}.`
  try {
    const body = await response.json()
    message = body?.detail?.message || body?.detail || message
  } catch {
    // Keep the safe generic message when the server does not return JSON.
  }
  throw new ApiError(message, response.status)
}

async function request(path, options) {
  try {
    return await readResponse(await fetch(`${API_BASE_URL}${path}`, options))
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('The DepthWizard API is unavailable. Start the backend and try again.')
  }
}

export function startDemoPipeline(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/process', { method: 'POST', body: form })
}

export function getJob(jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}`)
}

export function getJobResult(jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}/result`)
}

export function artifactUrl(jobId, artifactName) {
  return `${API_BASE_URL}/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(artifactName)}`
}
