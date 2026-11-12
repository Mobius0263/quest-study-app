function getOptionState(option, selected, feedback) {
  if (!feedback) return selected === option ? 'selected' : ''
  if (option === feedback.correct_answer) return 'correct'
  if (option === selected && !feedback.correct) return 'wrong'
  return 'disabled'
}

function FeedbackMessage({ feedback }) {
  if (feedback.correct) {
    const bonus = Number(feedback.streak_bonus) || 0
    return (
      <>
        <b>Hit! −{Number(feedback.damage) || 10} boss HP</b>
        <span className="boss-feedback-detail">
          +{Number(feedback.xp_gained) || 5} XP this answer
          {bonus > 0 ? `, including +${bonus} streak bonus` : ''} · Streak ×{' '}
          {Number(feedback.current_streak) || 0}
        </span>
        {feedback.explanation && (
          <p className="quiz-feedback-explanation">{feedback.explanation}</p>
        )}
      </>
    )
  }

  const playerDamage = Number(feedback.player_damage) || 0
  return (
    <>
      <b>
        {playerDamage > 0
          ? `Wrong again — you lost ${playerDamage} HP`
          : 'First wrong in a row is free'}
      </b>
      <span className="boss-feedback-detail">
        Correct answer: {feedback.correct_answer} ·{' '}
        {playerDamage > 0
          ? `Your HP dropped by ${playerDamage}.`
          : 'No player HP lost this time.'}
      </span>
      {feedback.explanation && (
        <p className="quiz-feedback-explanation">{feedback.explanation}</p>
      )}
    </>
  )
}

export default function BossQuestionCard({
  question,
  questionNumber,
  total = 20,
  subject,
  selected,
  onSelect,
  onCheck,
  checking,
  feedback,
  onNext,
  error,
  answeredCount = 0,
}) {
  const options = Array.isArray(question?.options) ? question.options : []
  const dots = Array.from({ length: total }, (_, index) => index)

  return (
    <section
      className="card quiz-question-card boss-question-card"
      aria-labelledby="boss-question-title"
    >
      <div className="quiz-question-topline boss-question-topline">
        <span className="boss-q-topic">
          Question {questionNumber} · {subject || 'Boss exam'}
        </span>
        {question?.type === 'true_false' && (
          <span className="tag revision">True / False</span>
        )}
        <span className="boss-q-note">Order shuffled for this attempt</span>
      </div>

      <h2 id="boss-question-title" className="quiz-question-text">
        {question?.question}
      </h2>

      <div className="answer-grid" role="group" aria-label="Answer options">
        {options.map((option, index) => {
          const state = getOptionState(option, selected, feedback)
          const disabled = Boolean(feedback) || checking

          return (
            <button
              key={`${option}-${index}`}
              type="button"
              className={`answer-btn ${state}`.trim()}
              onClick={() => onSelect(option)}
              disabled={disabled}
              aria-pressed={selected === option}
            >
              <span className="letter">{String.fromCharCode(65 + index)}</span>
              <span>{option}</span>
            </button>
          )
        })}
      </div>

      {feedback && (
        <div
          className={`quiz-feedback ${feedback.correct ? 'correct' : 'wrong'}`}
          role="status"
        >
          <FeedbackMessage feedback={feedback} />
        </div>
      )}

      {error && (
        <div className="form-error boss-answer-error" role="alert">
          {error}
        </div>
      )}

      <div className="quiz-actions">
        {!feedback ? (
          <button
            type="button"
            className="btn-primary btn-block"
            onClick={onCheck}
            disabled={!selected || checking}
          >
            {checking ? 'Checking…' : 'Check Answer'}
          </button>
        ) : feedback.finished ? (
          <button type="button" className="btn-primary btn-block" disabled>
            Finishing fight…
          </button>
        ) : (
          <button type="button" className="btn-primary btn-block" onClick={onNext}>
            Next Question
          </button>
        )}
      </div>

      <div className="boss-progress">
        <div className="q-dots" aria-hidden="true">
          {dots.map((index) => {
            const done = index < answeredCount
            const now = !feedback && index === answeredCount
            return (
              <span
                key={index}
                className={`q-dot ${done ? 'done' : ''} ${now ? 'now' : ''}`.trim()}
              />
            )
          })}
        </div>
        <span className="boss-progress-label">
          {Math.min(answeredCount, total)} of {total} answered
        </span>
      </div>
    </section>
  )
}
