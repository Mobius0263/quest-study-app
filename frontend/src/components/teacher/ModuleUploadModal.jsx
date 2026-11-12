import { useEffect, useRef, useState } from 'react'
import {
  getModule,
  getModules,
  pasteModule,
  processModule,
  uploadModule,
} from '../../api/modules.js'
import { SUBJECT_NAMES } from '../../utils/subjects.js'
import {
  BookIcon,
  CheckIcon,
  RefreshIcon,
  UploadIcon,
} from '../ui/icons.jsx'

export default function ModuleUploadModal({ onClose, onSuccess, onOpenReview }) {
  const [tab, setTab] = useState('upload') // 'upload' | 'paste' | 'existing'
  const [existingModules, setExistingModules] = useState([])
  const [selectedModuleId, setSelectedModuleId] = useState('')
  const [subject, setSubject] = useState('')
  const [topic, setTopic] = useState('')
  const [file, setFile] = useState(null)
  const [pastedText, setPastedText] = useState('')

  // Generation parameters (§7)
  const [difficulty, setDifficulty] = useState('Medium') // 'Easy' | 'Medium' | 'Hard'
  const [quizQuestions] = useState(5)
  const [bossQuestions, setBossQuestions] = useState(20)

  // Status & Progress (§7)
  const [stage, setStage] = useState('form') // 'form' | 'uploading' | 'processing' | 'done'
  const [currentBatch, setCurrentBatch] = useState(0)
  const [totalBatches, setTotalBatches] = useState(5)
  const [error, setError] = useState('')
  const [createdModuleId, setCreatedModuleId] = useState(null)
  const pollTimerRef = useRef(null)

  useEffect(() => {
    async function loadExisting() {
      try {
        const list = await getModules()
        if (Array.isArray(list)) {
          setExistingModules(list)
        }
      } catch {
        // ignore background fetch error
      }

    }
    loadExisting()

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

  function handleSelectExisting(modId) {
    setSelectedModuleId(modId)
    const found = existingModules.find((m) => String(m.id) === String(modId))
    if (found) {
      setSubject(found.subject || '')
      setTopic(found.topic || found.title || '')
      if (found.difficulty) setDifficulty(found.difficulty)
    }
  }

  async function handleStartGeneration(e) {
    e.preventDefault()
    setError('')

    if (!subject) {
      setError('Please select a subject.')
      return
    }
    if (!topic.trim()) {
      setError('Please enter a topic title.')
      return
    }

    let targetModId = selectedModuleId

    // If uploading new or pasting new
    if (tab === 'upload') {
      if (!file) {
        setError('Please select a PDF file.')
        return
      }
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Only PDF files are supported.')
        return
      }
      setStage('uploading')
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('subject', subject)
        formData.append('topic', topic.trim())
        const res = await uploadModule(formData)
        targetModId = res.module?.id || res.id
        setCreatedModuleId(targetModId)
      } catch (err) {
        setStage('form')
        setError(
          err?.response?.data?.error ||
            err?.response?.data?.detail ||
            'Failed to upload module PDF.'
        )
        return
      }
    } else if (tab === 'paste') {
      if (!pastedText.trim()) {
        setError('Please paste the reading text.')
        return
      }
      setStage('uploading')
      try {
        const res = await pasteModule({
          subject,
          topic: topic.trim(),
          extracted_text: pastedText.trim(),
        })
        targetModId = res.module?.id || res.id
        setCreatedModuleId(targetModId)
      } catch (err) {
        setStage('form')
        setError(
          err?.response?.data?.error ||
            err?.response?.data?.detail ||
            'Failed to save pasted text.'
        )
        return
      }
    }

    if (!targetModId) {
      setError('No module selected.')
      setStage('form')
      return
    }

    // Now trigger batch generation (§7)
    setStage('processing')
    setCurrentBatch(1)
    const quizB = Math.ceil(quizQuestions / 5)
    const bossB = Math.ceil(bossQuestions / 5)
    const totalB = quizB + bossB
    setTotalBatches(totalB)

    // Start progress poller
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    pollTimerRef.current = setInterval(async () => {
      try {
        const mod = await getModule(targetModId)
        const cur = mod.module?.current_batch ?? mod.current_batch
        const tot = mod.module?.total_batches ?? mod.total_batches
        if (cur != null) setCurrentBatch(cur)
        if (tot != null && tot > 0) setTotalBatches(tot)
      } catch {
        // ignore poll errors
      }

    }, 1000)

    try {
      const processRes = await processModule(targetModId, {
        difficulty,
        quiz_questions: quizQuestions,
        boss_questions: bossQuestions,
        subject,
        topic: topic.trim(),
      })
      clearInterval(pollTimerRef.current)
      setStage('done')
      onSuccess?.(processRes)
      if (onOpenReview) {
        onOpenReview(targetModId)
      }
    } catch (err) {
      clearInterval(pollTimerRef.current)
      setStage('form')
      setError(
        err?.response?.data?.error ||
          'Batch generation failed. Please try again or check the backend Ollama service.'
      )
    }
  }

  // Calculate difficulty ramp for preview in UI (§5)
  function getPreviewRamp(diff, numBossBatches) {
    const levels = ['Easy', 'Medium', 'Hard']
    const peakIdx = levels.indexOf(diff)
    const ramp = []
    for (let i = 0; i < numBossBatches; i++) {
      ramp.push(levels[Math.min(i, peakIdx >= 0 ? peakIdx : 1)])
    }
    return ramp
  }

  const numBossBatches = Math.ceil(bossQuestions / 5)
  const previewRamp = getPreviewRamp(difficulty, numBossBatches)

  return (
    <div className="module-modal-content">
      {stage === 'uploading' && (
        <div style={{ textAlign: 'center', padding: '32px 16px' }}>
          <div style={{ marginBottom: 12 }}>
            <UploadIcon size={32} />
          </div>
          <h4>Uploading & Extracting PDF…</h4>
          <p style={{ color: 'var(--mm)', fontSize: '0.9rem' }}>
            Running text extraction and OCR if needed.
          </p>
        </div>
      )}

      {stage === 'processing' && (
        <div style={{ textAlign: 'center', padding: '32px 16px' }}>
          <div style={{ marginBottom: 16 }}>
            <RefreshIcon size={32} />
          </div>
          <h3 style={{ margin: '0 0 8px' }}>
            Generating batch {currentBatch} of {totalBatches}…
          </h3>
          <p style={{ color: 'var(--mm)', fontSize: '0.95rem', marginBottom: 16 }}>
            {currentBatch === 1
              ? 'Generating Batch 1 — Quest Quiz (Easy difficulty, grounded in module)'
              : `Generating Batch ${currentBatch} — Boss Exam (${previewRamp[currentBatch - 2] || difficulty} difficulty)`}
          </p>

          <div
            style={{
              width: '100%',
              maxWidth: 320,
              height: 10,
              background: 'var(--bdr, #e2e8f0)',
              borderRadius: 5,
              overflow: 'hidden',
              margin: '0 auto 16px',
            }}
          >
            <div
              style={{
                width: `${Math.min(100, Math.round((currentBatch / totalBatches) * 100))}%`,
                height: '100%',
                background: 'var(--brand, #3b82f6)',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
          <small style={{ color: 'var(--mm)' }}>
            Each batch of 5 questions is strictly validated and deduplicated.
          </small>
        </div>
      )}

      {stage === 'done' && (
        <div style={{ textAlign: 'center', padding: '32px 16px' }}>
          <div className="card-callout success" style={{ marginBottom: 16 }}>
            <CheckIcon size={24} />
            <div>
              <b>All batches generated successfully!</b>
              <p>Ready for review before publishing.</p>
            </div>
          </div>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              if (onOpenReview && createdModuleId) {
                onOpenReview(createdModuleId)
              } else {
                onClose?.()
              }
            }}
          >
            Open Review Screen
          </button>
        </div>
      )}

      {stage === 'form' && (
        <form onSubmit={handleStartGeneration}>
          <div className="tab-group" style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <button
              type="button"
              className={tab === 'upload' ? 'btn-primary' : 'btn-ghost'}
              onClick={() => {
                setTab('upload')
                setError('')
              }}
            >
              <UploadIcon size={16} />
              Upload PDF
            </button>
            <button
              type="button"
              className={tab === 'paste' ? 'btn-primary' : 'btn-ghost'}
              onClick={() => {
                setTab('paste')
                setError('')
              }}
            >
              <BookIcon size={16} />
              Paste Text
            </button>
            {existingModules.length > 0 && (
              <button
                type="button"
                className={tab === 'existing' ? 'btn-primary' : 'btn-ghost'}
                onClick={() => {
                  setTab('existing')
                  setError('')
                }}
              >
                Existing Module ({existingModules.length})
              </button>
            )}
          </div>

          {error && (
            <div className="form-error" role="alert" style={{ marginBottom: 14 }}>
              {error}
            </div>
          )}

          {tab === 'existing' ? (
            <div className="form-group" style={{ marginBottom: 14 }}>
              <label htmlFor="mod-existing-select">Choose Uploaded Module</label>
              <select
                id="mod-existing-select"
                value={selectedModuleId}
                onChange={(e) => handleSelectExisting(e.target.value)}
                className="form-control"
                required
              >
                <option value="">Select an uploaded module...</option>
                {existingModules.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.subject} — {m.topic || m.title} ({m.page_count || 1} pgs)
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div className="form-group" style={{ marginBottom: 14 }}>
            <label htmlFor="mod-subject">Subject</label>
            <select
              id="mod-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="form-control"
              required
            >
              <option value="">Select subject...</option>
              {SUBJECT_NAMES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 14 }}>
            <label htmlFor="mod-topic">Topic Title</label>
            <input
              id="mod-topic"
              type="text"
              placeholder="e.g. Barisan dan Deret or World War II"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="form-control"
              required
            />
          </div>

          {tab === 'upload' && (
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label htmlFor="mod-file">Module PDF File</label>
              <input
                id="mod-file"
                type="file"
                accept=".pdf,application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="form-control"
                required
              />
            </div>
          )}

          {tab === 'paste' && (
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label htmlFor="mod-text">Lecture Notes / Syllabus Text</label>
              <textarea
                id="mod-text"
                rows={4}
                placeholder="Paste chapter text or notes here..."
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                className="form-control"
                required
              />
            </div>
          )}

          {/* Section 7 Generation Controls */}
          <div
            style={{
              padding: 12,
              background: 'var(--sub-bg, #f8fafc)',
              borderRadius: 'var(--r-sub, 8px)',
              border: '1px solid var(--bdr, #e2e8f0)',
              marginBottom: 18,
            }}
          >
            <h5 style={{ margin: '0 0 10px', fontSize: '0.9rem' }}>Generation Settings</h5>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: 4 }}>
                  Peak Difficulty
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="form-control"
                >
                  <option value="Easy">Easy</option>
                  <option value="Medium">Medium</option>
                  <option value="Hard">Hard</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: 4 }}>
                  Boss Question Count
                </label>
                <select
                  value={bossQuestions}
                  onChange={(e) => setBossQuestions(Number(e.target.value))}
                  className="form-control"
                >
                  <option value={20}>20 questions (4 batches)</option>
                  <option value={30}>30 questions (6 batches)</option>
                  <option value={15}>15 questions (3 batches)</option>
                  <option value={25}>25 questions (5 batches)</option>
                </select>
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--mm)' }}>
              <b>Batch Difficulty Ramp:</b>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                <span className="status-pill prog">Batch 1: Quest (Easy)</span>
                {previewRamp.map((d, idx) => (
                  <span key={idx} className="status-pill prog">
                    Batch {idx + 2}: Boss ({d})
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="modal-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button
              type="button"
              className="btn-ghost"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
            >
              Generate Questions (Batched)
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
