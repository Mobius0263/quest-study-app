import { normalizeQuest } from '../../utils/quests.js'
import { formatDueDate } from '../../utils/format.js'
import SubjectTile from './SubjectTile.jsx'
import Tag from './Tag.jsx'
import GemRow from './GemRow.jsx'
import StatusPill from './StatusPill.jsx'
import { ClockIcon } from './icons.jsx'

export default function PathNode({ quest: rawQuest, onClick }) {
  const quest = normalizeQuest(rawQuest)
  const isDone = quest.status === 'done'

  return (
    <button
      type="button"
      className="path-node"
      onClick={onClick ? () => onClick(quest) : undefined}
      data-quest-id={quest.id}
      aria-label={`${quest.title}. ${quest.difficulty}. ${quest.xp} XP. ${isDone ? 'Done' : 'Start'}`}
    >
      <SubjectTile subject={quest.subject} variant="dot" />

      <span className="path-node-main">
        <span className="quest-card-title">{quest.title}</span>
        <span className="quest-card-meta">
          <GemRow difficulty={quest.difficulty} />
          <Tag variant="xp">{quest.xp} XP</Tag>
          <span className="quest-card-due">
            <ClockIcon size={12} />
            {formatDueDate(quest.dueDate)}
          </span>
          <StatusPill status={quest.status} />
        </span>
      </span>

      <span className="btn-primary btn-sm">{isDone ? 'Done' : 'Start'}</span>
    </button>
  )
}
