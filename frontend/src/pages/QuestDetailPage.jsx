import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getQuest, updateQuest } from '../api/quests.js'
import { getProgress } from '../api/progress.js'
import { getApiErrorMessage } from '../api/errors.js'
import { useAuth } from '../context/AuthContext.js'
import { formatNumber } from '../utils/format.js'
import {
  getDeadlineDisplay,
  getLinkedQuiz,
  getQuestDifficulty,
  isQuestCompleted,
} from '../utils/questDetail.js'
import {
  CheckIcon,
  ChevronLeftIcon,
  ClockIcon,
  GemIcon,
  LockIcon,
  ZapIcon,
} from '../components/ui/icons.jsx'
import { ErrorState, LoadingState } from '../components/ui/StateViews.jsx'
import StatCard from '../components/ui/StatCard.jsx'
import GemRow from '../components/ui/GemRow.jsx'
import QuestDetailHeader from '../components/quests/QuestDetailHeader.jsx'
import QuestStepChecklist from '../components/quests/QuestStepChecklist.jsx'
import BossUnlockBanner from '../components/quests/BossUnlockBanner.jsx'

const INITIAL_QUEST = { status: 'loading', quest: null, error: '' }
const INITIAL_PROGRESS = { status: 'loading', data: null }

function getQuestLoadMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  if (error.response.status === 404) {
    return 'This quest could not be found. It may have been deleted.'
  }
  return "We couldn't load this quest. Please try again."
}

function getStepSaveMessage(error) {
  return getApiErrorMessage(
    error,
    "We couldn't save your progress. Please try again.",
  )
}

function getCompleteMessage(error) {
  return getApiErrorMessage(
    error,
    "We couldn't complete this quest. Nothing was changed — please try again.",
  )
}

export default function QuestDetailPage() {
  const { questId } = useParams()
  const location = useLocation()
  const { isStudent } = useAuth()
  const boardSearch = location.state?.boardSearch || ''

  const [questState, setQuestState] = useState(INITIAL_QUEST)
  const [progressState, setProgressState] = useState(INITIAL_PROGRESS)
  const [reloadKey, setReloadKey] = useState(0)
  const [savingSteps, setSavingSteps] = useState(false)
  const [stepError, setStepError] = useState('')
  const [completing, setCompleting] = useState(false)
  const [completeError, setCompleteError] = useState('')
  const [reward, setReward] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    setQuestState((current) => ({
      ...current,
      status: 'loading',
      error: '',
    }))

    getQuest(questId, { signal: controller.signal })
      .then((quest) => {
        if (cancelled) return
        setQuestState({ status: 'ready', quest, error: '' })
      })
      .catch((error) => {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setQuestState({
          status: 'error',
          quest: null,
          error: getQuestLoadMessage(error),
        })
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [questId, reloadKey])

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    setProgressState((current) => ({ ...current, status: 'loading' }))

    getProgress({ signal: controller.signal })
      .then((data) => {
        if (cancelled) return
        setProgressState({ status: 'ready', data })
      })
      .catch((error) => {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setProgressState({ status: 'error', data: null })
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [reloadKey])

  useEffect(() => {
    if (!reward) return undefined
    const timer = window.setTimeout(() => setReward(null), 1600)
    return () => window.clearTimeout(timer)
  }, [reward])

  async function handleToggleStep(stepId) {
    const quest = questState.quest
    if (!quest || savingSteps || isQuestCompleted(quest)) return

    const currentIds = Array.isArray(quest.progress?.completed_step_ids)
      ? quest.progress.completed_step_ids.map(String)
      : []
    const nextSet = new Set(currentIds)
    if (nextSet.has(String(stepId))) nextSet.delete(String(stepId))
    else nextSet.add(String(stepId))

    const nextIds = (quest.steps || [])
      .map((step) => String(step.id))
      .filter((id) => nextSet.has(id))
    const isUnstarted = quest.status === 'active' || quest.status === 'published'
    const nextStatus =
      isUnstarted && nextIds.length > 0
        ? 'in_progress'
        : (nextIds.length === 0 && quest.status === 'in_progress'
            ? (quest.status === 'published' ? 'published' : 'active')
            : quest.status)

    const previousQuest = quest
    setQuestState({
      status: 'ready',
      quest: {
        ...quest,
        progress: { completed_step_ids: nextIds },
        status: nextStatus,
      },
      error: '',
    })
    setSavingSteps(true)
    setStepError('')

    try {
      const saved = await updateQuest(quest.id, {
        progress: { completed_step_ids: nextIds },
        status: nextStatus,
      })
      setQuestState({ status: 'ready', quest: saved, error: '' })
    } catch (error) {
      setQuestState({ status: 'ready', quest: previousQuest, error: '' })
      setStepError(getStepSaveMessage(error))
    } finally {
      setSavingSteps(false)
    }
  }

  async function handleComplete() {
    const quest = questState.quest
    if (!quest || completing) return

    setCompleting(true)
    setCompleteError('')

    try {
      const confirmed = await updateQuest(quest.id, { status: 'completed' })
      const awardedXp = Number(confirmed.gamification?.awarded_xp) || quest.reward_xp
      const nextQuest = { ...confirmed }
      delete nextQuest.gamification
      delete nextQuest.current_streak
      delete nextQuest.completed_now

      setQuestState({ status: 'ready', quest: nextQuest, error: '' })
      setReward({ xp: awardedXp })

      try {
        const refreshed = await getProgress()
        setProgressState({ status: 'ready', data: refreshed })
      } catch {
        // The completion itself is confirmed; keep the previous XP bar.
      }
    } catch (error) {
      setCompleteError(getCompleteMessage(error))
    } finally {
      setCompleting(false)
    }
  }

  if (questState.status === 'loading') {
    return (
      <div className="screen-stack detail-screen">
        <div className="detail-topbar">
          <Link to={`/quests${boardSearch}`} className="btn-ghost">
            <ChevronLeftIcon size={16} />
            Back to board
          </Link>
          <span className="layout-note">Quest detail</span>
        </div>
        <div className="card">
          <LoadingState label="Loading this quest…" />
        </div>
      </div>
    )
  }

  if (questState.status === 'error' || !questState.quest) {
    return (
      <div className="screen-stack detail-screen">
        <div className="detail-topbar">
          <Link to={`/quests${boardSearch}`} className="btn-ghost">
            <ChevronLeftIcon size={16} />
            Back to board
          </Link>
          <span className="layout-note">Quest detail</span>
        </div>
        <div className="card">
          <ErrorState
            title="We couldn't open this quest"
            message={questState.error || 'Please try again in a moment.'}
            onRetry={() => setReloadKey((current) => current + 1)}
          />
        </div>
      </div>
    )
  }

  const quest = questState.quest
  const completed = isQuestCompleted(quest)
  const linkedQuiz = getLinkedQuiz(quest)
  const bossQuiz = quest.boss_quiz || null
  const quizPassed = Boolean(linkedQuiz?.passed)
  const canComplete = isStudent && !completed && (!linkedQuiz || quizPassed)
  const difficulty = getQuestDifficulty(quest)
  const deadline = getDeadlineDisplay(quest.due_date)
  const levelInfo = progressState.data?.level_info || null
  const description = String(quest.description || '').trim()
  const creatorName =
    [quest.creator_details?.first_name, quest.creator_details?.last_name]
      .filter(Boolean)
      .join(' ')
      .trim() ||
    quest.creator_details?.username ||
    ''
  const fallbackDescription = creatorName
    ? `Set by ${creatorName} for ${quest.subject}. Follow the study steps below and finish the quest.`
    : `A ${quest.quest_type === 'revision' ? 'revision' : 'study'} quest for ${quest.subject}. Follow the study steps below and finish the quest.`

  return (
    <div className="screen-stack detail-screen">
      <div className="detail-topbar">
        <Link to={`/quests${boardSearch}`} className="btn-ghost">
          <ChevronLeftIcon size={16} />
          Back to board
        </Link>
        <span className="layout-note">Quest detail</span>
      </div>

      <QuestDetailHeader quest={quest} levelInfo={levelInfo} reward={reward} />

      <section className="detail-tiles" aria-label="Quest facts">
        <StatCard
          icon={ZapIcon}
          label="XP reward"
          value={`${formatNumber(quest.reward_xp)} XP`}
          sub={completed ? 'Earned' : 'On completion'}
        />
        <StatCard
          icon={ClockIcon}
          label="Deadline"
          value={deadline.date}
          sub={deadline.note}
        />
        <StatCard
          icon={GemIcon}
          label="Difficulty"
          value={<GemRow difficulty={difficulty} />}
          sub={`${formatNumber(quest.reward_xp)} XP quest`}
        />
      </section>

      <section className="card detail-section" aria-labelledby="quest-brief-title">
        <div className="layout-note">Brief</div>
        <h2 id="quest-brief-title" className="detail-section-title">
          What to study
        </h2>
        <p className="detail-description">
          {description || fallbackDescription}
        </p>
      </section>

      <QuestStepChecklist
        quest={quest}
        isStudent={isStudent}
        saving={savingSteps}
        error={stepError}
        onToggleStep={handleToggleStep}
        boardSearch={boardSearch}
      />

      {isStudent && (
        <section className={`card detail-complete ${completed ? 'is-done' : ''}`.trim()}>
          {completed ? (
            <div className="completed-banner detail-done-banner">
              <CheckIcon size={18} />
              <span>Done · +{formatNumber(quest.reward_xp)} XP earned</span>
            </div>
          ) : (
            <>
              <button
                type="button"
                className="btn-primary btn-block detail-complete-btn"
                onClick={handleComplete}
                disabled={!canComplete || completing}
              >
                {completing
                  ? 'Completing…'
                  : `Complete Quest · +${formatNumber(quest.reward_xp)} XP`}
              </button>

              {linkedQuiz && !quizPassed && (
                <p className="detail-complete-note">
                  <LockIcon size={14} />
                  Pass the quest quiz to complete this quest.
                </p>
              )}

              {completeError && (
                <div className="detail-inline-error" role="alert">
                  <span>{completeError}</span>
                  <button
                    type="button"
                    className="detail-retry-link"
                    onClick={handleComplete}
                    disabled={completing}
                  >
                    Retry
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      )}

      <BossUnlockBanner quiz={bossQuiz} unlocked={completed} />
    </div>
  )
}
