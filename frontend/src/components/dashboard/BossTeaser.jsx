import { Link } from 'react-router-dom'
import { formatNumber } from '../../utils/format.js'
import {
  formatQuizDuration,
  getQuizQuestionCount,
} from '../../utils/dashboard.js'
import { GolemSprite } from '../ui/Sprites.jsx'
import XpBar from '../ui/XpBar.jsx'
import { SwordIcon } from '../ui/icons.jsx'

export default function BossTeaser({ quiz }) {
  const bossName = quiz.boss_name || 'Boss'
  const topic = quiz.ai_topic || quiz.subject || quiz.title
  const bossHp = Number(quiz.boss_hp) > 0 ? Number(quiz.boss_hp) : 100
  const rewardXp = Number(quiz.reward_xp) || 0
  const questionCount = getQuizQuestionCount(quiz)
  const speech =
    quiz.content?.boss?.quote ||
    quiz.description ||
    'Your next boss exam is ready when you are.'

  const facts = ['Boss exam']
  if (questionCount) facts.push(`${questionCount} questions`)
  facts.push(formatQuizDuration(quiz.time_limit_seconds))
  facts.push(`${formatNumber(bossHp)} HP boss`)
  if (rewardXp > 0) facts.push(`Win bonus +${formatNumber(rewardXp)} XP`)

  return (
    <section className="boss-card dash-boss" aria-labelledby="boss-teaser-title">
      <div className="dash-boss-stage">
        <p className="dash-boss-speech">{speech}</p>
        <GolemSprite size="small" label={`${bossName} boss sprite`} />
        <span className="dash-boss-name">{bossName}</span>
      </div>

      <div className="dash-boss-copy">
        <div>
          <div className="layout-note dash-boss-kicker">Boss Fight</div>
          <h2 id="boss-teaser-title" className="dash-boss-title">
            {quiz.title}
          </h2>
          <p className="dash-boss-sub">
            {topic} · {facts.join(' · ')}
          </p>
        </div>

        <div className="dash-boss-hp">
          <div className="dash-boss-hp-label">
            <span>Boss HP</span>
            <span>
              {formatNumber(bossHp)} / {formatNumber(bossHp)}
            </span>
          </div>
          <XpBar
            value={bossHp}
            max={bossHp}
            variant="hp"
            label={`${bossName} boss HP`}
          />
        </div>

        <Link to={`/boss/${quiz.id}`} className="btn-danger dash-boss-start">
          <SwordIcon size={16} />
          Start Boss Fight
        </Link>
      </div>
    </section>
  )
}
