import api from './client.js'

export async function getModules(params = {}, config = {}) {
  const { data } = await api.get('/modules/', { params, ...config })
  return data
}

export async function getModule(id, config = {}) {
  const { data } = await api.get(`/modules/${id}/`, config)
  return data
}

export async function uploadModule(formData, config = {}) {
  const { data } = await api.post('/modules/', formData, {
    ...config,
    headers: {
      'Content-Type': 'multipart/form-data',
      ...(config.headers || {}),
    },
  })
  return data
}

export async function pasteModule(payload, config = {}) {
  const { data } = await api.post('/modules/', payload, config)
  return data
}

export async function processModule(id, payload, config = {}) {
  const { data } = await api.post(`/modules/${id}/process/`, payload, config)
  return data
}

export async function getModuleReview(id, config = {}) {
  const { data } = await api.get(`/modules/${id}/review/`, config)
  return data
}

export async function updateModuleQuestion(moduleId, questionId, payload, config = {}) {
  const { data } = await api.patch(
    `/modules/${moduleId}/questions/${questionId}/`,
    payload,
    config
  )
  return data
}

export async function regenerateModuleBatch(id, batchIndex, config = {}) {
  const { data } = await api.post(
    `/modules/${id}/batches/${batchIndex}/regenerate/`,
    {},
    config
  )
  return data
}

export async function publishModule(id, config = {}) {
  const { data } = await api.post(`/modules/${id}/publish/`, {}, config)
  return data
}

export async function deleteModule(id, config = {}) {
  const { data } = await api.delete(`/modules/${id}/`, config)
  return data
}


