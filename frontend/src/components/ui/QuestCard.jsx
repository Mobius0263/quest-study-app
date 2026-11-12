import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { normalizeQuest, STATUS_LABELS } from '../../utils/quests.js'
import { formatDueDate } from '../../utils/format.js'
import {
  ClockIcon,
  EditIcon,
  MoreIcon,
  TrashIcon,
  ZapIcon,
} from './icons.jsx'
import SubjectTile from './SubjectTile.jsx'
import Tag from './Tag.jsx'
import GemRow from './GemRow.jsx'
import StatusPill from './StatusPill.jsx'

function QuestCardMenu({ quest, onEdit, onDelete, showViewButton }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const buttonRef = useRef(null)
  const firstItemRef = useRef(null)
  const canManage = Boolean(onEdit || onDelete)

  useEffect(() => {
    if (!open) return undefined

    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  useEffect(() => {
    if (open) firstItemRef.current?.focus()
  }, [open])

  function choose(handler) {
    setOpen(false)
    handler?.(quest)
  }

  const location = useLocation()

  return (
    <div
      className={`quest-card-actions ${showViewButton ? 'with-view' : ''}`.trim()}
      ref={rootRef}
    >
      {showViewButton && (
        <Link
          to={`/quests/${quest.id}`}
          state={{ boardSearch: location.search }}
          className="btn-ghost quest-card-view"
          aria-label={`View ${quest.title}`}
        >
          View
        </Link>
      )}

      {canManage && (
        <>
          <button
            ref={buttonRef}
            type="button"
            className="card-menu-button"
            onClick={() => setOpen((current) => !current)}
            aria-label={`Manage ${quest.title}`}
            aria-haspopup="menu"
            aria-expanded={open}
          >
            <MoreIcon size={18} />
          </button>

          {open && (
            <div
              className="card-menu"
              role="menu"
              aria-label={`${quest.title} actions`}
            >
              <button
                ref={firstItemRef}
                type="button"
                className="card-menu-item"
                role="menuitem"
                onClick={() => choose(onEdit)}
              >
                <EditIcon size={15} />
                Edit
              </button>
              <button
                type="button"
                className="card-menu-item danger"
                role="menuitem"
                onClick={() => choose(onDelete)}
              >
                <TrashIcon size={15} />
                Delete
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function QuestCard({
  quest: rawQuest,
  onEdit,
  onDelete,
  showViewButton = false,
  className = '',
}) {
  const quest = normalizeQuest(rawQuest)
  const location = useLocation()
  const canManage = Boolean(onEdit || onDelete)
  const statusLabel = STATUS_LABELS[quest.status] || 'Not started'

  return (
    <article
      className={`quest-card ${className}`.trim()}
      data-quest-id={quest.id}
    >
      <Link
        to={`/quests/${quest.id}`}
        state={{ boardSearch: location.search }}
        className="quest-card-open"
        aria-label={`${quest.subject}: ${quest.title}. ${quest.typeLabel}. ${quest.difficulty}. ${quest.xp} XP. ${formatDueDate(quest.dueDate)}. ${statusLabel}.`}
      >
        <SubjectTile subject={quest.subject} />

        <span className="quest-card-main">
          <span className="quest-card-title">
            {quest.subject} — {quest.title}
          </span>

          <span className="quest-card-meta">
            <Tag variant={quest.typeKey}>{quest.typeLabel}</Tag>
            {(rawQuest?.is_ungrounded ?? quest?.is_ungrounded) && (
              <Tag variant="warning" title="Not grounded in an uploaded module">
                Ungrounded
              </Tag>
            )}
            <Tag variant="xp">
              <GemRow difficulty={quest.difficulty} />
            </Tag>

            <Tag variant="xp">
              <ZapIcon size={11} />
              {quest.xp} XP
            </Tag>
            <span className="quest-card-due">
              <ClockIcon size={12} />
              {formatDueDate(quest.dueDate)}
            </span>
            <StatusPill status={quest.status} />
          </span>
        </span>
      </Link>

      {(canManage || showViewButton) && (
        <QuestCardMenu
          quest={quest}
          onEdit={onEdit}
          onDelete={onDelete}
          showViewButton={showViewButton}
        />
      )}
    </article>
  )
}
