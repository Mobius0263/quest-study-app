import api from './client.js'

export async function getQuests(params = {}, config = {}) {
  const { data } = await api.get('/quests/', { ...config, params })
  return data
}

export async function getQuest(id, config = {}) {
  const { data } = await api.get(`/quests/${id}/`, config)
  return data
}

export async function createQuest(payload, config = {}) {
  const { data } = await api.post('/quests/', payload, config)
  return data
}

export async function updateQuest(id, payload, config = {}) {
  const { data } = await api.patch(`/quests/${id}/`, payload, config)
  return data
}

export async function deleteQuest(id, config = {}) {
  await api.delete(`/quests/${id}/`, config)
}

export async function publishQuest(id, config = {}) {
  const { data } = await api.post(`/quests/${id}/publish/`, {}, config)
  return data
}

export async function regenerateQuest(id, payload = {}, config = {}) {
  const { data } = await api.post(`/quests/${id}/regenerate/`, payload, config)
  return data
}
