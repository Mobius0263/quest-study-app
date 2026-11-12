import { STATUS_LABELS } from './quests.js'
import { SUBJECT_NAMES } from './subjects.js'
import { isSameLocalDay, parseDate } from './dates.js'

export const TYPE_FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'assignment', label: 'Assignment' },
  { value: 'revision', label: 'Revision' },
]

export const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
]

export const STATUS_TO_API = {
  'not-started': 'active',
  'in-progress': 'in_progress',
  done: 'completed',
}

export function isDoneStatus(status) {
  return status === 'completed' || status === 'done'
}

export function isArchivedStatus(status) {
  return status === 'archived'
}

export function getBoardCounts(quests = [], reference) {
  const visible = quests.filter((quest) => quest && !isArchivedStatus(quest.status))
  const done = visible.filter((quest) => isDoneStatus(quest.status)).length
  const dueToday = visible.filter(
    (quest) =>
      !isDoneStatus(quest.status) && isSameLocalDay(quest.due_date, reference),
  ).length

  return { total: visible.length, done, dueToday }
}

function compareDueDates(first, second) {
  const firstDue = parseDate(first.due_date)?.getTime() ?? Number.POSITIVE_INFINITY
  const secondDue = parseDate(second.due_date)?.getTime() ?? Number.POSITIVE_INFINITY

  if (firstDue !== secondDue) return firstDue - secondDue
  return Number(first.id ?? 0) - Number(second.id ?? 0)
}

/**
 * Filters and ordering are deliberately separate: the API owns filtering, while
 * this helper only keeps the returned cards scannable. Done quests sink below
 * unfinished ones only for the unfiltered board.
 */
export function sortBoardQuests(quests = [], statusFilter = 'all') {
  const visible = quests
    .filter((quest) => quest && !isArchivedStatus(quest.status))
    .slice()
    .sort(compareDueDates)

  if (statusFilter !== 'all') return visible

  return [
    ...visible.filter((quest) => !isDoneStatus(quest.status)),
    ...visible.filter((quest) => isDoneStatus(quest.status)),
  ]
}

export function getBoardSubjectOptions(quests = [], selectedSubject = 'all') {
  const observed = []
  for (const quest of quests) {
    const subject = quest?.subject
    if (subject && !observed.includes(subject)) observed.push(subject)
  }

  const options = [...SUBJECT_NAMES]
  for (const subject of observed) {
    if (!options.includes(subject)) options.push(subject)
  }
  if (selectedSubject !== 'all' && !options.includes(selectedSubject)) {
    options.push(selectedSubject)
  }

  return options
}

export function buildQuestQueryParams({ type, subject, status }) {
  const params = {}
  if (type && type !== 'all') params.type = type
  if (subject && subject !== 'all') params.subject = subject
  if (status && status !== 'all') params.status = STATUS_TO_API[status]
  return params
}
