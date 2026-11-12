import { formatNumber, getDisplayName } from '../../utils/format.js'
import { FlameIcon } from '../ui/icons.jsx'
import { HeroSprite } from '../ui/Sprites.jsx'
import XpBar from '../ui/XpBar.jsx'

const RANKS = [
  { minLevel: 10, label: 'Mastermind' },
  { minLevel: 7, label: 'Strategist' },
  { minLevel: 5, label: 'Scholar' },
  { minLevel: 3, label: 'Pathfinder' },
  { minLevel: 1, label: 'Explorer' },
]

function getRank(level) {
  return RANKS.find((rank) => level >= rank.minLevel)?.label ?? 'Explorer'
}

export default function ProfileHeader({ student, levelInfo, streak }) {
  const displayName = getDisplayName(student)
  const level = Number(levelInfo?.level) || 1
  const totalXp = Number(levelInfo?.total_xp) || 0
  const xpToNext = Number(levelInfo?.xp_to_next_level) || 0
  const xpCeiling = Math.max(totalXp + xpToNext, 1)
  const currentStreak = Number(streak?.current) || 0
  const rank = getRank(level)

  return (
    <section className="profile-hero" aria-labelledby="profile-name">
      <div className="profile-hero-art">
        <HeroSprite size={84} label={`${displayName}'s hero`} />
      </div>

      <div className="profile-hero-body">
        <div className="profile-hero-top">
          <div className="profile-identity">
            <div className="layout-note">Your game identity</div>
            <h1 id="profile-name" className="profile-name">
              {displayName}
            </h1>
            <p className="profile-rank">
              Level {formatNumber(level)} · {rank}
              {student?.username && (
                <span className="profile-handle"> @{student.username}</span>
              )}
            </p>
          </div>

          <div
            className="profile-streak-chip"
            aria-label={`Current streak: ${currentStreak} ${
              currentStreak === 1 ? 'day' : 'days'
            }`}
          >
            <FlameIcon size={20} />
            <span>
              <b>{formatNumber(currentStreak)}</b>
              <small>day streak</small>
            </span>
          </div>
        </div>

        <div className="profile-xp-block">
          <div className="profile-xp-line">
            <span>Total XP</span>
            <b>{formatNumber(totalXp)} XP</b>
          </div>
          <XpBar
            value={totalXp}
            max={xpCeiling}
            label={`XP progress to Level ${level + 1}`}
          />
          <div className="profile-xp-sub">
            <span>
              {formatNumber(totalXp)} / {formatNumber(xpCeiling)} XP
            </span>
            <span>
              {formatNumber(xpToNext)} XP to Level {formatNumber(level + 1)}
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
