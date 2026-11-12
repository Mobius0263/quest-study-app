export function parseDate(value) {
  if (!value) return null
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }

  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    const localDate = new Date(year, month - 1, day)
    return Number.isNaN(localDate.getTime()) ? null : localDate
  }

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function isSameLocalDay(value, reference = new Date()) {
  const date = parseDate(value)
  if (!date) return false

  return (
    date.getFullYear() === reference.getFullYear() &&
    date.getMonth() === reference.getMonth() &&
    date.getDate() === reference.getDate()
  )
}

function pad(value) {
  return String(value).padStart(2, '0')
}

export function toDateInputValue(value) {
  if (!value) return ''
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value
  }

  const date = parseDate(value)
  if (!date) return ''
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function deadlineInputToIso(value) {
  if (!value) return null
  const date = new Date(`${value}T23:59:59.999`)
  return Number.isNaN(date.getTime()) ? null : date.toISOString()
}

export function isDeadlineInputInPast(value, reference = new Date()) {
  if (!value) return false
  const date = new Date(`${value}T23:59:59.999`)
  if (Number.isNaN(date.getTime())) return true
  return date.getTime() < reference.getTime()
}
