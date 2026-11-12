import api from './client.js'

export async function getQuizzes(params = {}, config = {}) {
  const { data } = await api.get('/quizzes/', { ...config, params })
  return data
}

export async function getQuiz(id, config = {}) {
  const { data } = await api.get(`/quizzes/${id}/`, config)
  return data
}

export async function generateQuiz(payload, config = {}) {
  const { data } = await api.post('/ai/generate-quiz/', payload, config)
  return data
}

export async function updateQuiz(id, payload, config = {}) {
  const { data } = await api.patch(`/quizzes/${id}/`, payload, config)
  return data
}

export async function deleteQuiz(id, config = {}) {
  await api.delete(`/quizzes/${id}/`, config)
}

export async function checkQuizAnswer(id, payload, config = {}) {
  const { data } = await api.post(`/quizzes/${id}/check-answer/`, payload, config)
  return data
}

export async function submitQuizAttempt(id, payload, config = {}) {
  const { data } = await api.post(`/quizzes/${id}/attempts/`, payload, config)
  return data
}

export async function startBossAttempt(id, payload = {}, config = {}) {
  const { data } = await api.post(`/quizzes/${id}/boss/start/`, payload, config)
  return data
}

export async function getBossAttempt(id, attemptId, config = {}) {
  const { data } = await api.get(`/quizzes/${id}/boss/${attemptId}/`, config)
  return data
}

export async function answerBossQuestion(id, attemptId, payload, config = {}) {
  const { data } = await api.post(
    `/quizzes/${id}/boss/${attemptId}/answer/`,
    payload,
    config,
  )
  return data
}

export async function timeoutBossAttempt(id, attemptId, config = {}) {
  const { data } = await api.post(
    `/quizzes/${id}/boss/${attemptId}/timeout/`,
    {},
    config,
  )
  return data
}

export async function publishQuiz(id, config = {}) {
  const { data } = await api.post(`/quizzes/${id}/publish/`, {}, config)
  return data
}

export async function regenerateQuiz(id, payload = {}, config = {}) {
  const { data } = await api.post(`/quizzes/${id}/regenerate/`, payload, config)
  return data
}
