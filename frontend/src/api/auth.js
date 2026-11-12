import api from './client.js'

export async function loginRequest(credentials) {
  const { data } = await api.post('/auth/login/', credentials)
  return data
}

export async function registerRequest(payload) {
  const { data } = await api.post('/auth/register/', payload)
  return data
}

export async function meRequest() {
  const { data } = await api.get('/auth/me/')
  return data
}
