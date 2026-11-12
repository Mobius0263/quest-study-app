import { Outlet } from 'react-router-dom'
import TopBar from './TopBar.jsx'
import BottomNav from './BottomNav.jsx'

export default function AppShell() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <TopBar />
      <main id="main-content" className="content-col">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
