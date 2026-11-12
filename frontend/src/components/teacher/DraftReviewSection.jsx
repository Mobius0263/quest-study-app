import { useState } from 'react'
import { deleteQuest, publishQuest, regenerateQuest } from '../../api/quests.js'
import { deleteQuiz, publishQuiz, regenerateQuiz } from '../../api/quizzes.js'
import {
  AlertCircleIcon,
  CheckIcon,
  EditIcon,
  RefreshIcon,
  TrashIcon,
} from '../ui/icons.jsx'

export default function DraftReviewSection({
  draftQuests = [],
  draftQuizzes = [],
  onEditQuest,
  onOpenModuleReview,
  onRefresh,
  onNotice,
}) {
  const [busyId, setBusyId] = useState(null)
  const [actionType, setActionType] = useState(null) // 'regenerating' | 'publishing' | 'deleting'
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [error, setError] = useState('')


  const totalDrafts = draftQuests.length + draftQuizzes.length

  if (totalDrafts === 0) {
    return null
  }

  function formatOcrFlag(ocrPages) {
    if (!ocrPages || !Array.isArray(ocrPages) || ocrPages.length === 0) return null
    const pagesStr =
      ocrPages.length === 1
        ? `Page ${ocrPages[0]}`
        : `Pages ${ocrPages.join('–')}`
    return `${pagesStr} were read from scans — check the questions against the module.`
  }

  async function handlePublishQuest(quest) {
    setBusyId(`quest-${quest.id}`)
    setActionType('publishing')
    setError('')
    try {
      await publishQuest(quest.id)
      onNotice?.(`"${quest.title}" published! Now live for students.`)
      onRefresh?.()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to publish quest.')
    } finally {
      setBusyId(null)
      setActionType(null)
    }
  }

  async function handleDeleteQuest(quest) {
    setBusyId(`quest-${quest.id}`)
    setActionType('deleting')
    setError('')
    try {
      await deleteQuest(quest.id)
      onNotice?.(`Draft quest "${quest.title}" discarded.`)
      onRefresh?.()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to delete draft quest.')
    } finally {
      setBusyId(null)
      setActionType(null)
      setConfirmDeleteId(null)
    }
  }

  async function handleRegenerateQuest(quest) {
    setBusyId(`quest-${quest.id}`)
    setActionType('regenerating')
    setError('')
    try {
      const res = await regenerateQuest(quest.id)
      onNotice?.(`"${quest.title}" regenerated with fresh AI questions. Stored as draft.`)
      if (res.ocr_pages && res.ocr_pages.length > 0) {
        // ocr_pages will be reflected in quest data upon refresh
      }
      onRefresh?.()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to regenerate quest.')
    } finally {
      setBusyId(null)
      setActionType(null)
    }
  }

  async function handlePublishQuiz(quiz) {
    setBusyId(`quiz-${quiz.id}`)
    setActionType('publishing')
    setError('')
    try {
      await publishQuiz(quiz.id)
      onNotice?.(`Boss Quiz "${quiz.title}" published! Now live for students.`)
      onRefresh?.()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to publish quiz.')
    } finally {
      setBusyId(null)
      setActionType(null)
    }
  }

  async function handleDeleteQuiz(quiz) {
    setBusyId(`quiz-${quiz.id}`)
    setActionType('deleting')
    setError('')
    try {
      await deleteQuiz(quiz.id)
      onNotice?.(`Draft Boss Exam "${quiz.title}" discarded.`)
      onRefresh?.()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to delete draft quiz.')
    } finally {
      setBusyId(null)
      setActionType(null)
      setConfirmDeleteId(null)
    }
  }

  async function handleRegenerateQuiz(quiz) {
    setBusyId(`quiz-${quiz.id}`)
    setActionType('regenerating')
    setError('')
    try {
      await regenerateQuiz(quiz.id)
      onNotice?.(`Boss Quiz "${quiz.title}" regenerated. Stored as draft.`)
      onRefresh?.()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to regenerate quiz.')
    } finally {
      setBusyId(null)
      setActionType(null)
    }
  }

  return (
    <section className="teacher-section draft-review-section" aria-labelledby="draft-review-title">
      <div className="sec-head">
        <h4 id="draft-review-title">Review before publishing</h4>
        <span className="teacher-section-note">
          {totalDrafts} {totalDrafts === 1 ? 'draft' : 'drafts'} awaiting approval (hidden from students)
        </span>
      </div>

      {error && (
        <div className="form-error" role="alert" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      <div className="draft-grid" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {draftQuests.map((quest) => {
          const isBusy = busyId === `quest-${quest.id}`
          const ocrMessage = formatOcrFlag(quest.ocr_pages)

          return (
            <div key={`quest-${quest.id}`} className="card draft-card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="status-pill prog">Draft Quest</span>
                    <span className="subject-pill">{quest.subject}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--mm)' }}>
                      {quest.quest_type === 'revision' ? 'Revision' : 'Assignment'}
                    </span>
                    {quest.is_ungrounded && (
                      <span className="status-pill warn" style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#ca8a04' }}>
                        Ungrounded
                      </span>
                    )}
                  </div>
                  <h4 style={{ margin: '4px 0 6px' }}>{quest.title}</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--mm)' }}>
                    {quest.description || 'No description provided.'}
                  </p>
                </div>

                <div className="draft-actions" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {confirmDeleteId === `quest-${quest.id}` ? (
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', background: 'rgba(239, 68, 68, 0.08)', padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(239, 68, 68, 0.25)' }}>
                      <span style={{ fontSize: '0.8rem', color: '#b91c1c', fontWeight: 600 }}>Discard draft?</span>
                      <button
                        type="button"
                        className="btn-danger"
                        style={{ padding: '3px 8px', fontSize: '0.8rem' }}
                        onClick={() => handleDeleteQuest(quest)}
                        disabled={isBusy}
                      >
                        {isBusy && actionType === 'deleting' ? 'Discarding…' : 'Yes, Discard'}
                      </button>
                      <button
                        type="button"
                        className="btn-ghost"
                        style={{ padding: '3px 6px', fontSize: '0.8rem' }}
                        onClick={() => setConfirmDeleteId(null)}
                        disabled={isBusy}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => setConfirmDeleteId(`quest-${quest.id}`)}
                      disabled={isBusy}
                      title="Discard draft quest"
                      style={{ color: '#ef4444' }}
                    >
                      <TrashIcon size={15} />
                      Discard
                    </button>
                  )}

                  {quest.module && onOpenModuleReview && (
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => onOpenModuleReview(quest.module)}
                      disabled={isBusy}
                      title="Review all 25 batch questions"
                    >
                      Review Batches
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => onEditQuest?.(quest)}
                    disabled={isBusy}
                    title="Edit draft content"
                  >
                    <EditIcon size={15} />
                    Edit
                  </button>

                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => handleRegenerateQuest(quest)}
                    disabled={isBusy}
                    title="Regenerate questions using local AI"
                  >
                    <RefreshIcon size={15} />
                    {isBusy && actionType === 'regenerating' ? 'Regenerating…' : 'Regenerate'}
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => handlePublishQuest(quest)}
                    disabled={isBusy}
                    title="Publish and make live for students"
                  >
                    <CheckIcon size={15} />
                    {isBusy && actionType === 'publishing' ? 'Publishing…' : 'Publish'}
                  </button>
                </div>
              </div>

              {ocrMessage && (
                <div
                  className="card-callout warning"
                  style={{
                    marginTop: 12,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 12px',
                    borderRadius: 'var(--r-sub, 8px)',
                    background: 'rgba(234, 179, 8, 0.12)',
                    color: '#ca8a04',
                    border: '1px solid rgba(234, 179, 8, 0.3)',
                    fontSize: '0.85rem',
                  }}
                >
                  <AlertCircleIcon size={16} />
                  <span>{ocrMessage}</span>
                </div>
              )}
            </div>
          )
        })}

        {draftQuizzes.map((quiz) => {
          const isBusy = busyId === `quiz-${quiz.id}`
          const ocrMessage = formatOcrFlag(quiz.ocr_pages)

          return (
            <div key={`quiz-${quiz.id}`} className="card draft-card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="status-pill prog">Draft Boss Exam</span>
                    <span className="subject-pill">{quiz.subject}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--mm)' }}>
                      {quiz.question_count || 20} questions · Tier: {quiz.difficulty_tier || 'normal'}
                    </span>
                    {quiz.is_ungrounded && (
                      <span className="status-pill warn" style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#ca8a04' }}>
                        Ungrounded
                      </span>
                    )}
                  </div>
                  <h4 style={{ margin: '4px 0 6px' }}>{quiz.title}</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--mm)' }}>
                    Boss: {quiz.boss_name} ({quiz.boss_hp} HP) · Required Correct: {quiz.required_correct}
                  </p>
                </div>

                <div className="draft-actions" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {confirmDeleteId === `quiz-${quiz.id}` ? (
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', background: 'rgba(239, 68, 68, 0.08)', padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(239, 68, 68, 0.25)' }}>
                      <span style={{ fontSize: '0.8rem', color: '#b91c1c', fontWeight: 600 }}>Discard draft?</span>
                      <button
                        type="button"
                        className="btn-danger"
                        style={{ padding: '3px 8px', fontSize: '0.8rem' }}
                        onClick={() => handleDeleteQuiz(quiz)}
                        disabled={isBusy}
                      >
                        {isBusy && actionType === 'deleting' ? 'Discarding…' : 'Yes, Discard'}
                      </button>
                      <button
                        type="button"
                        className="btn-ghost"
                        style={{ padding: '3px 6px', fontSize: '0.8rem' }}
                        onClick={() => setConfirmDeleteId(null)}
                        disabled={isBusy}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => setConfirmDeleteId(`quiz-${quiz.id}`)}
                      disabled={isBusy}
                      title="Discard draft boss exam"
                      style={{ color: '#ef4444' }}
                    >
                      <TrashIcon size={15} />
                      Discard
                    </button>
                  )}

                  {quiz.module && onOpenModuleReview && (
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => onOpenModuleReview(quiz.module)}
                      disabled={isBusy}
                      title="Review all 25 batch questions"
                    >
                      Review Batches
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => handleRegenerateQuiz(quiz)}

                    disabled={isBusy}
                    title="Regenerate questions using local AI"
                  >
                    <RefreshIcon size={15} />
                    {isBusy && actionType === 'regenerating' ? 'Regenerating…' : 'Regenerate'}
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => handlePublishQuiz(quiz)}
                    disabled={isBusy}
                    title="Publish and make live for students"
                  >
                    <CheckIcon size={15} />
                    {isBusy && actionType === 'publishing' ? 'Publishing…' : 'Publish'}
                  </button>
                </div>
              </div>

              {ocrMessage && (
                <div
                  className="card-callout warning"
                  style={{
                    marginTop: 12,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '8px 12px',
                    borderRadius: 'var(--r-sub, 8px)',
                    background: 'rgba(234, 179, 8, 0.12)',
                    color: '#ca8a04',
                    border: '1px solid rgba(234, 179, 8, 0.3)',
                    fontSize: '0.85rem',
                  }}
                >
                  <AlertCircleIcon size={16} />
                  <span>{ocrMessage}</span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
