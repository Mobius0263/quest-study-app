import { Link } from 'react-router-dom'
import { CheckIcon, TargetIcon } from '../ui/icons.jsx'

export default function QuizResultPanel({
  result,
  questId,
  boardSearch = '',
  onRetry,
}) {
  const total = Number(result.total_questions) || 0
  const correct = Number(result.correct_count) || 0
  const score = Number(result.score) || 0
  const best = result.best_attempt
  const bestCorrect = Number(best?.correct_count ?? correct) || 0
  const passingScore = Number(result.passing_score) || 80

  return (
    <section
      className={`card quiz-result ${result.passed ? 'pass' : 'retry'}`.trim()}
      aria-live="polite"
    >
      <span className={`quiz-result-icon ${result.passed ? 'pass' : 'retry'}`.trim()} aria-hidden="true">
        {result.passed ? <CheckIcon size={28} /> : <TargetIcon size={28} />}
      </span>

      <h2>{result.passed ? 'Quiz passed!' : 'Not quite yet'}</h2>

      <p className="quiz-result-score">
        {correct} / {total} · {score}% · {result.passed ? 'Passed' : 'Not passed'}
      </p>

      <p className="quiz-result-best">
        Pass line: {passingScore}% · Best attempt: {bestCorrect} / {total}
      </p>

      <p className="quiz-result-copy">
        {result.passed
          ? 'The quiz step is now ticked — you can complete the quest.'
          : 'The quiz step stays unticked and the quest stays incomplete. Retry as often as you like; your best attempt counts.'}
      </p>

      <div className="quiz-result-actions">
        <Link
          to={`/quests/${questId}`}
          state={{ boardSearch }}
          className="btn-primary"
        >
          Back to quest
        </Link>
        <button type="button" className="btn-ghost" onClick={onRetry}>
          Retry quiz
        </button>
      </div>
    </section>
  )
}
