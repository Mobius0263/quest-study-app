const FALLBACK_MESSAGE = 'Something went wrong. Please try again.'

/**
 * Turns a DRF error response into one short, human-readable message.
 * Validation responses look like { field: ["message"] } or { detail: "..." }.
 */
export function getApiErrorMessage(error, fallback = FALLBACK_MESSAGE) {
  if (!error?.response) {
    return error?.message && error.message !== 'Network Error'
      ? error.message
      : 'Cannot reach the server. Check that the backend is running and try again.'
  }

  const data = error.response.data

  if (typeof data === 'string') return data
  if (data?.detail) return data.detail
  if (data?.error) return data.error
  if (data?.message) return data.message

  if (data && typeof data === 'object') {
    const firstValue = Object.values(data).flat()[0]
    if (typeof firstValue === 'string') return firstValue
  }

  return fallback
}
