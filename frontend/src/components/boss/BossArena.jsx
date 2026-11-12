import { GolemSprite } from '../ui/Sprites.jsx'

export default function BossArena({
  bossName,
  quote,
  defeated = false,
  hitKey = 0,
  damage = null,
}) {
  const name = bossName || 'The Boss'
  const taunt = quote || 'Twenty questions. One hour. Show me what you know.'
  const spriteClass = defeated ? 'defeated' : hitKey > 0 ? 'hit' : ''

  return (
    <section className="boss-stage boss-arena" aria-label={`Arena: ${name}`}>
      {damage?.text && (
        <span key={damage.key} className="dmg-pop show" aria-hidden="true">
          {damage.text}
        </span>
      )}
      <div className="speech-bubble">
        “{taunt}” — {name}
      </div>
      <GolemSprite
        key={`golem-${hitKey}-${defeated ? 'down' : 'up'}`}
        size="large"
        className={spriteClass}
        label={`${name} boss sprite`}
      />
      <div className="boss-name-pill">{name.toUpperCase()} · BOSS EXAM</div>
    </section>
  )
}
