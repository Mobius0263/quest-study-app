import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'
import { getProgress } from '../api/progress.js'
import { formatNumber, getDisplayName, getInitials } from '../utils/format.js'
import { toList } from '../utils/dashboard.js'
import PageHeader from '../components/ui/PageHeader.jsx'
import { ErrorState, LoadingState } from '../components/ui/StateViews.jsx'
import ProfileHeader from '../components/profile/ProfileHeader.jsx'
import BadgeGrid from '../components/profile/BadgeGrid.jsx'
import StreakCalendar from '../components/profile/StreakCalendar.jsx'
import { LogOutIcon } from '../components/ui/icons.jsx'

function getProfileErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  return "We couldn't load your profile. Please try again."
}

export default function ProfilePage() {
  const { user, isStudent, logout } = useAuth()
  const [state, setState] = useState({
    status: 'loading',
    progress: null,
    error: '',
  })
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!isStudent) return undefined

    const controller = new AbortController()
    let cancelled = false

    async function loadProfile() {
      setState({ status: 'loading', progress: null, error: '' })

      try {
        const progress = await getProgress({ signal: controller.signal })
        if (cancelled) return
        setState({ status: 'ready', progress, error: '' })
      } catch (error) {
        if (cancelled || error?.code === 'ERR_CANCELED') return
        setState({
          status: 'error',
          progress: null,
          error: getProfileErrorMessage(error),
        })
      }
    }

    loadProfile()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [isStudent, reloadKey])

  const displayName = getDisplayName(user)

  if (!isStudent) {
    return (
      <div className="screen-stack profile-screen">
        <PageHeader
          eyebrow="Your account"
          title="Profile"
          subtitle="Teacher accounts use the teacher workspace for class progress."
        />

        <section className="card profile-teacher-card">
          <span className="profile-teacher-avatar" aria-hidden="true">
            {getInitials(displayName)}
          </span>
          <div className="profile-teacher-copy">
            <div className="layout-note">Teacher account</div>
            <h2>{displayName}</h2>
            <p className="profile-teacher-handle">
              @{user?.username} · Teacher
            </p>
            <p className="profile-teacher-note">
              Level, XP, badges and the streak calendar belong to student
              accounts. Use the Teacher view to create quests and follow your
              class.
            </p>
            <Link to="/teacher" className="btn-primary">
              Open Teacher view
            </Link>
          </div>
        </section>

        <section className="profile-panel profile-account-panel">
          <div className="profile-account-copy">
            <div className="layout-note">Session</div>
            <h3>Signed in as {displayName}</h3>
            <p>@{user?.username} · Teacher</p>
          </div>
          <button
            type="button"
            className="profile-logout-btn"
            onClick={logout}
            aria-label="Log out of Quest Study"
          >
            <LogOutIcon size={16} />
            Log Out
          </button>
        </section>
      </div>
    )
  }

  if (state.status === 'loading') {
    return (
      <div className="screen-stack profile-screen">
        <div className="card">
          <LoadingState label="Loading your profile…" />
        </div>
      </div>
    )
  }

  if (state.status === 'error') {
    return (
      <div className="screen-stack profile-screen">
        <div className="card">
          <ErrorState
            title="Profile unavailable"
            message={state.error}
            onRetry={() => setReloadKey((current) => current + 1)}
          />
        </div>

        <section className="profile-panel profile-account-panel">
          <div className="profile-account-copy">
            <div className="layout-note">Session</div>
            <h3>Signed in as {displayName}</h3>
            <p>@{user?.username}</p>
          </div>
          <button
            type="button"
            className="profile-logout-btn"
            onClick={logout}
            aria-label="Log out of Quest Study"
          >
            <LogOutIcon size={16} />
            Log Out
          </button>
        </section>
      </div>
    )
  }

  const progress = state.progress ?? {}
  const levelInfo = progress.level_info ?? {}
  const streak = progress.streak ?? {}
  const badges = toList(progress.badges)
  const earnedCount = badges.filter((badge) => badge.earned).length
  const calendar = streak.calendar

  return (
    <div className="screen-stack profile-screen">
      <ProfileHeader
        student={progress.student}
        levelInfo={levelInfo}
        streak={streak}
      />

      <section className="profile-panel" aria-labelledby="profile-badges-title">
        <div className="sec-head">
          <div>
            <div className="layout-note">Achievements</div>
            <h2 id="profile-badges-title" className="dash-section-title">
              Badges
            </h2>
          </div>
          <span className="tag">
            {formatNumber(earnedCount)} of {formatNumber(badges.length)} earned
          </span>
        </div>
        <BadgeGrid badges={badges} />
      </section>

      {calendar && (
        <StreakCalendar
          key={calendar.month}
          calendar={calendar}
          currentStreak={streak.current}
          personalBest={streak.longest}
        />
      )}

      <section className="profile-panel profile-account-panel" aria-labelledby="profile-account-title">
        <div className="profile-account-copy">
          <div className="layout-note">Session</div>
          <h3 id="profile-account-title">Signed in as {displayName}</h3>
          <p>@{user?.username} · Student</p>
        </div>
        <button
          type="button"
          className="profile-logout-btn"
          onClick={logout}
          aria-label="Log out of Quest Study"
        >
          <LogOutIcon size={16} />
          Log Out
        </button>
      </section>
    </div>
  )
}
