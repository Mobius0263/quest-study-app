import { Link } from 'react-router-dom'
import { getBadgeArt } from '../../utils/badgeArt.js'
import { TrophyIcon } from '../ui/icons.jsx'

const MAX_DASHBOARD_BADGES = 4

export default function BadgeRow({ badges = [] }) {
  const visibleBadges = badges
    .filter((badge) => badge.earned)
    .slice(0, MAX_DASHBOARD_BADGES)

  return (
    <section className="dash-section" aria-labelledby="dashboard-badges-title">
      <div className="sec-head">
        <div>
          <div className="layout-note">Achievements</div>
          <h2 id="dashboard-badges-title" className="dash-section-title">
            Badges
          </h2>
        </div>
        <Link to="/profile" className="dash-text-link">
          View profile
        </Link>
      </div>

      {visibleBadges.length > 0 ? (
        <div className="badge-row">
          {visibleBadges.map((badge) => {
            const { Icon, color } = getBadgeArt(badge)

            return (
              <Link
                key={badge.id ?? badge.code}
                to="/profile"
                className="badge-item"
                aria-label={`${badge.title} badge, earned`}
              >
                <span
                  className="badge-icon"
                  style={{ background: color }}
                  aria-hidden="true"
                >
                  <Icon size={22} />
                </span>
                <b>{badge.title}</b>
                <span>Earned</span>
              </Link>
            )
          })}
        </div>
      ) : (
        <div className="dash-badge-empty">
          <span
            className="badge-icon"
            style={{ background: 'var(--ma)' }}
            aria-hidden="true"
          >
            <TrophyIcon size={22} />
          </span>
          <div>
            <b>Your first badge is waiting</b>
            <span>Complete a quest or pass a boss fight to earn one.</span>
          </div>
          <Link to="/quests" className="btn-ghost btn-sm">
            Browse quests
          </Link>
        </div>
      )}
    </section>
  )
}
