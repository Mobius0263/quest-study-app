import { useEffect, useState } from 'react'
import {
  deleteModule,
  getModuleReview,
  publishModule,
  regenerateModuleBatch,
  updateModuleQuestion,
} from '../../api/modules.js'
import Modal from '../ui/Modal.jsx'
import {
  AlertCircleIcon,
  CheckIcon,
  EditIcon,
  RefreshIcon,
  TrashIcon,
} from '../ui/icons.jsx'

export default function ModuleReviewModal({ moduleId, onClose, onPublished, onDeleted }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyBatch, setBusyBatch] = useState(null)
  const [publishing, setPublishing] = useState(false)
  const [discarding, setDiscarding] = useState(false)
  const [confirmingDiscard, setConfirmingDiscard] = useState(false)
  const [editingQuestionId, setEditingQuestionId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [savingQuestion, setSavingQuestion] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)


  useEffect(() => {
    let active = true
    if (!moduleId) return undefined

    async function fetchReview() {
      setLoading(true)
      setError('')
      try {
        const res = await getModuleReview(moduleId)
        if (active) setData(res)
      } catch (err) {
        if (active) {
          setError(
            err?.response?.data?.error ||
              err?.response?.data?.detail ||
              'Failed to load module review data.'
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchReview()
    return () => {
      active = false
    }
  }, [moduleId, refreshKey])

  async function handleRegenerateBatch(batchIndex) {
    setBusyBatch(batchIndex)
    setError('')
    setSuccessMessage('')
    try {
      const res = await regenerateModuleBatch(moduleId, batchIndex)
      setData(res.review || data)
      setSuccessMessage(`Batch ${batchIndex} regenerated successfully!`)
      setRefreshKey((k) => k + 1)
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          `Failed to regenerate batch ${batchIndex}.`
      )
    } finally {
      setBusyBatch(null)
    }
  }

  function startEdit(question) {

    setEditingQuestionId(question.id)
    setEditForm({
      question: question.question || '',
      options: Array.isArray(question.options)
        ? [...question.options]
        : ['', '', '', ''],
      correct_answer: question.correct_answer || '',
      explanation: question.explanation || '',
    })
  }

  function cancelEdit() {
    setEditingQuestionId(null)
    setEditForm(null)
  }

  async function handleSaveEdit(questionId) {
    if (!editForm) return
    setSavingQuestion(true)
    setError('')
    try {
      await updateModuleQuestion(moduleId, questionId, editForm)
      setSuccessMessage('Question updated successfully.')
      setEditingQuestionId(null)
      setEditForm(null)
      setRefreshKey((k) => k + 1)
    } catch (err) {

      setError(
        err?.response?.data?.error ||
          err?.response?.data?.correct_answer?.[0] ||
          'Failed to update question.'
      )
    } finally {
      setSavingQuestion(false)
    }
  }

  async function handlePublishAll() {
    setPublishing(true)
    setError('')
    setSuccessMessage('')
    try {
      const res = await publishModule(moduleId)
      setSuccessMessage('Module and all questions published! Live for students.')
      setData(res.review || data)
      onPublished?.(res)
      setTimeout(() => {
        onClose?.()
      }, 1200)
    } catch (err) {
      setError(
        err?.response?.data?.error || 'Failed to publish module.'
      )
    } finally {
      setPublishing(false)
    }
  }

  async function handleDiscardModule() {
    setDiscarding(true)
    setError('')
    try {
      await deleteModule(moduleId)
      onDeleted?.(moduleId)
      onClose?.()
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.detail ||
          'Failed to discard module.'
      )
      setDiscarding(false)
      setConfirmingDiscard(false)
    }
  }

  const module = data?.module || {}
  const batches = data?.batches || []
  const ocrPages = data?.ocr_pages || []

  return (
    <Modal
      open={Boolean(moduleId)}
      onClose={onClose}
      title={`Review Module: ${module.title || module.topic || 'Questions'}`}
      className="module-review-modal"
    >
      <div className="module-review-container" style={{ maxHeight: '75vh', overflowY: 'auto', paddingRight: 8 }}>
        {loading && (
          <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--mm)' }}>
            Loading questions for review…
          </div>
        )}

        {error && (
          <div className="form-error" role="alert" style={{ marginBottom: 14 }}>
            {error}
          </div>
        )}

        {successMessage && (
          <div className="card-callout success" style={{ marginBottom: 14 }}>
            <CheckIcon size={18} />
            <span>{successMessage}</span>
          </div>
        )}

        {!loading && data && (
          <>
            <div
              className="module-review-header"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 12,
                paddingBottom: 12,
                borderBottom: '1px solid var(--bdr, #e2e8f0)',
                marginBottom: 16,
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="subject-pill">{module.subject}</span>
                  <span className="status-pill prog">Difficulty: {data.difficulty || 'Medium'}</span>
                  <span className={`status-pill ${data.status === 'published' ? 'comp' : 'prog'}`}>
                    {data.status === 'published' ? 'Published' : 'Ready for Review'}
                  </span>
                </div>
                <div style={{ marginTop: 4, fontSize: '0.85rem', color: 'var(--mm)' }}>
                  Total Questions: <b>{data.total_questions}</b> (5 Quest Quiz + {data.total_questions - 5} Boss Exam)
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                {confirmingDiscard ? (
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', background: 'rgba(239, 68, 68, 0.08)', padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(239, 68, 68, 0.25)' }}>
                    <span style={{ fontSize: '0.82rem', color: '#b91c1c', fontWeight: 600 }}>Discard module & drafts?</span>
                    <button
                      type="button"
                      className="btn-danger"
                      style={{ padding: '3px 8px', fontSize: '0.8rem' }}
                      onClick={handleDiscardModule}
                      disabled={discarding}
                    >
                      {discarding ? 'Deleting…' : 'Yes, Discard'}
                    </button>
                    <button
                      type="button"
                      className="btn-ghost"
                      style={{ padding: '3px 6px', fontSize: '0.8rem' }}
                      onClick={() => setConfirmingDiscard(false)}
                      disabled={discarding}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="btn-ghost"
                    style={{ color: '#b91c1c' }}
                    onClick={() => setConfirmingDiscard(true)}
                    disabled={publishing || discarding}
                    title="Delete this module and all generated draft questions"
                  >
                    <TrashIcon size={14} />
                    Discard Draft
                  </button>
                )}

                <button
                  type="button"
                  className="btn-primary"
                  onClick={handlePublishAll}
                  disabled={publishing || data.status === 'published'}
                  title="Make quest and boss exam live for students"
                >
                  <CheckIcon size={16} />
                  {publishing
                    ? 'Publishing…'
                    : data.status === 'published'
                    ? 'Already Published'
                    : 'Publish All'}
                </button>
              </div>
            </div>


            {ocrPages && ocrPages.length > 0 && (
              <div
                className="card-callout warning"
                style={{
                  marginBottom: 16,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 14px',
                  borderRadius: 'var(--r-sub, 8px)',
                  background: 'rgba(234, 179, 8, 0.12)',
                  color: '#ca8a04',
                  border: '1px solid rgba(234, 179, 8, 0.3)',
                  fontSize: '0.88rem',
                }}
              >
                <AlertCircleIcon size={20} />
                <span>
                  ⚠️ Pages {ocrPages.join('–')} were read from scans. Please verify questions against the original module before publishing.
                </span>
              </div>
            )}

            <div className="batches-list" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {batches.map((batch) => {
                const isBusy = busyBatch === batch.batch_index
                return (
                  <div
                    key={`batch-${batch.batch_index}`}
                    className="card batch-card"
                    style={{
                      padding: 16,
                      borderRadius: 'var(--r-sub, 8px)',
                      border: '1px solid var(--bdr, #e2e8f0)',
                      background: 'var(--card-bg, #fff)',
                    }}
                  >
                    <div
                      className="batch-header"
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: 8,
                        marginBottom: 12,
                        paddingBottom: 8,
                        borderBottom: '1px dashed var(--bdr, #e2e8f0)',
                      }}
                    >
                      <div>
                        <h4 style={{ margin: 0 }}>{batch.label}</h4>
                        <span style={{ fontSize: '0.8rem', color: 'var(--mm)' }}>
                          Section: {batch.section === 'quest_quiz' ? 'Quest Quiz' : 'Boss Exam'} · Target: {batch.difficulty}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => handleRegenerateBatch(batch.batch_index)}
                        disabled={isBusy || publishing}
                        style={{ fontSize: '0.85rem' }}
                      >
                        <RefreshIcon size={14} />
                        {isBusy ? 'Regenerating batch…' : 'Regenerate Batch'}
                      </button>
                    </div>

                    <div className="questions-list" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {batch.questions.map((q, qIdx) => {
                        const isEditing = editingQuestionId === q.id
                        return (
                          <div
                            key={`q-${q.id}`}
                            className="question-item"
                            style={{
                              padding: 12,
                              borderRadius: 6,
                              background: 'var(--sub-bg, #f8fafc)',
                              border: '1px solid var(--bdr, #edf2f7)',
                            }}
                          >
                            {isEditing ? (
                              <div className="question-editor">
                                <label style={{ display: 'block', fontWeight: 600, fontSize: '0.85rem', marginBottom: 4 }}>
                                  Question {qIdx + 1}
                                </label>
                                <textarea
                                  className="form-control"
                                  rows={2}
                                  value={editForm.question}
                                  onChange={(e) =>
                                    setEditForm({ ...editForm, question: e.target.value })
                                  }
                                  style={{ width: '100%', marginBottom: 8 }}
                                />

                                <label style={{ display: 'block', fontWeight: 600, fontSize: '0.85rem', marginBottom: 4 }}>
                                  Options & Correct Answer
                                </label>
                                {editForm.options.map((opt, optIdx) => (
                                  <div
                                    key={optIdx}
                                    style={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 8,
                                      marginBottom: 6,
                                    }}
                                  >
                                    <input
                                      type="radio"
                                      name={`correct-choice-${q.id}`}
                                      checked={editForm.correct_answer === opt}
                                      onChange={() =>
                                        setEditForm({ ...editForm, correct_answer: opt })
                                      }
                                      title="Mark as correct answer"
                                    />
                                    <input
                                      type="text"
                                      className="form-control"
                                      value={opt}
                                      onChange={(e) => {
                                        const newOpts = [...editForm.options]
                                        const oldVal = newOpts[optIdx]
                                        newOpts[optIdx] = e.target.value
                                        const newCorrect =
                                          editForm.correct_answer === oldVal
                                            ? e.target.value
                                            : editForm.correct_answer
                                        setEditForm({
                                          ...editForm,
                                          options: newOpts,
                                          correct_answer: newCorrect,
                                        })
                                      }}
                                      style={{ flex: 1 }}
                                    />
                                  </div>
                                ))}

                                <label style={{ display: 'block', fontWeight: 600, fontSize: '0.85rem', marginTop: 8, marginBottom: 4 }}>
                                  Explanation
                                </label>
                                <textarea
                                  className="form-control"
                                  rows={2}
                                  value={editForm.explanation}
                                  onChange={(e) =>
                                    setEditForm({ ...editForm, explanation: e.target.value })
                                  }
                                  style={{ width: '100%', marginBottom: 10 }}
                                />

                                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                                  <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={cancelEdit}
                                    disabled={savingQuestion}
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-primary"
                                    onClick={() => handleSaveEdit(q.id)}
                                    disabled={savingQuestion}
                                  >
                                    {savingQuestion ? 'Saving…' : 'Save Question'}
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                  <p style={{ margin: '0 0 6px', fontWeight: 600, fontSize: '0.92rem' }}>
                                    {qIdx + 1}. {q.question}
                                  </p>
                                  <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => startEdit(q)}
                                    title="Edit this question"
                                    style={{ padding: '2px 8px', fontSize: '0.78rem' }}
                                  >
                                    <EditIcon size={12} /> Edit
                                  </button>
                                </div>

                                <div
                                  style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                    gap: 6,
                                    marginTop: 6,
                                  }}
                                >
                                  {q.options?.map((opt, optIdx) => {
                                    const isCorrect = opt === q.correct_answer
                                    return (
                                      <div
                                        key={optIdx}
                                        style={{
                                          padding: '4px 8px',
                                          borderRadius: 4,
                                          fontSize: '0.85rem',
                                          background: isCorrect ? 'rgba(34, 197, 94, 0.12)' : 'transparent',
                                          border: isCorrect ? '1px solid rgba(34, 197, 94, 0.4)' : '1px solid var(--bdr, #e2e8f0)',
                                          color: isCorrect ? '#15803d' : 'inherit',
                                          fontWeight: isCorrect ? 600 : 400,
                                        }}
                                      >
                                        {isCorrect && '✓ '}
                                        {opt}
                                      </div>
                                    )
                                  })}
                                </div>

                                {q.explanation && (
                                  <p
                                    style={{
                                      margin: '6px 0 0',
                                      fontSize: '0.8rem',
                                      color: 'var(--mm)',
                                      fontStyle: 'italic',
                                    }}
                                  >
                                    💡 {q.explanation}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
