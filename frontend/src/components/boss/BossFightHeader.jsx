import { ClockIcon, SwordIcon } from '../ui/icons.jsx'

function formatClock(totalSeconds) {
  const safe = Math.max(0, Math.floor(Number(totalSeconds) || 0))
  const minutes = Math.floor(safe / 60)
  const seconds = safe % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function retriesLabel(attempt) {
  const retries = Math.max(0, Number(attempt?.retries_left) || 0)
  return `${retries} retr${retries === 1 ? 'y' : 'ies'} left`
}

export default function BossFightHeader({ quiz, attempt, timeLeft }) {
  const bossName = quiz?.boss_name || quiz?.title || 'Boss exam'
  const total = Number(attempt?.total_questions) || 20
  const questionNumber = Math.min(
    total,
    Math.max(1, Number(attempt?.question_number) || 1),
  )
  const attemptsTotal = Number(attempt?.attempts_total) || 3
  const attemptNumber = Number(attempt?.attempt_number) || 1
  const lowTime = Number(timeLeft) <= 300

  return (
    <header className="card boss-fight-head">
      <div className="boss-fight-top">
        <div className="boss-fight-id">
          <span className="boss-face" aria-hidden="true">
            <SwordIcon size={20} />
          </span>
          <div className="boss-fight-copy">
            <div className="layout-note">Boss exam</div>
            <h1 id="boss-fight-title">{bossName}</h1>
            <p>
              {quiz?.subject || 'Boss exam'} · Question {questionNumber} of{' '}
              {total}
            </p>
          </div>
        </div>

        <div className="boss-fight-meta">
          <span className="attempt-pill">
            Attempt {attemptNumber} of {attemptsTotal} · {retriesLabel(attempt)}
          </span>
          <span
            className={`timer-pill ${lowTime ? 'low' : ''}`.trim()}
            aria-label={`Time left ${formatClock(timeLeft)}`}
          >
            <ClockIcon size={14} />
            {formatClock(timeLeft)}
          </span>
        </div>
      </div>
    </header>
  )
}
