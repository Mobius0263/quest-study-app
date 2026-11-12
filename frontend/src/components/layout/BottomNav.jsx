import { NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.js'
import { HomeIcon, MapIcon, ShieldIcon, UserIcon } from '../ui/icons.jsx'

const BASE_ITEMS = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/quests', label: 'Quests', icon: MapIcon },
  { to: '/profile', label: 'Profile', icon: UserIcon },
]

export default function BottomNav() {
  const { isTeacher } = useAuth()
  const items = isTeacher
    ? [
        ...BASE_ITEMS.slice(0, 2),
        { to: '/teacher', label: 'Teach', icon: ShieldIcon },
        BASE_ITEMS[2],
      ]
    : BASE_ITEMS

  return (
    <nav className="bottom-nav" aria-label="Mobile navigation">
      <div className="bottom-nav-inner">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? 'active' : undefined)}
          >
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
