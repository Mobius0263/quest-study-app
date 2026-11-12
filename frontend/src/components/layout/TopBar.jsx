import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.js'
import { getDisplayName, getInitials } from '../../utils/format.js'
import { ShieldIcon } from '../ui/icons.jsx'

const BASE_NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/quests', label: 'Quests' },
  { to: '/profile', label: 'Profile' },
]

export default function TopBar() {
  const { user, isTeacher } = useAuth()
  const displayName = getDisplayName(user)
  const navItems = isTeacher
    ? [...BASE_NAV.slice(0, 2), { to: '/teacher', label: 'Teacher' }, BASE_NAV[2]]
    : BASE_NAV

  return (
    <header className="topbar">
      <Link to="/" className="topbar-logo" aria-label="Quest Study home">
        <span className="topbar-crest" aria-hidden="true">
          <ShieldIcon size={16} />
        </span>
        Quest Study
      </Link>

      <nav className="topbar-nav" aria-label="Main navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => (isActive ? 'active' : undefined)}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Link
        to="/profile"
        className="topbar-avatar"
        aria-label={`Profile for ${displayName}`}
        title={displayName}
      >
        {getInitials(displayName)}
      </Link>
    </header>
  )
}
