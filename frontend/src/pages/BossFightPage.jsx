import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  answerBossQuestion,
  startBossAttempt,
  timeoutBossAttempt,
} from '../api/quizzes.js'
import { getApiErrorMessage } from '../api/errors.js'
import { ChevronLeftIcon } from '../components/ui/icons.jsx'
import { ErrorState, LoadingState } from '../components/ui/StateViews.jsx'
import BossArena from '../components/boss/BossArena.jsx'
import BossFightHeader from '../components/boss/BossFightHeader.jsx'
import BossHpBars from '../components/boss/BossHpBars.jsx'
import BossQuestionCard from '../components/boss/BossQuestionCard.jsx'
import BossResultPanel from '../components/boss/BossResultPanel.jsx'

const INITIAL_PAGE = { status: 'loading', error: '' }

function getBossLoadMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  if (error.response.status === 404) {
    return 'This boss exam could not be found. It may have been deleted.'
  }
  return getApiErrorMessage(
    error,
    "We couldn't open this boss exam. Please try again.",
  )
}

function BackLink({ to }) {
  return (
    <Link to={to} className="btn-ghost">
      <ChevronLeftIcon size={16} />
      Back to quest
    </Link>
  )
}

export default function BossFightPage() {
  const { quizId } = useParams()
  const [page, setPage] = useState(INITIAL_PAGE)
  const [reloadKey, setReloadKey] = useState(0)
  const [attempt, setAttempt] = useState(null)
  const [result, setResult] = useState(null)
  const [selected, setSelected] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState('')
  const [timeLeft, setTimeLeft] = useState(null)
  const [damage, setDamage] = useState(null)
  const [hitKey, setHitKey] = useState(0)
  const [retrying, setRetrying] = useState(false)
  const [retryError, setRetryError] = useState('')

  const timeoutRef = useRef(false)
  const resultTimerRef = useRef(null)

  const applyAttempt = useCallback((data) => {
    if (resultTimerRef.current) {
      window.clearTimeout(resultTimerRef.current)
      resultTimerRef.current = null
    }
    timeoutRef.current = false
    setAttempt(data)
    setSelected('')
    setFeedback(null)
    setCheckError('')
    setDamage(null)
    setRetryError('')

    const finished = data?.status && data.status !== 'in_progress'
    if (finished && data.result) {
      setResult(data.result)
      const limit = Number(data.time_limit_seconds) || 3600
      const taken = Number(data.result.time_taken_seconds) || 0
      setTimeLeft(Math.max(0, limit - taken))
    } else {
      setResult(null)
      setTimeLeft(
        Math.max(
          0,
          Number(data?.time_remaining_seconds) ||
            Number(data?.time_limit_seconds) ||
            0,
        ),
      )
    }
    setPage({ status: 'ready', error: '' })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    setPage(INITIAL_PAGE)
    setAttempt(null)
    setResult(null)
    setFeedback(null)
    setSelected('')
    setCheckError('')
    setTimeLeft(null)
    setDamage(null)
    setRetryError('')

    startBossAttempt(quizId, { retry: false }, { signal: controller.signal })
      .then((data) => {
        if (!cancelled) applyAttempt(data)
      })
      .catch((error) => {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setPage({ status: 'error', error: getBossLoadMessage(error) })
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [quizId, reloadKey, applyAttempt])

  const activeAttemptId = attempt?.attempt_id
  const activeStatus = attempt?.status

  useEffect(() => {
    if (page.status !== 'ready' || result || !activeAttemptId) return undefined
    if (activeStatus !== 'in_progress') return undefined

    const timer = window.setInterval(() => {
      setTimeLeft((current) =>
        current == null ? current : Math.max(0, current - 1),
      )
    }, 1000)
    return () => window.clearInterval(timer)
  }, [page.status, result, activeAttemptId, activeStatus])

  useEffect(() => {
    if (page.status !== 'ready' || result || !attempt) return undefined
    if (attempt.status !== 'in_progress' || timeLeft !== 0) return undefined
    if (timeoutRef.current) return undefined

    timeoutRef.current = true
    let cancelled = false

    async function expire() {
      try {
        const data = await timeoutBossAttempt(quizId, attempt.attempt_id)
        if (!cancelled) applyAttempt(data)
      } catch (error) {
        if (cancelled) return
        const state = error?.response?.data?.state
        if (state) {
          applyAttempt(state)
          return
        }
        if (error?.response?.status === 400) {
          // The server clock can trail the local countdown by a moment.
          timeoutRef.current = false
          setTimeLeft(1)
          return
        }
        timeoutRef.current = false
        setCheckError(
          getApiErrorMessage(
            error,
            'The timer ended, but we could not close the attempt. Please refresh.',
          ),
        )
      }
    }

    expire()
    return () => {
      cancelled = true
    }
  }, [page.status, result, attempt, timeLeft, quizId, applyAttempt])

  useEffect(() => {
    if (!damage) return undefined
    const timer = window.setTimeout(() => setDamage(null), 1000)
    return () => window.clearTimeout(timer)
  }, [damage])

  useEffect(
    () => () => {
      if (resultTimerRef.current) {
        window.clearTimeout(resultTimerRef.current)
      }
    },
    [],
  )

  async function handleCheck() {
    const question = attempt?.question
    if (!question || !selected || checking || feedback || result) return

    setChecking(true)
    setCheckError('')

    try {
      const data = await answerBossQuestion(quizId, attempt.attempt_id, {
        question_id: question.id,
        answer: selected,
      })

      setFeedback(data)

      if (Number(data.damage) > 0) {
        setHitKey((current) => current + 1)
        setDamage({
          key: Date.now(),
          text: `-${Number(data.damage)} DAMAGE`,
        })
      }

      setAttempt((current) => {
        if (!current) return current
        const prevXp = current.xp || {}
        const finished = Boolean(data.finished && data.result)
        let xp = data.result?.xp
        if (!finished) {
          const perAnswer =
            (Number(prevXp.per_answer) || 0) + (data.correct ? 5 : 0)
          const streakBonus =
            (Number(prevXp.streak_bonus) || 0) +
            (Number(data.streak_bonus) || 0)
          xp = {
            per_answer: perAnswer,
            streak_bonus: streakBonus,
            win_bonus: 0,
            total: perAnswer + streakBonus,
          }
        }

        return {
          ...current,
          status: finished ? data.result.status : current.status,
          passed: finished ? data.result.passed : current.passed,
          failure_reason: finished
            ? data.result.failure_reason
            : current.failure_reason,
          boss_hp: data.boss_hp,
          player_hp: data.player_hp,
          current_streak: data.current_streak,
          correct_count: finished
            ? data.result.correct_count
            : (Number(current.correct_count) || 0) + (data.correct ? 1 : 0),
          answered_count: data.answered_count,
          xp,
          xp_earned: finished ? data.result.xp_earned : xp?.total || 0,
        }
      })

      if (data.finished && data.result) {
        const finishedResult = data.result
        const limit = Number(attempt.time_limit_seconds) || 3600
        resultTimerRef.current = window.setTimeout(() => {
          setResult(finishedResult)
          setTimeLeft(
            Math.max(
              0,
              limit - (Number(finishedResult.time_taken_seconds) || 0),
            ),
          )
        }, 700)
      }
    } catch (error) {
      const state = error?.response?.data?.state
      if (state) {
        applyAttempt(state)
        return
      }
      setCheckError(
        getApiErrorMessage(
          error,
          "We couldn't check that answer. Please try again.",
        ),
      )
    } finally {
      setChecking(false)
    }
  }

  function handleNext() {
    if (!feedback) return
    const nextQuestion = feedback.next_question
    if (nextQuestion) {
      setAttempt((current) =>
        current
          ? {
              ...current,
              question: nextQuestion,
              question_number: nextQuestion.number,
              question_index: nextQuestion.index,
            }
          : current,
      )
    }
    setSelected('')
    setFeedback(null)
    setCheckError('')
  }

  async function handleRetry() {
    if (retrying) return
    setRetrying(true)
    setRetryError('')
    try {
      const data = await startBossAttempt(quizId, { retry: true })
      applyAttempt(data)
    } catch (error) {
      setRetryError(
        getApiErrorMessage(
          error,
          "We couldn't start a retry. Please try again.",
        ),
      )
    } finally {
      setRetrying(false)
    }
  }

  const questId = attempt?.quiz?.quest_id
  const backTo = questId ? `/quests/${questId}` : '/quests'

  if (page.status === 'loading') {
    return (
      <div className="screen-stack boss-screen">
        <div className="detail-topbar">
          <BackLink to={backTo} />
          <span className="layout-note">Boss exam</span>
        </div>
        <div className="card">
          <LoadingState label="Preparing the boss arena…" />
        </div>
      </div>
    )
  }

  if (page.status === 'error') {
    return (
      <div className="screen-stack boss-screen">
        <div className="detail-topbar">
          <BackLink to={backTo} />
          <span className="layout-note">Boss exam</span>
        </div>
        <div className="card">
          <ErrorState
            title="We couldn't open this boss exam"
            message={page.error}
            onRetry={() => setReloadKey((current) => current + 1)}
          />
        </div>
      </div>
    )
  }

  if (!attempt) return null

  const bossName = attempt.quiz?.boss_name || attempt.quiz?.title || 'The Boss'
  const total = Number(attempt.total_questions) || 20
  const unanswered = !result && !attempt.question
  const headerAttempt = result
    ? {
        ...attempt,
        question_number: Math.max(1, Number(result.answered_count) || 1),
        attempt_number: result.attempt_number || attempt.attempt_number,
        attempts_total: result.attempts_total || attempt.attempts_total,
        retries_left: result.retries_left,
      }
    : attempt

  return (
    <div className="screen-stack boss-screen">
      <div className="detail-topbar">
        <BackLink to={backTo} />
        <span className="layout-note">Boss exam</span>
      </div>

      <BossArena
        bossName={bossName}
        quote={attempt.quiz?.quote}
        defeated={result?.status === 'won'}
        hitKey={hitKey}
        damage={damage}
      />

      <BossFightHeader
        quiz={attempt.quiz}
        attempt={headerAttempt}
        timeLeft={timeLeft}
      />

      <BossHpBars
        bossHp={result ? result.boss_hp : attempt.boss_hp}
        bossHpMax={result ? result.boss_hp_max : attempt.boss_hp_max}
        playerHp={result ? result.player_hp : attempt.player_hp}
        playerHpMax={result ? result.player_hp_max : attempt.player_hp_max}
        streak={attempt.current_streak}
        xpEarned={result ? result.xp_earned : attempt.xp_earned}
      />

      {unanswered ? (
        <div className="card">
          <ErrorState
            title="No question is available"
            message="The arena has no current question. Reload the exam to continue."
            onRetry={() => setReloadKey((current) => current + 1)}
          />
        </div>
      ) : result ? (
        <BossResultPanel
          result={result}
          bossName={bossName}
          onRetry={handleRetry}
          retrying={retrying}
          retryError={retryError}
        />
      ) : (
        <BossQuestionCard
          question={attempt.question}
          questionNumber={Number(attempt.question_number) || 1}
          total={total}
          subject={attempt.quiz?.subject}
          selected={selected}
          onSelect={setSelected}
          onCheck={handleCheck}
          checking={checking}
          feedback={feedback}
          onNext={handleNext}
          error={checkError}
          answeredCount={Number(attempt.answered_count) || 0}
        />
      )}
    </div>
  )
}
