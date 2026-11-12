import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.js'
import { getTeacherProgress } from '../api/progress.js'
import {
  createQuest,
  deleteQuest,
  getQuests,
  updateQuest,
} from '../api/quests.js'
import { getQuizzes } from '../api/quizzes.js'
import { deleteModule, getModules } from '../api/modules.js'
import { toList } from '../utils/dashboard.js'
import { formatNumber, getDisplayName, getInitials } from '../utils/format.js'
import StatCard from '../components/ui/StatCard.jsx'
import QuestCard from '../components/ui/QuestCard.jsx'
import QuestForm from '../components/quests/QuestForm.jsx'
import Modal from '../components/ui/Modal.jsx'
import TeacherQuizForm from '../components/teacher/TeacherQuizForm.jsx'
import DraftReviewSection from '../components/teacher/DraftReviewSection.jsx'
import ModuleUploadModal from '../components/teacher/ModuleUploadModal.jsx'
import ModuleReviewModal from '../components/teacher/ModuleReviewModal.jsx'
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/ui/StateViews.jsx'
import {
  BookIcon,
  CheckIcon,
  MapIcon,
  PlusIcon,
  StarIcon,
  SwordIcon,
  TargetIcon,
  TrashIcon,
  UploadIcon,
} from '../components/ui/icons.jsx'

const INITIAL_DATA = {
  status: 'loading',
  progress: null,
  quests: [],
  draftQuizzes: [],
  modules: [],
  error: '',
}


const STUDENT_STATUS = {
  'on-track': { label: 'On track', className: 'on-track' },
  'almost-there': { label: 'Almost there', className: 'almost-there' },
  'needs-nudge': { label: 'Needs a nudge', className: 'needs-nudge' },
}

function getLoadErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  return "We couldn't load the teacher workspace. Please try again."
}

function getDeleteErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check your connection and try again.'
  }
  return "We couldn't delete this quest. Please try again."
}

function getStudentName(student) {
  const name = [student?.first_name, student?.last_name]
    .filter(Boolean)
    .join(' ')
    .trim()
  return name || student?.username || 'Student'
}

function getStatusMeta(student) {
  return STUDENT_STATUS[student?.status] || STUDENT_STATUS['needs-nudge']
}

function formatPercent(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '0'
  return Number.isInteger(number) ? String(number) : number.toFixed(1)
}

function formatScore(value) {
  const number = Number(value)
  if (value == null || !Number.isFinite(number)) return '—'
  return Number.isInteger(number) ? String(number) : number.toFixed(1)
}

function getStudentCountLine(count) {
  return `${count} ${count === 1 ? 'student' : 'students'} · Create quests and quizzes, follow progress and scores.`
}

export default function TeacherPage() {
  const { user } = useAuth()
  const [data, setData] = useState(INITIAL_DATA)
  const [reloadKey, setReloadKey] = useState(0)
  const [questModal, setQuestModal] = useState(null)
  const [quizOpen, setQuizOpen] = useState(false)
  const [moduleModalOpen, setModuleModalOpen] = useState(false)
  const [reviewModuleId, setReviewModuleId] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [deleteModuleTarget, setDeleteModuleTarget] = useState(null)
  const [deletingModule, setDeletingModule] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    async function loadWorkspace() {
      try {
        const [progress, quests, draftQuizzes, modules] = await Promise.all([
          getTeacherProgress({ signal: controller.signal }),
          getQuests({}, { signal: controller.signal }),
          getQuizzes({ status: 'draft' }, { signal: controller.signal }),
          getModules({}, { signal: controller.signal }).catch(() => []),
        ])
        if (cancelled) return
        setData({
          status: 'ready',
          progress,
          quests: toList(quests),
          draftQuizzes: toList(draftQuizzes),
          modules: toList(modules),
          error: '',
        })
      } catch (error) {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setData({
          status: 'error',
          progress: null,
          quests: [],
          draftQuizzes: [],
          modules: [],
          error: getLoadErrorMessage(error),
        })
      }
    }


    loadWorkspace()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [reloadKey])

  const summary = data.progress?.class_summary ?? {}
  const students = data.progress?.students ?? []
  const className = summary.class_name || 'Your class'
  const draftQuests = useMemo(
    () =>
      data.quests.filter(
        (quest) =>
          String(quest.creator) === String(user?.id) && quest.status === 'draft',
      ),
    [data.quests, user?.id],
  )
  const publishedTeacherQuests = useMemo(
    () =>
      data.quests.filter(
        (quest) =>
          String(quest.creator) === String(user?.id) && quest.status !== 'draft',
      ),
    [data.quests, user?.id],
  )
  const teacherQuests = publishedTeacherQuests
  const teacherName = getDisplayName(user)

  function refresh() {
    setReloadKey((current) => current + 1)
  }

  function openCreateQuest() {
    setQuestModal({ mode: 'create', quest: null })
    setNotice('')
  }

  function openEditQuest(quest) {
    setQuestModal({ mode: 'edit', quest })
    setNotice('')
  }

  function closeQuestModal() {
    setQuestModal(null)
  }

  async function handleQuestSubmit(payload) {
    if (questModal?.mode === 'edit' && questModal.quest?.id != null) {
      const updated = await updateQuest(questModal.quest.id, payload)
      setNotice(
        `${updated.quest_type === 'revision' ? 'Revision' : 'Assignment'} Quest updated.`,
      )
    } else {
      const created = await createQuest(payload)
      setNotice(
        `${created.quest_type === 'revision' ? 'Revision' : 'Assignment'} Quest created.`,
      )
    }

    closeQuestModal()
    refresh()
  }

  function openDelete(quest) {
    setDeleteTarget(quest)
    setDeleteError('')
    setNotice('')
  }

  async function handleDelete() {
    if (!deleteTarget) return

    setDeleting(true)
    setDeleteError('')
    try {
      await deleteQuest(deleteTarget.id)
      setDeleteTarget(null)
      setNotice('Quest deleted.')
      refresh()
    } catch (error) {
      setDeleteError(getDeleteErrorMessage(error))
    } finally {
      setDeleting(false)
    }
  }

  function openDeleteModule(module) {
    setDeleteModuleTarget(module)
    setNotice('')
  }

  async function handleDeleteModule() {
    if (!deleteModuleTarget) return

    setDeletingModule(true)
    try {
      await deleteModule(deleteModuleTarget.id)
      setNotice(`Module "${deleteModuleTarget.topic || deleteModuleTarget.title}" and its drafts deleted.`)
      setDeleteModuleTarget(null)
      refresh()
    } catch (err) {
      setNotice(err?.response?.data?.error || err?.response?.data?.detail || 'Failed to delete module.')
    } finally {
      setDeletingModule(false)
    }
  }

  function openQuiz() {
    setQuizOpen(true)
    setNotice('')
  }

  function handleQuizPublished() {
    setQuizOpen(false)
    setNotice('Boss quiz published and live for students.')
    refresh()
  }

  if (data.status === 'loading') {
    return (
      <div className="screen-stack teacher-screen">
        <div className="card">
          <LoadingState label="Loading the teacher workspace…" />
        </div>
      </div>
    )
  }

  if (data.status === 'error') {
    return (
      <div className="screen-stack teacher-screen">
        <div className="card">
          <ErrorState
            title="Teacher workspace unavailable"
            message={data.error}
            onRetry={refresh}
          />
        </div>
      </div>
    )
  }

  const studentCount = Number(summary.total_students) || students.length

  return (
    <div className="screen-stack teacher-screen">
      <section className="teacher-hero" aria-labelledby="teacher-class-name">
        <div className="teacher-hero-copy">
          <div className="layout-note">Teacher workspace</div>
          <h1 id="teacher-class-name" className="teacher-class-name">
            {className}
          </h1>
          <p>{getStudentCountLine(studentCount)}</p>
        </div>

        <div className="teacher-identity">
          <span className="teacher-identity-avatar" aria-hidden="true">
            {getInitials(teacherName)}
          </span>
          <span className="teacher-identity-copy">
            <b>{teacherName}</b>
            <small>Teacher</small>
          </span>
        </div>
      </section>

      <div className="teacher-create-row">
        <button type="button" className="btn-primary" onClick={openCreateQuest}>
          <PlusIcon size={16} />
          Create Quest
        </button>
        <button
          type="button"
          className="btn-ghost teacher-create-quiz"
          onClick={openQuiz}
        >
          <SwordIcon size={16} />
          Create Boss Quiz
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={() => setModuleModalOpen(true)}
        >
          <UploadIcon size={16} />
          Upload Module
        </button>
      </div>

      {notice && (
        <div className="board-notice" role="status">
          {notice}
        </div>
      )}

      <div className="stat-strip teacher-stats">
        <StatCard
          icon={TargetIcon}
          label="Active quests"
          value={summary.active_quests ?? 0}
          sub={`${summary.assignment_quests ?? 0} Assignment · ${summary.revision_quests ?? 0} Revision`}
        />
        <StatCard
          icon={CheckIcon}
          label="Avg completion"
          value={`${formatPercent(summary.average_completion)}%`}
          sub="across the class"
        />
        <StatCard
          icon={SwordIcon}
          label="Boss quizzes"
          value={summary.boss_quizzes ?? 0}
          sub={`${summary.live_boss_quizzes ?? 0} live`}
        />
        <StatCard
          icon={StarIcon}
          label="Avg quiz score"
          value={formatScore(summary.average_last_boss_score)}
          sub="last boss fight"
        />
      </div>

      {summary.subject_quest_counts && Object.keys(summary.subject_quest_counts).length > 0 && (
        <div
          className="card teacher-subject-counts"
          style={{
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexWrap: 'wrap',
          }}
        >
          <span className="layout-note" style={{ fontWeight: 700, margin: 0 }}>
            Quests by Subject:
          </span>
          {Object.entries(summary.subject_quest_counts).map(([sub, count]) => (
            <span
              key={sub}
              className="status-pill prog"
              style={{ fontSize: '0.8rem', padding: '2px 8px' }}
            >
              {sub}: <b>{count}</b>
            </span>
          ))}
        </div>
      )}

      <section
        className="teacher-section"
        aria-labelledby="teacher-students-title"
      >
        <div className="sec-head">
          <h4 id="teacher-students-title">Student progress</h4>
          <span className="teacher-section-note">Read-only roster</span>
        </div>

        {students.length === 0 ? (
          <div className="card board-state">
            <EmptyState
              icon={MapIcon}
              title="No students yet"
              message="Students appear here as soon as their accounts join the class."
            />
          </div>
        ) : (
          <div className="teacher-table" role="table" aria-label="Student progress">
            <div className="t-row head" role="row">
              <span role="columnheader">Student</span>
              <span role="columnheader">Quests</span>
              <span className="hide-m" role="columnheader">
                XP
              </span>
              <span className="hide-m" role="columnheader">
                Last quiz
              </span>
              <span role="columnheader">Status</span>
            </div>

            {students.map((student) => {
              const name = getStudentName(student)
              const status = getStatusMeta(student)
              return (
                <div className="t-row" role="row" key={student.student_id}>
                  <span className="who" role="cell">
                    <span className="t-avatar" aria-hidden="true">
                      {getInitials(name)}
                    </span>
                    <span className="t-name">{name}</span>
                  </span>
                  <span className="t-quests tabular" role="cell">
                    {student.completed_quests_count ?? 0} /{' '}
                    {student.total_quests_count ?? 0}
                  </span>
                  <span className="hide-m tabular" role="cell">
                    {formatNumber(student.total_xp)} XP
                  </span>
                  <span className="hide-m t-last-quiz tabular" role="cell">
                    {formatScore(student.last_quiz_score)}
                  </span>
                  <span role="cell">
                    <span
                      className={`status-pill teacher-status ${status.className}`.trim()}
                    >
                      {status.label}
                    </span>
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <DraftReviewSection
        draftQuests={draftQuests}
        draftQuizzes={data.draftQuizzes}
        onEditQuest={openEditQuest}
        onOpenModuleReview={(modId) => setReviewModuleId(modId)}
        onRefresh={refresh}
        onNotice={setNotice}
      />

      <section
        className="teacher-section"
        aria-labelledby="teacher-quests-title"
      >
        <div className="sec-head">
          <h4 id="teacher-quests-title">Quests you&apos;ve set</h4>
          <span className="teacher-section-note">
            {teacherQuests.length} {teacherQuests.length === 1 ? 'quest' : 'quests'}
          </span>
        </div>

        {teacherQuests.length === 0 ? (
          <div className="card board-state">
            <EmptyState
              icon={MapIcon}
              title="No quests set yet"
              message="Create an Assignment or Revision Quest and it will appear here for your class."
              action={
                <button
                  type="button"
                  className="btn-primary"
                  onClick={openCreateQuest}
                >
                  <PlusIcon size={16} />
                  Create Quest
                </button>
              }
            />
          </div>
        ) : (
          <div className="board-list teacher-quest-list">
            {teacherQuests.map((quest) => (
              <QuestCard
                key={quest.id}
                quest={quest}
                showViewButton
                onEdit={openEditQuest}
                onDelete={openDelete}
              />
            ))}
          </div>
        )}
      </section>

      {data.modules && data.modules.length > 0 && (
        <section
          className="teacher-section"
          aria-labelledby="teacher-modules-title"
        >
          <div className="sec-head">
            <h4 id="teacher-modules-title">Uploaded Modules & Grounding</h4>
            <span className="teacher-section-note">
              {data.modules.length} {data.modules.length === 1 ? 'module' : 'modules'}
            </span>
          </div>

          <div className="board-list" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {data.modules.map((mod) => (
              <div
                key={mod.id}
                className="card"
                style={{
                  padding: '12px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 10,
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="subject-pill">{mod.subject}</span>
                    <span
                      className={`status-pill ${
                        mod.status === 'published' ? 'comp' : 'prog'
                      }`}
                    >
                      {mod.status === 'published'
                        ? 'Published'
                        : mod.status === 'ready_for_review'
                        ? 'Ready for Review'
                        : 'Draft'}
                    </span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--mm)' }}>
                      {mod.page_count || 1} pgs · Difficulty: {mod.difficulty || 'Medium'}
                    </span>
                  </div>
                  <h4 style={{ margin: 0, fontSize: '0.98rem' }}>
                    {mod.topic || mod.title}
                  </h4>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => openDeleteModule(mod)}
                    style={{ color: '#ef4444' }}
                    title="Delete module and its drafts"
                  >
                    <TrashIcon size={15} />
                    Delete
                  </button>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setReviewModuleId(mod.id)}
                    title="Review draft questions for this module"
                  >
                    <BookIcon size={15} />
                    Review Questions
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}


      {questModal && (
        <Modal
          title={
            questModal.mode === 'edit' ? 'Edit Quest' : 'Create Quest'
          }
          eyebrow="Teacher quest"
          description="Set the title, subject, type, difficulty and deadline. There are no file fields."
          onClose={closeQuestModal}
        >
          <QuestForm
            key={questModal.quest?.id ?? 'create'}
            quest={questModal.mode === 'edit' ? questModal.quest : null}
            allowType
            contextLabel="quest"
            onSubmit={handleQuestSubmit}
            onCancel={closeQuestModal}
          />
        </Modal>
      )}

      {quizOpen && (
        <Modal
          title="Create Boss Quiz"
          eyebrow="AI draft"
          description="Generate 20 questions, review the stored result, then publish when it is ready for students."
          onClose={() => setQuizOpen(false)}
        >
          <TeacherQuizForm
            className={className}
            onCancel={() => setQuizOpen(false)}
            onPublished={handleQuizPublished}
          />
        </Modal>
      )}

      {moduleModalOpen && (
        <Modal
          title="Module PDF & Notes Pipeline"
          eyebrow="Teacher source material"
          description="Upload a syllabus PDF or paste notes to extract text with OCR and generate grounded question batches."
          onClose={() => setModuleModalOpen(false)}
        >
          <ModuleUploadModal
            onClose={() => setModuleModalOpen(false)}
            onSuccess={() => {
              setNotice('Module processed and ready for review.')
              refresh()
            }}
            onOpenReview={(modId) => {
              setModuleModalOpen(false)
              setReviewModuleId(modId)
              refresh()
            }}
          />
        </Modal>
      )}

      {reviewModuleId && (
        <ModuleReviewModal
          moduleId={reviewModuleId}
          onClose={() => {
            setReviewModuleId(null)
            refresh()
          }}
          onPublished={() => {
            setNotice('Module questions and quizzes published!')
            refresh()
          }}
          onDeleted={() => {
            setNotice('Module and draft questions discarded.')
            setReviewModuleId(null)
            refresh()
          }}
        />
      )}

      {deleteModuleTarget && (
        <Modal
          title="Delete module & drafts?"
          eyebrow="Module management"
          onClose={() => {
            if (!deletingModule) setDeleteModuleTarget(null)
          }}
          closeDisabled={deletingModule}
        >
          <div className="modal-body-copy">
            <p>
              <b>{deleteModuleTarget.topic || deleteModuleTarget.title}</b> and all associated draft questions, quest drafts, and boss exams will be permanently deleted.
              This cannot be undone.
            </p>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setDeleteModuleTarget(null)}
              disabled={deletingModule}
              data-autofocus
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={handleDeleteModule}
              disabled={deletingModule}
            >
              {deletingModule ? 'Deleting…' : 'Delete module'}
            </button>
          </div>
        </Modal>
      )}

      {deleteTarget && (
        <Modal
          title="Delete quest?"
          eyebrow="Teacher quest"
          onClose={() => {
            if (!deleting) setDeleteTarget(null)
          }}
          closeDisabled={deleting}
        >
          <div className="modal-body-copy">
            <p>
              <b>{deleteTarget.title}</b> will be removed for every student.
              This cannot be undone.
            </p>
          </div>

          {deleteError && (
            <div className="form-error" role="alert">
              {deleteError}
            </div>
          )}

          <div className="modal-actions">
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setDeleteTarget(null)}
              disabled={deleting}
              data-autofocus
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? 'Deleting…' : 'Delete quest'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
