import api from './client.js'

export async function getProgress(config = {}) {
  const { data } = await api.get('/progress/me/', config)
  return data
}

export async function getTeacherProgress(config = {}) {
  const { data } = await api.get('/progress/', config)
  return data
}
