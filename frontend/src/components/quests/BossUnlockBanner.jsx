import { Link } from 'react-router-dom'
import { GolemSprite } from '../ui/Sprites.jsx'
import { LockIcon, SwordIcon } from '../ui/icons.jsx'

export default function BossUnlockBanner({ quiz, unlocked }) {
  if (!quiz) return null

  const bossName = quiz.boss_name || quiz.title || 'Boss quiz'
  const topic = quiz.title || quiz.subject || 'the boss quiz'

  if (!unlocked) {
    return (
      <div className="boss-card-locked detail-boss-locked">
        <span className="detail-boss-lock-icon" aria-hidden="true">
          <LockIcon size={22} />
        </span>
        <div className="detail-boss-locked-copy">
          <b>Boss locked</b>
          <span>Finish this quest to unlock {bossName}.</span>
        </div>
      </div>
    )
  }

  return (
    <section className="boss-unlocked" aria-label="Boss unlocked">
      <GolemSprite size="small" label={`${bossName} boss sprite`} />
      <div className="boss-unlocked-copy">
        <div className="layout-note">Boss unlocked</div>
        <h2>{bossName}</h2>
        <p>
          {topic} · You finished the study material — the boss quiz is open.
        </p>
      </div>
      <Link to={`/boss/${quiz.id}`} className="btn-danger boss-unlocked-action">
        <SwordIcon size={16} />
        Fight the Boss
      </Link>
    </section>
  )
}
