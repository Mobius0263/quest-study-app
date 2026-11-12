import { useEffect, useId, useState } from 'react'
import {
  deleteQuiz,
  generateQuiz,
  updateQuiz,
} from '../../api/quizzes.js'
import { getModules } from '../../api/modules.js'
import { SUBJECT_NAMES } from '../../utils/subjects.js'
import { AlertCircleIcon, CheckIcon, SwordIcon } from '../ui/icons.jsx'

const DEFAULT_BOSS_QUESTIONS = 20


const SOURCE_LABELS = {
  database_cache: 'Server cache',
  ollama: 'Ollama',
  ollama_retry: 'Ollama retry',
  fallback_bank: 'Fallback bank',
}

function getGenerationErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  if (error.response.status === 400) {
    return 'Check the subject, topic and question count, then try again.'
  }
  return "We couldn't generate this boss quiz. Please try again."
}

function getPublishErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check your connection and try again.'
  }
  return "We couldn't publish this boss quiz. Please try again."
}

function validate(values) {
  const errors = {}
  const topic = values.topic.trim()

  if (!values.subject) errors.subject = 'Choose a subject.'
  if (!topic) {
    errors.topic = 'Enter a topic for the quiz.'
  } else if (topic.length > 200) {
    errors.topic = 'Keep the topic under 200 characters.'
  }

  const count = Number(values.numQuestions)
  if (!Number.isInteger(count) || count < 5 || count > 50) {
    errors.numQuestions = 'Boss exams must have between 5 and 50 questions.'
  }

  return errors
}

function getQuestionCount(quiz) {
  const questions = quiz?.content?.questions
  return Array.isArray(questions) ? questions.length : 0
}

export default function TeacherQuizForm({
  className,
  onCancel,
  onPublished,
}) {
  const [values, setValues] = useState({
    subject: '',
    topic: '',
    moduleId: '',
    numQuestions: String(DEFAULT_BOSS_QUESTIONS),
  })
  const [modules, setModules] = useState([])
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [result, setResult] = useState(null)
  const subjectErrorId = useId()
  const topicErrorId = useId()
  const numQuestionsErrorId = useId()
  const numQuestionsHintId = useId()

  useEffect(() => {
    async function loadModules() {
      try {
        const list = await getModules()
        if (Array.isArray(list)) setModules(list)
      } catch {
        // ignore
      }

    }
    loadModules()
  }, [])

  const subjectModules = modules.filter(
    (m) =>
      values.subject &&
      m.subject &&
      m.subject.toLowerCase() === values.subject.toLowerCase(),
  )

  const busy = submitting || regenerating || publishing
  const quiz = result?.quiz ?? null
  const questions = quiz?.content?.questions ?? []
  const questionCount = getQuestionCount(quiz)
  const isPublished = Boolean(quiz?.is_published)

  function setField(name, value) {
    setValues((current) => ({ ...current, [name]: value }))
    setErrors((current) => {
      if (!current[name]) return current
      const next = { ...current }
      delete next[name]
      return next
    })
  }

  function handleSelectModule(modId) {
    if (!modId) {
      setValues((current) => ({ ...current, moduleId: '' }))
      return
    }
    const found = modules.find((m) => String(m.id) === String(modId))
    setValues((current) => ({
      ...current,
      moduleId: modId,
      topic: found ? (found.topic || found.title || current.topic) : current.topic,
    }))
  }

  async function handleGenerate(event) {
    event.preventDefault()
    const nextErrors = validate(values)
    setErrors(nextErrors)
    setError('')
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    try {
      const response = await generateQuiz({
        subject: values.subject,
        topic: values.topic.trim(),
        module_id: values.moduleId ? Number(values.moduleId) : null,
        num_questions: Number(values.numQuestions),
      })
      setResult(response)
    } catch (requestError) {
      setError(getGenerationErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRegenerate() {
    if (!result?.quiz || regenerating) return

    setRegenerating(true)
    setError('')
    const previousQuiz = result.quiz
    try {
      const response = await generateQuiz({
        subject: values.subject,
        topic: values.topic.trim(),
        module_id: values.moduleId ? Number(values.moduleId) : null,
        num_questions: Number(values.numQuestions),
        regenerate: true,
      })
      setResult(response)

      // Keep the catalog tidy: the replaced draft was never visible to
      // students. A published quiz can never reach this branch.
      if (!previousQuiz.is_published) {
        deleteQuiz(previousQuiz.id).catch(() => {})
      }
    } catch (requestError) {
      setError(getGenerationErrorMessage(requestError))
    } finally {
      setRegenerating(false)
    }
  }


  async function handlePublish() {
    if (!quiz || publishing) return

    setPublishing(true)
    setError('')
    try {
      const updated = await updateQuiz(quiz.id, { is_published: true })
      onPublished?.(updated)
    } catch (requestError) {
      setError(getPublishErrorMessage(requestError))
    } finally {
      setPublishing(false)
    }
  }

  if (result && quiz) {
    return (
      <div className="teacher-quiz-review">
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}

        <div className="quiz-review-status">
          <span
            className={`status-pill ${isPublished ? 'done' : 'prog'}`.trim()}
          >
            {isPublished ? 'Live' : 'Draft'}
          </span>
          <span>{result.cached ? 'Reused from cache' : 'Newly generated'}</span>
          <span>{SOURCE_LABELS[result.generation_source] || 'AI service'}</span>
        </div>

        <div className="quiz-review-copy">
          <div className="layout-note">Review before publishing</div>
          <h3>{quiz.title}</h3>
          <p>
            {[quiz.subject, `${questionCount} questions`, quiz.boss_name]
              .filter(Boolean)
              .join(' · ')}
          </p>
          <p className="quiz-review-cache">
            {result.cached
              ? `Generated once — reused for ${className}.`
              : `Generated now and saved as a draft for ${className}.`}
          </p>
        </div>

        <div className="quiz-review-questions" aria-label="Generated questions">
          <ol>
            {questions.map((question, index) => (
              <li key={question.id ?? index} className="quiz-review-question">
                <p className="quiz-review-question-text">
                  <span>{index + 1}.</span> {question.question}
                </p>
                <ul className="quiz-review-options">
                  {(question.options || []).map((option) => {
                    const correct = option === question.correct_answer
                    return (
                      <li
                        key={option}
                        className={correct ? 'correct' : undefined}
                      >
                        {correct && <CheckIcon size={13} />}
                        <span>{option}</span>
                      </li>
                    )
                  })}
                </ul>
                {question.explanation && (
                  <p className="quiz-review-explanation">
                    {question.explanation}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </div>

        <div className="modal-actions teacher-quiz-review-actions">
          <button
            type="button"
            className="btn-ghost"
            onClick={onCancel}
            disabled={busy}
          >
            {isPublished ? 'Close' : 'Save draft & close'}
          </button>
          {!isPublished && (
            <button
              type="button"
              className="btn-ghost"
              onClick={handleRegenerate}
              disabled={busy}
            >
              {regenerating ? 'Regenerating…' : 'Regenerate'}
            </button>
          )}
          {isPublished ? (
            <button
              type="button"
              className="btn-primary"
              onClick={onCancel}
              disabled={busy}
            >
              Done
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary"
              onClick={handlePublish}
              disabled={busy || questions.length === 0}
            >
              {publishing ? 'Publishing…' : 'Publish boss quiz'}
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <form className="quest-form" onSubmit={handleGenerate} noValidate>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}

      <div className="form-group">
        <label className="form-label" htmlFor="boss-quiz-subject">
          Subject
        </label>
        <select
          id="boss-quiz-subject"
          className="form-select"
          value={values.subject}
          onChange={(event) => setField('subject', event.target.value)}
          aria-invalid={Boolean(errors.subject)}
          aria-describedby={errors.subject ? subjectErrorId : undefined}
          data-autofocus
          disabled={busy}
        >
          <option value="">Choose a subject</option>
          {SUBJECT_NAMES.map((subject) => (
            <option key={subject} value={subject}>
              {subject}
            </option>
          ))}
        </select>
        {errors.subject && (
          <span id={subjectErrorId} className="form-field-error">
            {errors.subject}
          </span>
        )}
      </div>

      <div className="form-group">
        <label className="form-label" htmlFor="boss-quiz-module">
          Module Grounding
        </label>
        <select
          id="boss-quiz-module"
          className="form-select"
          value={values.moduleId}
          onChange={(event) => handleSelectModule(event.target.value)}
          disabled={busy || !values.subject}
        >
          <option value="">
            {!values.subject
              ? 'Choose a subject first'
              : subjectModules.length === 0
              ? 'No uploaded modules for this subject'
              : 'Link to an uploaded module (recommended)'}
          </option>
          {subjectModules.map((m) => (
            <option key={m.id} value={m.id}>
              {m.topic || m.title} ({m.page_count || 1} pgs)
            </option>
          ))}
        </select>
        {values.subject && subjectModules.length === 0 && (
          <span className="form-hint" style={{ color: 'var(--mm)' }}>
            No uploaded modules for this subject. Questions will be ungrounded.
          </span>
        )}
      </div>

      <div className="form-group">
        <label className="form-label" htmlFor="boss-quiz-topic">
          Topic
        </label>
        <input
          id="boss-quiz-topic"
          className="form-input"
          type="text"
          value={values.topic}
          onChange={(event) => setField('topic', event.target.value)}
          maxLength={200}
          autoComplete="off"
          placeholder="e.g. Cell division"
          aria-invalid={Boolean(errors.topic)}
          aria-describedby={errors.topic ? topicErrorId : undefined}
          disabled={busy}
        />
        {errors.topic ? (
          <span id={topicErrorId} className="form-field-error">
            {errors.topic}
          </span>
        ) : (
          <span className="form-hint">
            The topic is also the cache key for this class.
          </span>
        )}
        {!values.moduleId && (
          <div
            className="card-callout warning"
            style={{
              marginTop: 8,
              padding: '6px 10px',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <AlertCircleIcon size={14} />
            <span>
              <b>Ungrounded:</b> Not linked to an uploaded module (AI may hallucinate without textbook grounding).
            </span>
          </div>
        )}
      </div>

      <div className="form-group">
        <label className="form-label" htmlFor="boss-quiz-count">
          Question count
        </label>
        <select
          id="boss-quiz-count"
          className="form-select"
          value={values.numQuestions}
          onChange={(event) => setField('numQuestions', event.target.value)}
          aria-invalid={Boolean(errors.numQuestions)}
          aria-describedby={
            errors.numQuestions ? numQuestionsErrorId : numQuestionsHintId
          }
          disabled={busy}
        >
          <option value="20">20 questions (Default — 4 batches)</option>
          <option value="30">30 questions (Extended — 6 batches)</option>
          <option value="15">15 questions (3 batches)</option>
          <option value="25">25 questions (5 batches)</option>
        </select>
        {errors.numQuestions ? (
          <span id={numQuestionsErrorId} className="form-field-error">
            {errors.numQuestions}
          </span>
        ) : (
          <span id={numQuestionsHintId} className="form-hint">
            Boss exams default to 20 questions across ramping batches.
          </span>
        )}
      </div>


      <div className="teacher-quiz-note">
        <SwordIcon size={17} />
        <span>
          The quiz is stored as a draft first. Nothing reaches students until
          you review it and press Publish.
        </span>
      </div>

      <div className="modal-actions">
        <button
          type="button"
          className="btn-ghost"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={busy}>
          {submitting ? 'Generating…' : 'Generate boss quiz'}
        </button>
      </div>
    </form>
  )
}
