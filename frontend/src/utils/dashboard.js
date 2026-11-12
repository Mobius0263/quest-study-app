import { isSameLocalDay, parseDate } from './dates.js'

export function toList(value) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.results)) return value.results
  return []
}

export function isCompletedQuest(quest) {
  return quest?.status === 'completed' || quest?.status === 'done'
}

function isArchivedQuest(quest) {
  return quest?.status === 'archived'
}

export function getCompletedQuestIdsToday(progress, reference = new Date()) {
  const completedIds = new Set()
  const events = toList(progress?.recent_xp_events)

  for (const event of events) {
    if (event?.source_type !== 'quest_completion') continue
    if (!isSameLocalDay(event.created_at, reference)) continue

    const sourceId = String(event.source_id || '')
    const match = sourceId.match(/^quest_(\d+)$/) || sourceId.match(/^(\d+)$/)
    if (match) completedIds.add(match[1])
  }

  return completedIds
}

/**
 * Today's path keeps every active quest, plus quests completed today so they
 * stay in place until the day ends. The API has no completed_at field, so the
 * recent XP events are the source of truth for "completed today".
 */
export function getPathQuests(
  quests = [],
  completedTodayIds = new Set(),
  reference = new Date(),
) {
  return toList(quests)
    .filter((quest) => quest && !isArchivedQuest(quest))
    .filter((quest) => {
      if (!isCompletedQuest(quest)) return true
      return (
        completedTodayIds.has(String(quest.id)) ||
        isSameLocalDay(quest.due_date, reference)
      )
    })
    .sort((first, second) => {
      const firstDue = parseDate(first.due_date)?.getTime() ?? Number.POSITIVE_INFINITY
      const secondDue = parseDate(second.due_date)?.getTime() ?? Number.POSITIVE_INFINITY

      if (firstDue !== secondDue) return firstDue - secondDue
      return Number(first.id ?? 0) - Number(second.id ?? 0)
    })
}

/**
 * The backend stores no daily-goal field. Use quests due today as the goal,
 * with quests completed today as the progress, so both values stay driven by
 * API data instead of a hardcoded sample target.
 */
export function getDailyGoal(quests, completedTodayIds = new Set(), reference = new Date()) {
  const todayQuests = toList(quests).filter(
    (quest) => quest && !isArchivedQuest(quest) && isSameLocalDay(quest.due_date, reference),
  )
  const dueToday = todayQuests.length
  const done = completedTodayIds?.size ?? 0
  const target = Math.max(dueToday, done)

  return {
    done,
    target,
    dueToday,
    percent: target > 0 ? Math.round((done / target) * 100) : 0,
  }
}

export function getNextBossQuiz(quizzes = [], pathQuests = []) {
  const quizList = toList(quizzes).filter(
    (quiz) => quiz && quiz.id != null && quiz.kind === 'boss',
  )
  if (quizList.length === 0) return null

  for (const quest of toList(pathQuests)) {
    if (isCompletedQuest(quest)) continue
    const linkedQuiz = quizList.find(
      (quiz) => quiz.quest != null && String(quiz.quest) === String(quest.id),
    )
    if (linkedQuiz) return linkedQuiz
  }

  return quizList[0]
}

export function getQuizQuestionCount(quiz) {
  const questions = quiz?.content?.questions
  return Array.isArray(questions) && questions.length > 0 ? questions.length : null
}

export function formatQuizDuration(seconds) {
  const totalSeconds = Number(seconds)
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) return 'Timed exam'

  if (totalSeconds >= 3600) {
    const hours = Math.floor(totalSeconds / 3600)
    const minutes = Math.round((totalSeconds % 3600) / 60)
    if (minutes > 0) return `${hours}h ${minutes}m`
    return `${hours} hour${hours === 1 ? '' : 's'}`
  }

  const minutes = Math.max(1, Math.round(totalSeconds / 60))
  return `${minutes} min`
}
