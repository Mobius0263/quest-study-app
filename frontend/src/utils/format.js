export function formatNumber(value) {
  return new Intl.NumberFormat('en-US').format(Number(value) || 0)
}

export function getInitials(value) {
  if (!value) return '?'
  const parts = String(value).trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

export function getDisplayName(user) {
  if (!user) return 'Student'
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim()
  return fullName || user.username || 'Student'
}

export function formatDueDate(value) {
  if (!value) return 'No deadline'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)

  const today = new Date()
  const targetDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const todayDay = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const days = Math.round((targetDay - todayDay) / 86400000)

  const formatted = new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  }).format(date)

  if (days === 0) return `Due ${formatted} · Due today`
  if (days < 0) return `Due ${formatted} · Overdue ${Math.abs(days)}d`
  return `Due ${formatted}`
}
