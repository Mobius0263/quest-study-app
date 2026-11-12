import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'
import { getProgress } from '../api/progress.js'
import { getQuests } from '../api/quests.js'
import { getQuizzes } from '../api/quizzes.js'
import { formatNumber, getDisplayName } from '../utils/format.js'
import {
  getCompletedQuestIdsToday,
  getDailyGoal,
  getNextBossQuiz,
  getPathQuests,
  isCompletedQuest,
  toList,
} from '../utils/dashboard.js'
import { isSameLocalDay } from '../utils/dates.js'
import { HeroSprite } from '../components/ui/Sprites.jsx'
import StatStrip from '../components/ui/StatStrip.jsx'
import StatCard from '../components/ui/StatCard.jsx'
import XpBar from '../components/ui/XpBar.jsx'
import PathNode from '../components/ui/PathNode.jsx'
import { ErrorState, LoadingState } from '../components/ui/StateViews.jsx'
import BossTeaser from '../components/dashboard/BossTeaser.jsx'
import BadgeRow from '../components/dashboard/BadgeRow.jsx'
import { FlameIcon, StarIcon, TargetIcon, ZapIcon } from '../components/ui/icons.jsx'

const INITIAL_DATA = {
  status: 'loading',
  progress: null,
  quests: [],
  quizzes: [],
  now: null,
  error: '',
}

function getGreeting(reference) {
  const hour = reference.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function getDashboardErrorMessage(error) {
  if (!error?.response) {
    return 'Cannot reach the server. Check that the backend is running and try again.'
  }
  return "We couldn't load your dashboard. Please try again."
}

function buildHeroLine({ pathCount, activeCount, dueTodayCount }) {
  if (pathCount === 0) {
    return "No quests on today's path yet. Add a Revision Quest or open the quest board."
  }

  if (activeCount === 0) {
    return "All of today's quests are done. The trail is clear — nice work."
  }

  if (dueTodayCount > 0) {
    const label = dueTodayCount === 1 ? 'quest' : 'quests'
    return `${dueTodayCount} ${label} due today. Follow the trail — one node at a time.`
  }

  const label = activeCount === 1 ? 'quest' : 'quests'
  return `${activeCount} ${label} on your path, nearest deadline first.`
}

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState(INITIAL_DATA)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    async function loadDashboard() {
      setData((current) => ({ ...current, status: 'loading', error: '' }))

      try {
        const [progress, quests, quizzes] = await Promise.all([
          getProgress({ signal: controller.signal }),
          getQuests({}, { signal: controller.signal }),
          getQuizzes({}, { signal: controller.signal }),
        ])

        if (cancelled) return

        setData({
          status: 'ready',
          progress,
          quests: toList(quests),
          quizzes: toList(quizzes),
          now: new Date(),
          error: '',
        })
      } catch (error) {
        if (cancelled || error?.code === 'ERR_CANCELED') return

        setData((current) => ({
          ...current,
          status: 'error',
          error: getDashboardErrorMessage(error),
        }))
      }
    }

    loadDashboard()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [reloadKey])

  const derived = useMemo(() => {
    if (data.status !== 'ready' || !data.now) return null

    const now = data.now
    const completedTodayIds = getCompletedQuestIdsToday(data.progress, now)
    const pathQuests = getPathQuests(data.quests, completedTodayIds, now)
    const dailyGoal = getDailyGoal(data.quests, completedTodayIds, now)
    const nextBoss = getNextBossQuiz(data.quizzes, pathQuests)
    const activeCount = pathQuests.filter(
      (quest) => !isCompletedQuest(quest),
    ).length
    const dueTodayCount = pathQuests.filter(
      (quest) => !isCompletedQuest(quest) && isSameLocalDay(quest.due_date, now),
    ).length

    return { pathQuests, dailyGoal, nextBoss, activeCount, dueTodayCount }
  }, [data])

  if (data.status === 'loading') {
    return (
      <div className="screen-stack">
        <div className="card">
          <LoadingState label="Loading your dashboard…" />
        </div>
      </div>
    )
  }

  if (data.status === 'error') {
    return (
      <div className="screen-stack">
        <div className="card">
          <ErrorState
            title="Dashboard unavailable"
            message={data.error}
            onRetry={() => setReloadKey((current) => current + 1)}
          />
        </div>
      </div>
    )
  }

  if (!derived) return null

  const progress = data.progress ?? {}
  const levelInfo = progress.level_info ?? {}
  const streak = progress.streak ?? {}
  const badges = toList(progress.badges)

  const totalXp = Number(levelInfo.total_xp) || 0
  const level = Number(levelInfo.level) || 1
  const xpToNext = Number(levelInfo.xp_to_next_level) || 0
  const xpCeiling = Math.max(totalXp + xpToNext, 1)

  const currentStreak = Number(streak.current) || 0
  const longestStreak = Number(streak.longest) || 0
  const streakLabel = `${formatNumber(currentStreak)} day${currentStreak === 1 ? '' : 's'}`

  const goalValue =
    derived.dailyGoal.target > 0
      ? `${derived.dailyGoal.done} of ${derived.dailyGoal.target}`
      : `${derived.dailyGoal.done} done`
  const goalSub =
    derived.dailyGoal.target > 0 ? 'quests done today' : 'No quests due today'

  const displayName = getDisplayName(user)
  const firstName = displayName.split(/\s+/)[0] || 'Student'
  const heroLine = buildHeroLine({
    pathCount: derived.pathQuests.length,
    activeCount: derived.activeCount,
    dueTodayCount: derived.dueTodayCount,
  })

  return (
    <div className="screen-stack dash-screen">
      <section className="dash-hero" aria-labelledby="dashboard-greeting">
        <HeroSprite size={64} label={`${displayName}'s hero`} />
        <div className="dash-hero-copy">
          <div className="layout-note">Today's goal</div>
          <h1 id="dashboard-greeting" className="dash-greeting">
            {getGreeting(data.now)}, {firstName}!
          </h1>
          <p className="dash-hero-line">{heroLine}</p>
        </div>
      </section>

      <StatStrip>
        <StatCard
          icon={StarIcon}
          label="Level"
          value={formatNumber(level)}
          sub="Scholar rank"
        />
        <StatCard
          icon={ZapIcon}
          label="XP"
          value={formatNumber(totalXp)}
          sub={`${formatNumber(xpToNext)} XP to Level ${level + 1}`}
        >
          <XpBar
            value={totalXp}
            max={xpCeiling}
            label={`XP progress to Level ${level + 1}`}
          />
        </StatCard>
        <StatCard
          icon={FlameIcon}
          label="Streak"
          value={streakLabel}
          sub={`Personal best: ${formatNumber(longestStreak)}`}
          valueClassName="orange"
        />
        <StatCard
          icon={TargetIcon}
          label="Daily goal"
          value={goalValue}
          sub={goalSub}
        >
          <XpBar
            value={derived.dailyGoal.done}
            max={derived.dailyGoal.target || 1}
            label="Daily goal progress"
          />
        </StatCard>
      </StatStrip>

      <section className="dash-section" aria-labelledby="today-path-title">
        <div className="sec-head">
          <div>
            <div className="layout-note">Learning path</div>
            <h2 id="today-path-title" className="dash-section-title">
              Today's Path
            </h2>
          </div>
          {derived.pathQuests.length > 0 && (
            <span className="tag xp">
              {derived.pathQuests.length}{' '}
              {derived.pathQuests.length === 1 ? 'quest' : 'quests'}
            </span>
          )}
        </div>

        {derived.pathQuests.length > 0 ? (
          <div className="path-list">
            {derived.pathQuests.map((quest) => (
              <PathNode
                key={quest.id}
                quest={quest}
                onClick={(selectedQuest) =>
                  navigate(`/quests/${selectedQuest.id}`)
                }
              />
            ))}
          </div>
        ) : (
          <div className="card dash-empty">
            <HeroSprite size={72} label="Hero waiting for a quest" />
            <div className="dash-empty-copy">
              <h2>Your path is clear</h2>
              <p>
                No quests on today's path yet. Add a Revision Quest or pick one
                from the quest board.
              </p>
              <Link to="/quests" className="btn-primary">
                Open quest board
              </Link>
            </div>
          </div>
        )}
      </section>

      {derived.nextBoss && <BossTeaser quiz={derived.nextBoss} />}

      <BadgeRow badges={badges} />
    </div>
  )
}
