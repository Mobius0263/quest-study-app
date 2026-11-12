import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'
import {
  createQuest,
  deleteQuest,
  getQuests,
  updateQuest,
} from '../api/quests.js'
import { toList } from '../utils/dashboard.js'
import {
  buildQuestQueryParams,
  getBoardCounts,
  getBoardSubjectOptions,
  sortBoardQuests,
  STATUS_FILTER_OPTIONS,
  TYPE_FILTER_OPTIONS,
} from '../utils/questBoard.js'
import { getSubjectConfig } from '../utils/subjects.js'
import PageHeader from '../components/ui/PageHeader.jsx'
import FilterChips from '../components/quests/FilterChips.jsx'
import QuestBoard from '../components/quests/QuestBoard.jsx'
import QuestForm from '../components/quests/QuestForm.jsx'
import Modal from '../components/ui/Modal.jsx'
import { PlusIcon } from '../components/ui/icons.jsx'

const TYPES = new Set(['assignment', 'revision'])
const STATUSES = new Set(['not-started', 'in-progress', 'done'])

const INITIAL_SUMMARY = {
  status: 'loading',
  quests: [],
  error: '',
  loadedAt: null,
}

const INITIAL_LIST = {
  status: 'loading',
  quests: [],
  error: '',
}

function getBoardLoadErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  return "We couldn't load the quest board. Please try again."
}

function getDeleteErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check your connection and try again.'
  }
  return "We couldn't delete this Revision Quest. Please try again."
}

function getHeaderSubtitle(summary, counts) {
  if (summary.status === 'loading') return 'Loading your quests…'
  if (summary.status === 'error') return 'Quest counts are unavailable right now.'
  if (counts.total === 0) return 'No quests yet. Start with your own Revision Quest.'

  const questLabel = counts.total === 1 ? 'quest' : 'quests'
  return `${counts.total} ${questLabel} · ${counts.dueToday} due today · ${counts.done} done`
}

export default function QuestBoardPage() {
  const { user, isStudent } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [summary, setSummary] = useState(INITIAL_SUMMARY)
  const [list, setList] = useState(INITIAL_LIST)
  const [reloadKey, setReloadKey] = useState(0)
  const [formMode, setFormMode] = useState(null)
  const [editingQuest, setEditingQuest] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [notice, setNotice] = useState('')

  const rawType = searchParams.get('type')
  const rawSubject = searchParams.get('subject')
  const rawStatus = searchParams.get('status')
  const typeFilter = TYPES.has(rawType) ? rawType : 'all'
  const subjectFilter =
    rawSubject && rawSubject !== 'all' ? rawSubject : 'all'
  const statusFilter = STATUSES.has(rawStatus) ? rawStatus : 'all'
  const hasActiveFilters =
    typeFilter !== 'all' || subjectFilter !== 'all' || statusFilter !== 'all'

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    getQuests({}, { signal: controller.signal })
      .then((data) => {
        if (cancelled) return
        setSummary({
          status: 'ready',
          quests: toList(data),
          error: '',
          loadedAt: new Date(),
        })
      })
      .catch((error) => {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setSummary((current) => ({
          ...current,
          status: 'error',
          error: getBoardLoadErrorMessage(error),
        }))
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [reloadKey])

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    getQuests(
      buildQuestQueryParams({
        type: typeFilter,
        subject: subjectFilter,
        status: statusFilter,
      }),
      { signal: controller.signal },
    )
      .then((data) => {
        if (cancelled) return
        setList({ status: 'ready', quests: toList(data), error: '' })
      })
      .catch((error) => {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setList({
          status: 'error',
          quests: [],
          error: getBoardLoadErrorMessage(error),
        })
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [typeFilter, subjectFilter, statusFilter, reloadKey])

  const counts = useMemo(() => {
    if (summary.status !== 'ready' || !summary.loadedAt) {
      return { total: 0, dueToday: 0, done: 0 }
    }
    return getBoardCounts(summary.quests, summary.loadedAt)
  }, [summary.status, summary.quests, summary.loadedAt])

  const sortedQuests = useMemo(
    () => sortBoardQuests(list.quests, statusFilter),
    [list.quests, statusFilter],
  )

  const subjectOptions = useMemo(() => {
    const subjects = getBoardSubjectOptions(summary.quests, subjectFilter)
    return [
      { value: 'all', label: 'All' },
      ...subjects.map((subject) => {
        const { Icon } = getSubjectConfig(subject)
        return { value: subject, label: subject, icon: Icon }
      }),
    ]
  }, [summary.quests, subjectFilter])

  const boardStatus =
    summary.status === 'error' || list.status === 'error'
      ? 'error'
      : summary.status === 'loading' || list.status === 'loading'
        ? 'loading'
        : 'ready'
  const boardError = list.error || summary.error
  const headerSubtitle = getHeaderSubtitle(summary, counts)

  function showListLoading() {
    setList((current) => ({ ...current, status: 'loading', error: '' }))
  }

  function refreshBoard() {
    setSummary((current) => ({ ...current, status: 'loading', error: '' }))
    showListLoading()
    setReloadKey((current) => current + 1)
  }

  function setFilter(key, value) {
    const next = new URLSearchParams(searchParams)
    if (!value || value === 'all') next.delete(key)
    else next.set(key, value)
    if (next.toString() === searchParams.toString()) return

    showListLoading()
    setSearchParams(next, { replace: true })
    setNotice('')
  }

  function clearFilters() {
    const next = new URLSearchParams(searchParams)
    next.delete('type')
    next.delete('subject')
    next.delete('status')
    if (next.toString() === searchParams.toString()) return

    showListLoading()
    setSearchParams(next, { replace: true })
    setNotice('')
  }

  function openCreate() {
    setEditingQuest(null)
    setFormMode('create')
    setNotice('')
  }

  function openEdit(quest) {
    setEditingQuest(quest)
    setFormMode('edit')
    setNotice('')
  }

  function closeForm() {
    setFormMode(null)
    setEditingQuest(null)
  }

  function openDelete(quest) {
    setDeleteTarget(quest)
    setDeleteError('')
    setNotice('')
  }

  async function handleFormSubmit(payload) {
    if (formMode === 'edit' && editingQuest?.id != null) {
      await updateQuest(editingQuest.id, payload)
      setNotice('Revision Quest updated.')
    } else {
      await createQuest(payload)
      setNotice('Revision Quest created.')
    }

    closeForm()
    refreshBoard()
  }

  async function handleDelete() {
    if (!deleteTarget) return

    setDeleting(true)
    setDeleteError('')
    try {
      await deleteQuest(deleteTarget.id)
      setDeleteTarget(null)
      setNotice('Revision Quest deleted.')
      refreshBoard()
    } catch (error) {
      setDeleteError(getDeleteErrorMessage(error))
    } finally {
      setDeleting(false)
    }
  }

  function canManageQuest(quest) {
    return (
      isStudent &&
      quest?.quest_type === 'revision' &&
      String(quest.creator) === String(user?.id)
    )
  }

  return (
    <div className="screen-stack board-screen">
      <PageHeader
        eyebrow="Calm list layout"
        title="Quest Board"
        subtitle={headerSubtitle}
        actions={
          isStudent ? (
            <button type="button" className="btn-primary" onClick={openCreate}>
              <PlusIcon size={16} />
              New Revision Quest
            </button>
          ) : null
        }
      />

      <section className="board-filters" aria-label="Quest filters">
        <FilterChips
          label="Type"
          options={TYPE_FILTER_OPTIONS}
          value={typeFilter}
          onChange={(value) => setFilter('type', value)}
        />
        <FilterChips
          label="Subject"
          options={subjectOptions}
          value={subjectFilter}
          onChange={(value) => setFilter('subject', value)}
        />
        <FilterChips
          label="Status"
          options={STATUS_FILTER_OPTIONS}
          value={statusFilter}
          onChange={(value) => setFilter('status', value)}
        />
      </section>

      <QuestBoard
        quests={sortedQuests}
        status={boardStatus}
        error={boardError}
        totalCount={
          summary.status === 'ready' ? counts.total : Number.NaN
        }
        hasActiveFilters={hasActiveFilters}
        notice={notice}
        onRetry={refreshBoard}
        onClearFilters={clearFilters}
        onCreate={openCreate}
        canCreate={isStudent}
        canManage={canManageQuest}
        onEdit={openEdit}
        onDelete={openDelete}
      />

      {formMode && (
        <Modal
          title={
            formMode === 'edit' ? 'Edit Revision Quest' : 'New Revision Quest'
          }
          eyebrow="Revision Quest"
          description="Set the title, subject, difficulty and deadline. Assignment Quests stay read-only."
          onClose={closeForm}
        >
          <QuestForm
            key={editingQuest?.id ?? 'create'}
            quest={formMode === 'edit' ? editingQuest : null}
            onSubmit={handleFormSubmit}
            onCancel={closeForm}
          />
        </Modal>
      )}

      {deleteTarget && (
        <Modal
          title="Delete Revision Quest?"
          eyebrow="Revision Quest"
          onClose={() => {
            if (!deleting) setDeleteTarget(null)
          }}
          closeDisabled={deleting}
        >
          <div className="modal-body-copy">
            <p>
              <b>{deleteTarget.title}</b> will be removed from your board. This
              cannot be undone.
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
