import { Link } from 'react-router-dom'
import { TrophyIcon } from '../ui/icons.jsx'
import { formatNumber } from '../../utils/format.js'

const FAILURE_REASONS = {
  player_hp: 'Your HP reached zero — the boss outlasted you.',
  timer: 'The 1 hour ran out — time expiry counts as a fail.',
  questions_exhausted:
    'The 20 questions ran out with the boss still standing.',
}

function breakdown(result) {
  const xp = result?.xp || {}
  return {
    perAnswer: Number(xp.per_answer) || 0,
    streakBonus: Number(xp.streak_bonus) || 0,
    winBonus: Number(xp.win_bonus) || 0,
    total: Number(xp.total ?? result?.xp_earned) || 0,
  }
}

function retriesLabel(retries) {
  return `${retries} retr${retries === 1 ? 'y' : 'ies'} left`
}

export default function BossResultPanel({
  result,
  bossName,
  onRetry,
  retrying = false,
  retryError = '',
}) {
  if (!result) return null

  const won = result.status === 'won' || result.passed
  const xp = breakdown(result)
  const badges = Array.isArray(result.newly_awarded_badges)
    ? result.newly_awarded_badges
    : []
  const retries = Math.max(0, Number(result.retries_left) || 0)
  const attemptNumber = Number(result.attempt_number) || 1
  const attemptsTotal = Number(result.attempts_total) || 3

  if (won) {
    return (
      <section className="end-panel win boss-result-panel" aria-live="polite">
        <div className="boss-result-kicker">Victory</div>
        <h2>Boss defeated!</h2>
        <p className="boss-result-copy">
          You answered {formatNumber(result.correct_count)} correctly and{' '}
          {bossName || 'the boss'} crumbles. Attempt {attemptNumber} of{' '}
          {attemptsTotal}.
        </p>

        <div className="boss-xp-breakdown" aria-label="XP breakdown">
          <div>
            <span>Per-answer XP</span>
            <b>+{formatNumber(xp.perAnswer)} XP</b>
          </div>
          <div>
            <span>Streak bonus XP</span>
            <b>+{formatNumber(xp.streakBonus)} XP</b>
          </div>
          <div>
            <span>Win bonus</span>
            <b>+{formatNumber(xp.winBonus)} XP</b>
          </div>
          <div className="total">
            <span>Total XP</span>
            <b>{formatNumber(xp.total)} XP</b>
          </div>
        </div>

        <p className="boss-result-score">
          Score {formatNumber(result.score)}% · {formatNumber(result.correct_count)}{' '}
          correct of {formatNumber(result.answered_count)} answered
        </p>

        {badges.length > 0 && (
          <div className="boss-badge-earned">
            <TrophyIcon size={18} />
            <span>
              Badge earned: <b>{badges.join(', ')}</b>
            </span>
          </div>
        )}

        <div className="boss-result-actions">
          <Link to="/" className="btn-primary">
            Back to Dashboard
          </Link>
        </div>
      </section>
    )
  }

  const reason =
    FAILURE_REASONS[result.failure_reason] ||
    'The boss exam ended before the boss was defeated.'

  return (
    <section className="end-panel lose boss-result-panel" aria-live="polite">
      <div className="boss-result-kicker">Defeat</div>
      <h2>Exam failed</h2>
      <p className="boss-result-copy">{reason}</p>

      <div className="boss-result-facts">
        <div className="boss-result-fact">
          <span>Correct answers</span>
          <b>
            {formatNumber(result.correct_count)} /{' '}
            {formatNumber(result.answered_count)}
          </b>
        </div>
        <div className="boss-result-fact">
          <span>Score</span>
          <b>{formatNumber(result.score)}%</b>
        </div>
        <div className="boss-result-fact">
          <span>Boss HP left</span>
          <b>
            {formatNumber(result.boss_hp)} / {formatNumber(result.boss_hp_max)}
          </b>
        </div>
        <div className="boss-result-fact">
          <span>Your HP</span>
          <b>
            {formatNumber(result.player_hp)} /{' '}
            {formatNumber(result.player_hp_max)}
          </b>
        </div>
        <div className="boss-result-fact">
          <span>XP from this attempt</span>
          <b>{formatNumber(xp.total)} XP</b>
        </div>
        <div className="boss-result-fact">
          <span>Attempt</span>
          <b>
            {attemptNumber} of {attemptsTotal}
          </b>
        </div>
      </div>

      {retries > 0 ? (
        <p className="boss-retry-note">
          You can retry with a fresh timer, full HP and a new question order.
        </p>
      ) : (
        <p className="boss-no-retries">
          <b>No retries left — 3 attempts used.</b> There is no fourth attempt.
        </p>
      )}

      {retryError && (
        <div className="form-error" role="alert">
          {retryError}
        </div>
      )}

      <div className="boss-result-actions">
        {retries > 0 && (
          <button
            type="button"
            className="btn-danger"
            onClick={onRetry}
            disabled={retrying}
          >
            {retrying
              ? 'Starting retry…'
              : `Retry Boss · ${retriesLabel(retries)}`}
          </button>
        )}
        <Link to="/" className="btn-ghost">
          Back to Dashboard
        </Link>
      </div>
    </section>
  )
}
