import { useMemo, useState } from 'react'
import { getProgress } from '../../api/progress.js'
import { formatNumber } from '../../utils/format.js'
import StatCard from '../ui/StatCard.jsx'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  FlameIcon,
  TrophyIcon,
} from '../ui/icons.jsx'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function parseMonth(month) {
  const match = /^(\d{4})-(\d{2})$/.exec(String(month ?? ''))
  if (match) {
    return { year: Number(match[1]), monthIndex: Number(match[2]) - 1 }
  }

  const now = new Date()
  return { year: now.getFullYear(), monthIndex: now.getMonth() }
}

function formatMonthKey(year, monthIndex) {
  return `${year}-${String(monthIndex + 1).padStart(2, '0')}`
}

function shiftMonth(month, delta) {
  const { year, monthIndex } = parseMonth(month)
  const shifted = new Date(year, monthIndex + delta, 1)
  return formatMonthKey(shifted.getFullYear(), shifted.getMonth())
}

function formatMonthLabel(month) {
  const { year, monthIndex } = parseMonth(month)
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    year: 'numeric',
  }).format(new Date(year, monthIndex, 1))
}

export default function StreakCalendar({
  calendar,
  currentStreak = 0,
  personalBest = 0,
}) {
  const [view, setView] = useState(calendar)
  const [status, setStatus] = useState('ready')
  const [error, setError] = useState('')

  const cells = useMemo(() => {
    if (!view?.month) return []

    const { year, monthIndex } = parseMonth(view.month)
    const daysInMonth = new Date(year, monthIndex + 1, 0).getDate()
    const leadingBlanks = (new Date(year, monthIndex, 1).getDay() + 6) % 7
    const studyDays = new Set(view.study_days ?? [])
    const items = []

    for (let blank = 0; blank < leadingBlanks; blank += 1) {
      items.push({ key: `blank-${blank}`, blank: true })
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const isoDate = `${formatMonthKey(year, monthIndex)}-${String(day).padStart(
        2,
        '0',
      )}`
      const isStudy = studyDays.has(isoDate)
      const isToday = isoDate === view.today
      const label = new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      }).format(new Date(year, monthIndex, day))
      const stateLabel = isStudy
        ? 'study day'
        : isToday
          ? 'today, no study activity yet'
          : 'no study activity'

      items.push({
        key: isoDate,
        day,
        isStudy,
        isToday,
        label: `${label}, ${stateLabel}`,
      })
    }

    return items
  }, [view])

  async function changeMonth(delta) {
    if (!view?.month || status === 'loading') return

    const nextMonth = shiftMonth(view.month, delta)
    setStatus('loading')
    setError('')

    try {
      const progress = await getProgress({ params: { month: nextMonth } })
      const nextCalendar = progress?.streak?.calendar

      if (!nextCalendar?.month) {
        throw new Error('Month data missing from the response.')
      }

      setView(nextCalendar)
      setStatus('ready')
    } catch {
      setStatus('error')
      setError('That month could not be loaded. Check the connection and try again.')
    }
  }

  if (!view?.month) {
    return null
  }

  const isLoading = status === 'loading'

  return (
    <section className="profile-panel profile-calendar" aria-labelledby="streak-calendar-title">
      <div className="sec-head">
        <div>
          <div className="layout-note">Consistency</div>
          <h2 id="streak-calendar-title" className="dash-section-title">
            Streak calendar
          </h2>
        </div>

        <div className="cal-month-nav">
          <button
            type="button"
            className="btn-ghost cal-nav-btn"
            onClick={() => changeMonth(-1)}
            disabled={isLoading}
            aria-label="Previous month"
          >
            <ChevronLeftIcon size={18} />
          </button>
          <span className="cal-month-label" aria-live="polite">
            {formatMonthLabel(view.month)}
          </span>
          <button
            type="button"
            className="btn-ghost cal-nav-btn"
            onClick={() => changeMonth(1)}
            disabled={isLoading}
            aria-label="Next month"
          >
            <ChevronRightIcon size={18} />
          </button>
        </div>
      </div>

      <div className="stat-strip cal-stats">
        <StatCard
          icon={FlameIcon}
          label="Current streak"
          value={`${formatNumber(currentStreak)} ${
            Number(currentStreak) === 1 ? 'day' : 'days'
          }`}
          sub="Keep the flame alive"
          valueClassName="orange"
        />
        <StatCard
          icon={TrophyIcon}
          label="Personal best"
          value={`${formatNumber(personalBest)} ${
            Number(personalBest) === 1 ? 'day' : 'days'
          }`}
          sub="Your longest run"
        />
      </div>

      {error && (
        <p className="cal-error" role="alert">
          {error}
        </p>
      )}

      <div className="cal-weekdays" aria-hidden="true">
        {WEEKDAYS.map((weekday) => (
          <span key={weekday} className="cal-weekday">
            {weekday.slice(0, 1)}
          </span>
        ))}
      </div>

      <div
        className={`cal-grid${isLoading ? ' is-loading' : ''}`.trim()}
        aria-label={`Study days for ${formatMonthLabel(view.month)}`}
        aria-busy={isLoading}
      >
        {cells.map((cell) =>
          cell.blank ? (
            <span
              key={cell.key}
              className="cal-day cal-day-empty"
              aria-hidden="true"
            />
          ) : (
            <span
              key={cell.key}
              className={`cal-day${cell.isStudy ? ' study' : ''}${
                cell.isToday ? ' today' : ''
              }`}
              aria-label={cell.label}
            >
              {cell.day}
            </span>
          ),
        )}
      </div>

      <div className="cal-legend">
        <span>
          <i className="cal-swatch study" aria-hidden="true" />
          Study day
        </span>
        <span>
          <i className="cal-swatch today" aria-hidden="true" />
          Today
        </span>
      </div>
    </section>
  )
}
