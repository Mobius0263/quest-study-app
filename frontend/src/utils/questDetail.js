import { parseDate } from './dates.js'
import { normalizeDifficulty, normalizeStatus } from './quests.js'

export function isQuestCompleted(quest) {
  return normalizeStatus(quest?.status) === 'done'
}

export function getQuestSteps(quest) {
  const steps = Array.isArray(quest?.steps) ? quest.steps : []
  return steps.filter((step) => step && step.id)
}

export function getCompletedStepIds(quest) {
  const progress = quest?.progress
  const ids = Array.isArray(progress)
    ? progress
    : progress?.completed_step_ids

  return Array.isArray(ids) ? ids.map(String) : []
}

export function getQuestDifficulty(quest) {
  return normalizeDifficulty(
    quest?.difficulty,
    quest?.reward_xp ?? quest?.xp ?? 50,
  )
}

export function getLinkedQuiz(quest) {
  return quest?.linked_quiz || null
}

export function isQuizPassed(quest) {
  return Boolean(getLinkedQuiz(quest)?.passed)
}

export function getQuizStepLabel(linkedQuiz) {
  const count = Number(linkedQuiz?.question_count) || 0
  const required = Number(linkedQuiz?.passes_required) || 0
  const questionLabel = count === 1 ? '1 question' : `${count} questions`
  if (!count) return 'Quest quiz'
  return `Quest quiz · ${questionLabel} · pass ${required} of ${count}`
}

export function getBestAttemptLabel(linkedQuiz) {
  const best = linkedQuiz?.best_attempt
  const count = Number(linkedQuiz?.question_count) || 0
  if (!best || !count) return ''
  const correct = Number(best.correct_count) || 0
  return `Best: ${correct} / ${count}`
}

export function getQuizQuestions(quiz) {
  const questions = quiz?.content?.questions
  return Array.isArray(questions) ? questions : []
}

/**
 * Split a deadline into the date itself plus a short, plain-language note.
 * The frontend never invents a deadline: null stays "No deadline".
 */
export function getDeadlineDisplay(value, reference = new Date()) {
  if (!value) return { date: 'No deadline', note: 'No deadline set' }

  const date = parseDate(value)
  if (!date) return { date: String(value), note: 'Deadline' }

  const targetDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const today = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate())
  const days = Math.round((targetDay - today) / 86400000)
  const formatted = new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() === reference.getFullYear() ? undefined : 'numeric',
  }).format(date)

  if (days === 0) return { date: formatted, note: 'Due today' }
  if (days === 1) return { date: formatted, note: 'Due tomorrow' }
  if (days > 1) return { date: formatted, note: `${days} days left` }
  if (days === -1) return { date: formatted, note: 'Overdue by 1 day' }
  return { date: formatted, note: `Overdue by ${Math.abs(days)} days` }
}

export function getLevelBar(levelInfo) {
  const totalXp = Number(levelInfo?.total_xp) || 0
  const xpToNext = Number(levelInfo?.xp_to_next_level) || 0
  return {
    totalXp,
    level: Number(levelInfo?.level) || 1,
    value: totalXp,
    max: Math.max(totalXp + xpToNext, 1),
  }
}
