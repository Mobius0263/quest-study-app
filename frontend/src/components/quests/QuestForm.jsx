import { useEffect, useId, useState } from 'react'
import {
  DIFFICULTIES,
  DIFFICULTY_META,
  normalizeDifficulty,
} from '../../utils/quests.js'
import { SUBJECT_NAMES } from '../../utils/subjects.js'
import {
  deadlineInputToIso,
  isDeadlineInputInPast,
  toDateInputValue,
} from '../../utils/dates.js'
import { getModules } from '../../api/modules.js'
import GemRow from '../ui/GemRow.jsx'
import { AlertCircleIcon, ZapIcon } from '../ui/icons.jsx'

const QUEST_TYPES = [
  { value: 'assignment', label: 'Assignment' },
  { value: 'revision', label: 'Revision' },
]

function getInitialType(quest, allowType) {
  if (quest?.quest_type === 'revision') return 'revision'
  if (quest?.quest_type === 'assignment') return 'assignment'
  return allowType ? 'assignment' : 'revision'
}

function buildInitialValues(quest, allowType) {
  return {
    title: quest?.title || '',
    subject: quest?.subject || '',
    moduleId: quest?.module || quest?.module_id || '',
    type: getInitialType(quest, allowType),
    difficulty: quest
      ? normalizeDifficulty(quest.difficulty, quest.reward_xp ?? quest.xp)
      : 'Medium',
    deadline: toDateInputValue(quest?.dueDate || quest?.due_date),
  }
}


function validate(values, allowType) {
  const errors = {}
  const title = values.title.trim()

  if (!title) {
    errors.title = 'Enter a quest title.'
  } else if (title.length > 200) {
    errors.title = 'Keep the title under 200 characters.'
  }

  if (!values.subject) errors.subject = 'Choose a subject.'
  if (allowType && !QUEST_TYPES.some((option) => option.value === values.type)) {
    errors.type = 'Choose Assignment or Revision.'
  }
  if (!DIFFICULTY_META[values.difficulty]) {
    errors.difficulty = 'Choose a difficulty.'
  }

  if (!values.deadline) {
    errors.deadline = 'Choose a deadline.'
  } else if (isDeadlineInputInPast(values.deadline)) {
    errors.deadline = 'Choose today or a future date.'
  }

  return errors
}

function getFormErrorMessage(error, contextLabel) {
  if (!error?.response) {
    return 'Cannot reach the server. Check your connection and try again.'
  }
  if (error.response.status === 400) {
    return 'Please check the form and try again.'
  }
  return `We couldn't save this ${contextLabel}. Please try again.`
}

export default function QuestForm({
  quest,
  onSubmit,
  onCancel,
  allowType = false,
  contextLabel = 'quest',
}) {
  const [values, setValues] = useState(() =>
    buildInitialValues(quest, allowType),
  )
  const [modules, setModules] = useState([])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const titleErrorId = useId()
  const subjectErrorId = useId()
  const typeErrorId = useId()
  const difficultyErrorId = useId()
  const deadlineErrorId = useId()
  const typeLabelId = useId()
  const difficultyLabelId = useId()

  useEffect(() => {
    async function fetchModules() {
      try {
        const list = await getModules()
        if (Array.isArray(list)) setModules(list)
      } catch {
        // ignore
      }

    }
    fetchModules()
  }, [])

  const subjectModules = modules.filter(
    (m) =>
      values.subject &&
      m.subject &&
      m.subject.toLowerCase() === values.subject.toLowerCase(),
  )

  const subjectOptions =
    values.subject && !SUBJECT_NAMES.includes(values.subject)
      ? [...SUBJECT_NAMES, values.subject]
      : SUBJECT_NAMES

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
      title: found ? (found.topic || found.title || current.title) : current.title,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const nextErrors = validate(values, allowType)
    setErrors(nextErrors)
    setFormError('')

    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    try {
      await onSubmit({
        title: values.title.trim(),
        subject: values.subject,
        module_id: values.moduleId ? Number(values.moduleId) : null,
        quest_type: allowType ? values.type : 'revision',
        reward_xp: DIFFICULTY_META[values.difficulty].xp,
        due_date: deadlineInputToIso(values.deadline),
      })
    } catch (error) {
      setFormError(getFormErrorMessage(error, contextLabel))
    } finally {
      setSubmitting(false)
    }
  }


  return (
    <form className="quest-form" onSubmit={handleSubmit} noValidate>
      {formError && (
        <div className="form-error" role="alert">
          {formError}
        </div>
      )}

      <div className="form-group">
        <label className="form-label" htmlFor="quest-title">
          Title
        </label>
        <input
          id="quest-title"
          className="form-input"
          type="text"
          value={values.title}
          onChange={(event) => setField('title', event.target.value)}
          maxLength={200}
          autoComplete="off"
          data-autofocus
          aria-invalid={Boolean(errors.title)}
          aria-describedby={errors.title ? titleErrorId : undefined}
          placeholder={
            allowType ? 'What should students work on?' : 'What will you revise?'
          }
          disabled={submitting}
        />
        {errors.title && (
          <span id={titleErrorId} className="form-field-error">
            {errors.title}
          </span>
        )}
        {allowType && !values.moduleId && (
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
              <b>Ungrounded:</b> Not linked to an uploaded module.
            </span>
          </div>
        )}
      </div>


      {allowType && (
        <div className="form-group">
          <span id={typeLabelId} className="form-label">
            Quest type
          </span>
          <div
            className="quest-type-options"
            role="group"
            aria-labelledby={typeLabelId}
            aria-describedby={errors.type ? typeErrorId : undefined}
          >
            {QUEST_TYPES.map((option) => {
              const active = values.type === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  className={`quest-type-option ${active ? 'active' : ''}`.trim()}
                  onClick={() => setField('type', option.value)}
                  aria-pressed={active}
                  disabled={submitting}
                >
                  {option.label}
                </button>
              )
            })}
          </div>
          <span className="form-hint">
            Assignments are class work; Revision Quests are study practice.
          </span>
          {errors.type && (
            <span id={typeErrorId} className="form-field-error">
              {errors.type}
            </span>
          )}
        </div>
      )}

      <div className="form-grid">
        <div className="form-group">
          <label className="form-label" htmlFor="quest-subject">
            Subject
          </label>
          <select
            id="quest-subject"
            className="form-select"
            value={values.subject}
            onChange={(event) => setField('subject', event.target.value)}
            aria-invalid={Boolean(errors.subject)}
            aria-describedby={errors.subject ? subjectErrorId : undefined}
            disabled={submitting}
          >
            <option value="">Choose a subject</option>
            {subjectOptions.map((subject) => (
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

        {allowType && (
          <div className="form-group">
            <label className="form-label" htmlFor="quest-module">
              Module Grounding
            </label>
            <select
              id="quest-module"
              className="form-select"
              value={values.moduleId}
              onChange={(event) => handleSelectModule(event.target.value)}
              disabled={submitting || !values.subject}
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
        )}

        <div className="form-group">
          <label className="form-label" htmlFor="quest-deadline">
            Deadline
          </label>

          <input
            id="quest-deadline"
            className="form-input"
            type="date"
            value={values.deadline}
            onChange={(event) => setField('deadline', event.target.value)}
            aria-invalid={Boolean(errors.deadline)}
            aria-describedby={errors.deadline ? deadlineErrorId : undefined}
            disabled={submitting}
          />
          {errors.deadline ? (
            <span id={deadlineErrorId} className="form-field-error">
              {errors.deadline}
            </span>
          ) : (
            <span className="form-hint">Choose today or a future date.</span>
          )}
        </div>
      </div>

      <div className="form-group">
        <span id={difficultyLabelId} className="form-label">
          Difficulty
        </span>
        <div
          className="difficulty-options"
          role="group"
          aria-labelledby={difficultyLabelId}
          aria-describedby={errors.difficulty ? difficultyErrorId : undefined}
        >
          {DIFFICULTIES.map((difficulty) => {
            const meta = DIFFICULTY_META[difficulty]
            const active = values.difficulty === difficulty

            return (
              <button
                key={difficulty}
                type="button"
                className={`difficulty-option ${active ? 'active' : ''}`.trim()}
                onClick={() => setField('difficulty', difficulty)}
                aria-pressed={active}
                disabled={submitting}
              >
                <GemRow difficulty={difficulty} />
                <span className="difficulty-xp">
                  <ZapIcon size={11} />
                  {meta.xp} XP
                </span>
              </button>
            )
          })}
        </div>
        {errors.difficulty && (
          <span id={difficultyErrorId} className="form-field-error">
            {errors.difficulty}
          </span>
        )}
      </div>

      <div className="modal-actions">
        <button
          type="button"
          className="btn-ghost"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? 'Saving…' : quest ? 'Save changes' : 'Create quest'}
        </button>
      </div>
    </form>
  )
}
