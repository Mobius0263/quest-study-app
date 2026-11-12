import { DIFFICULTY_META } from '../../utils/quests.js'
import { GemIcon } from './icons.jsx'

export default function GemRow({ difficulty = 'Medium', showLabel = true }) {
  const meta = DIFFICULTY_META[difficulty] || DIFFICULTY_META.Medium

  return (
    <span className="gem-row" title={`${difficulty} difficulty`}>
      {[0, 1, 2].map((index) => (
        <GemIcon
          key={index}
          className={index < meta.gems ? undefined : 'gem-off'}
        />
      ))}
      {showLabel && <span className="gem-label">{difficulty}</span>}
    </span>
  )
}
