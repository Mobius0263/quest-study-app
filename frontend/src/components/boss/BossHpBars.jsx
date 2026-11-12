import { FlameIcon, ZapIcon } from '../ui/icons.jsx'
import { formatNumber } from '../../utils/format.js'
import XpBar from '../ui/XpBar.jsx'

export default function BossHpBars({
  bossHp = 100,
  bossHpMax = 100,
  playerHp = 100,
  playerHpMax = 100,
  streak = 0,
  xpEarned = 0,
}) {
  return (
    <section className="boss-hp-grid" aria-label="Fight status">
      <div className="boss-hp-block">
        <div className="boss-hp-label">
          <span>Boss HP</span>
          <b>
            {formatNumber(bossHp)} / {formatNumber(bossHpMax)}
          </b>
        </div>
        <XpBar
          value={bossHp}
          max={bossHpMax}
          variant="hp boss"
          label="Boss HP"
        />
      </div>

      <div className="boss-hp-block">
        <div className="boss-hp-label">
          <span>Your HP</span>
          <b>
            {formatNumber(playerHp)} / {formatNumber(playerHpMax)}
          </b>
        </div>
        <XpBar
          value={playerHp}
          max={playerHpMax}
          variant="player boss"
          label="Your HP"
        />
      </div>

      <div className="boss-fight-pills">
        <span className="streak-pill">
          <FlameIcon size={13} />
          Streak × {formatNumber(streak)}
        </span>
        <span className="attempt-pill boss-xp-pill">
          <ZapIcon size={13} />
          {formatNumber(xpEarned)} XP this attempt
        </span>
      </div>

      <p className="boss-rules-line">
        Correct: −10 boss HP and +5 XP · Streak of 3+: +5 bonus XP · First
        wrong in a row is free, then −10 your HP.
      </p>
    </section>
  )
}
