import {
  CheckIcon,
  FlameIcon,
  ShieldIcon,
  StarIcon,
  SwordIcon,
  TrophyIcon,
  ZapIcon,
} from '../components/ui/icons.jsx'

/**
 * Presentation only: badge titles, colours and earned state come from the API.
 * The icon key chooses the medallion glyph, and Badge.color supplies its fill.
 */
const BADGE_ICONS = {
  flag: CheckIcon,
  shield: ShieldIcon,
  flame: FlameIcon,
  zap: ZapIcon,
  swords: SwordIcon,
  crown: TrophyIcon,
  star: StarIcon,
  award: TrophyIcon,
  trophy: TrophyIcon,
}

const FALLBACK_COLORS = {
  flag: '#f59e0b',
  shield: '#2563eb',
  flame: '#ff9600',
  zap: '#a855f7',
  swords: '#e5484d',
  crown: '#7c3aed',
  star: '#2563eb',
  award: '#f59e0b',
}

export function getBadgeArt(badge) {
  const icon = badge?.icon
  return {
    Icon: BADGE_ICONS[icon] || TrophyIcon,
    color: badge?.color || FALLBACK_COLORS[icon] || 'var(--ma)',
  }
}
