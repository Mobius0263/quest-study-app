import { formatNumber } from '../../utils/format.js'
import { getLevelBar } from '../../utils/questDetail.js'
import StatusPill from '../ui/StatusPill.jsx'
import SubjectTile from '../ui/SubjectTile.jsx'
import Tag from '../ui/Tag.jsx'
import XpBar from '../ui/XpBar.jsx'
import { StarIcon } from '../ui/icons.jsx'
import RewardPop from './RewardPop.jsx'

function getCreatorName(quest) {
  const details = quest?.creator_details
  if (!details) return ''
  const fullName = [details.first_name, details.last_name]
    .filter(Boolean)
    .join(' ')
    .trim()
  return fullName || details.username || ''
}

export default function QuestDetailHeader({ quest, levelInfo, reward }) {
  const typeKey = quest.quest_type === 'revision' ? 'revision' : 'assignment'
  const typeLabel = typeKey === 'revision' ? 'Revision Quest' : 'Assignment Quest'
  const creatorName = getCreatorName(quest)
  const levelBar = levelInfo ? getLevelBar(levelInfo) : null

  return (
    <header className="card detail-head">
      <RewardPop show={Boolean(reward)} xp={reward?.xp ?? 0} />

      <div className="detail-head-main">
        <SubjectTile subject={quest.subject} size={64} iconSize={32} />

        <div className="detail-head-copy">
          <div className="detail-head-tags">
            <Tag variant={typeKey}>{typeLabel}</Tag>
            <span className="detail-subject">{quest.subject}</span>
          </div>

          <h1 className="detail-title">{quest.title}</h1>

          <div className="detail-head-meta">
            <StatusPill status={quest.status} />
            {creatorName && <span>Set by {creatorName}</span>}
          </div>
        </div>
      </div>

      {levelBar && (
        <div className="detail-xp">
          <div className="detail-xp-head">
            <span>
              <StarIcon size={14} />
              Level {formatNumber(levelBar.level)}
            </span>
            <b>{formatNumber(levelBar.totalXp)} XP</b>
          </div>
          <XpBar
            value={levelBar.value}
            max={levelBar.max}
            label={`XP progress to Level ${levelBar.level + 1}`}
          />
        </div>
      )}
    </header>
  )
}
