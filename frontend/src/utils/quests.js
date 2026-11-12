export const DIFFICULTY_META = {
  Easy: { gems: 1, xp: 20 },
  Medium: { gems: 2, xp: 50 },
  Hard: { gems: 3, xp: 100 },
}

export const DIFFICULTIES = Object.keys(DIFFICULTY_META)

export const STATUS_LABELS = {
  'not-started': 'Not started',
  'in-progress': 'In progress',
  done: 'Done',
}

export function normalizeDifficulty(value, xp) {
  if (value && DIFFICULTY_META[value]) return value
  if (xp >= DIFFICULTY_META.Hard.xp) return 'Hard'
  if (xp >= DIFFICULTY_META.Medium.xp) return 'Medium'
  return 'Easy'
}

export function normalizeStatus(status) {
  if (status === 'done' || status === 'completed') return 'done'
  if (status === 'in-progress' || status === 'in_progress') return 'in-progress'
  return 'not-started'
}

/**
 * The API uses quest_type/reward_xp, while the UI guide talks about
 * type/xp/difficulty. Keep that mapping in one place so every component
 * receives the same shape.
 */
export function normalizeQuest(raw = {}) {
  const xp = raw.reward_xp ?? raw.xp ?? DIFFICULTY_META.Medium.xp
  const difficulty = normalizeDifficulty(raw.difficulty, xp)
  const typeKey =
    raw.quest_type === 'revision' || raw.type === 'Revision'
      ? 'revision'
      : 'assignment'
  const stepProgress = raw.progress ?? raw.steps_completed ?? 0

  return {
    ...raw,
    id: raw.id,
    title: raw.title || 'Untitled quest',
    subject: raw.subject || 'Matematika',
    typeKey,
    typeLabel: typeKey === 'revision' ? 'Revision' : 'Assignment',
    difficulty,
    xp,
    dueDate: raw.due_date ?? raw.dueDate ?? null,
    status: normalizeStatus(raw.status),
    description: raw.description || '',
    steps: raw.steps || [],
    progress: stepProgress,
    quizStepIndex: raw.quiz_step_index ?? raw.quizStepIndex,
    linkedBoss: raw.linked_boss ?? raw.linkedBoss ?? false,
  }
}
