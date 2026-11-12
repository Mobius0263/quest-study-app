import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getQuest } from '../api/quests.js'
import {
  checkQuizAnswer,
  getQuiz,
  submitQuizAttempt,
} from '../api/quizzes.js'
import { getApiErrorMessage } from '../api/errors.js'
import { useAuth } from '../context/AuthContext.js'
import {
  getLinkedQuiz,
  getQuizQuestions,
} from '../utils/questDetail.js'
import PageHeader from '../components/ui/PageHeader.jsx'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StateViews.jsx'
import { ChevronLeftIcon, MapIcon } from '../components/ui/icons.jsx'
import QuizQuestionCard from '../components/quiz/QuizQuestionCard.jsx'
import QuizResultPanel from '../components/quiz/QuizResultPanel.jsx'

const INITIAL_PAGE = {
  status: 'loading',
  quest: null,
  quiz: null,
  questions: [],
  error: '',
}

function getQuizLoadMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  if (error.response.status === 404) {
    return 'This quest or quiz could not be found.'
  }
  return "We couldn't load the quest quiz. Please try again."
}

export default function QuestQuizPage() {
  const { questId } = useParams()
  const location = useLocation()
  const { isStudent } = useAuth()
  const boardSearch = location.state?.boardSearch || ''

  const [page, setPage] = useState(INITIAL_PAGE)
  const [reloadKey, setReloadKey] = useState(0)
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [answers, setAnswers] = useState({})
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [attemptError, setAttemptError] = useState('')
  const [result, setResult] = useState(null)
  const [best, setBest] = useState(null)
  const startedAtRef = useRef(0)

  const resetAttempt = useCallback(() => {
    setIndex(0)
    setSelected('')
    setFeedback(null)
    setAnswers({})
    setChecking(false)
    setCheckError('')
    setSubmitting(false)
    setAttemptError('')
    setResult(null)
    startedAtRef.current = Date.now()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    setPage((current) => ({ ...current, status: 'loading', error: '' }))
    resetAttempt()

    async function loadQuiz() {
      try {
        const quest = await getQuest(questId, { signal: controller.signal })
        if (cancelled) return

        if (!isStudent) {
          setPage({
            status: 'not-student',
            quest,
            quiz: null,
            questions: [],
            error: '',
          })
          return
        }

        const linkedQuiz = getLinkedQuiz(quest)
        if (!linkedQuiz?.id) {
          setPage({
            status: 'empty',
            quest,
            quiz: null,
            questions: [],
            error: 'This quest has no linked quiz yet.',
          })
          return
        }

        const quiz = await getQuiz(linkedQuiz.id, { signal: controller.signal })
        if (cancelled) return

        const questions = getQuizQuestions(quiz)
        if (questions.length === 0) {
          setPage({
            status: 'empty',
            quest,
            quiz,
            questions: [],
            error: 'This quiz has no questions yet.',
          })
          return
        }

        setBest(linkedQuiz.best_attempt || null)
        startedAtRef.current = Date.now()
        setPage({ status: 'ready', quest, quiz, questions, error: '' })
      } catch (error) {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setPage({
          status: 'error',
          quest: null,
          quiz: null,
          questions: [],
          error: getQuizLoadMessage(error),
        })
      }
    }

    loadQuiz()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [questId, reloadKey, isStudent, resetAttempt])

  async function handleCheck() {
    const question = page.questions[index]
    if (!question || !selected || checking || feedback) return

    setChecking(true)
    setCheckError('')
    try {
      const data = await checkQuizAnswer(page.quiz.id, {
        question_id: question.id,
        answer: selected,
      })
      setFeedback(data)
      setAnswers((current) => ({
        ...current,
        [String(question.id)]: selected,
      }))
    } catch (error) {
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

  async function submitAttempt() {
    setSubmitting(true)
    setAttemptError('')
    try {
      const elapsed = Math.max(
        0,
        Math.round((Date.now() - startedAtRef.current) / 1000),
      )
      const data = await submitQuizAttempt(page.quiz.id, {
        mode: 'quest',
        answers,
        time_taken_seconds: elapsed,
      })
      setResult(data)
      setBest(data.best_attempt || best)
    } catch (error) {
      setAttemptError(
        getApiErrorMessage(
          error,
          "We couldn't score your quiz. Your answers are still here — please try again.",
        ),
      )
    } finally {
      setSubmitting(false)
    }
  }

  function handleContinue() {
    if (!feedback) return
    if (index < page.questions.length - 1) {
      setIndex((current) => current + 1)
      setSelected('')
      setFeedback(null)
      setCheckError('')
      return
    }
    submitAttempt()
  }

  function handleRetry() {
    resetAttempt()
  }

  const backLink = (
    <Link
      to={`/quests/${questId}`}
      state={{ boardSearch }}
      className="btn-ghost"
    >
      <ChevronLeftIcon size={16} />
      Back to quest
    </Link>
  )

  if (page.status === 'loading') {
    return (
      <div className="screen-stack quiz-screen">
        <div className="detail-topbar">
          {backLink}
          <span className="layout-note">Quest quiz</span>
        </div>
        <div className="card">
          <LoadingState label="Preparing the quest quiz…" />
        </div>
      </div>
    )
  }

  if (page.status === 'error') {
    return (
      <div className="screen-stack quiz-screen">
        <div className="detail-topbar">
          {backLink}
          <span className="layout-note">Quest quiz</span>
        </div>
        <div className="card">
          <ErrorState
            title="We couldn't open the quiz"
            message={page.error}
            onRetry={() => setReloadKey((current) => current + 1)}
          />
        </div>
      </div>
    )
  }

  if (page.status === 'not-student') {
    return (
      <div className="screen-stack quiz-screen">
        <div className="detail-topbar">
          {backLink}
          <span className="layout-note">Quest quiz</span>
        </div>
        <div className="card">
          <EmptyState
            icon={MapIcon}
            title="Quest quizzes are for students"
            message="You can review the quest content from the quest detail."
          />
        </div>
      </div>
    )
  }

  if (page.status === 'empty') {
    return (
      <div className="screen-stack quiz-screen">
        <div className="detail-topbar">
          {backLink}
          <span className="layout-note">Quest quiz</span>
        </div>
        <div className="card">
          <EmptyState
            icon={MapIcon}
            title="No quiz to play yet"
            message={page.error}
          />
        </div>
      </div>
    )
  }

  const total = page.questions.length
  const question = page.questions[index]

  return (
    <div className="screen-stack quiz-screen">
      <div className="detail-topbar">
        {backLink}
        <span className="layout-note">Quest quiz</span>
      </div>

      <PageHeader
        eyebrow="Practice quiz"
        title="Quest quiz"
        subtitle={`${page.quest.title} · ${total} question${total === 1 ? '' : 's'} · pass line 80%`}
      />

      {result ? (
        <QuizResultPanel
          result={result}
          questId={questId}
          boardSearch={boardSearch}
          onRetry={handleRetry}
        />
      ) : (
        <>
          {best?.score != null && (
            <div className="quiz-best-pill">
              Best attempt so far: {best.correct_count} / {total} · {best.score}%
            </div>
          )}
          <QuizQuestionCard
            question={question}
            questionNumber={index + 1}
            total={total}
            selected={selected}
            onSelect={setSelected}
            onCheck={handleCheck}
            checking={checking}
            feedback={feedback}
            onContinue={handleContinue}
            isLast={index === total - 1}
            submitting={submitting}
            checkError={attemptError || checkError}
          />
        </>
      )}
    </div>
  )
}
