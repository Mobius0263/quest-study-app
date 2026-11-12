import { getBadgeArt } from '../../utils/badgeArt.js'

export default function BadgeGrid({ badges = [] }) {
  if (badges.length === 0) {
    return (
      <p className="profile-empty-note">
        No badges have been defined yet. Check back after your next quest.
      </p>
    )
  }

  return (
    <div className="badge-grid">
      {badges.map((badge) => {
        const { Icon, color } = getBadgeArt(badge)
        const earned = Boolean(badge.earned)

        return (
          <article
            key={badge.id ?? badge.code}
            className={`badge-grid-item${earned ? '' : ' locked'}`}
            aria-label={`${badge.title}, ${earned ? 'earned' : 'locked'}`}
          >
            <span
              className="badge-icon"
              style={{ background: color }}
              aria-hidden="true"
            >
              <Icon size={22} />
            </span>
            <b>{badge.title}</b>
            <span className="badge-state">{earned ? 'Earned' : 'Locked'}</span>
          </article>
        )
      })}
    </div>
  )
}
