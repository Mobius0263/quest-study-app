import XpBar from '../ui/XpBar.jsx'

function getOptionState(option, selected, feedback) {
  if (!feedback) return selected === option ? 'selected' : ''
  if (option === feedback.correct_answer) return 'correct'
  if (option === selected && !feedback.correct) return 'wrong'
  return 'disabled'
}

export default function QuizQuestionCard({
  question,
  questionNumber,
  total,
  selected,
  onSelect,
  onCheck,
  checking,
  feedback,
  onContinue,
  isLast,
  submitting,
  checkError,
}) {
  const options = Array.isArray(question?.options) ? question.options : []

  return (
    <section className="card quiz-question-card" aria-labelledby="quiz-question-title">
      <div className="quiz-question-topline">
        <span>
          Question {questionNumber} of {total}
        </span>
        {question?.type === 'true_false' && (
          <span className="tag revision">True / False</span>
        )}
      </div>

      <XpBar
        value={questionNumber}
        max={Math.max(total, 1)}
        label={`Question ${questionNumber} of ${total}`}
      />

      <h2 id="quiz-question-title" className="quiz-question-text">
        {question?.question}
      </h2>

      <div className="answer-grid" role="group" aria-label="Answer options">
        {options.map((option, index) => {
          const state = getOptionState(option, selected, feedback)
          const disabled = Boolean(feedback) || checking || submitting

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
          <b>{feedback.correct ? 'Correct!' : 'Not quite yet'}</b>
          {!feedback.correct && (
            <span className="quiz-feedback-answer">
              Correct answer: {feedback.correct_answer}
            </span>
          )}
          {feedback.explanation && (
            <p className="quiz-feedback-explanation">{feedback.explanation}</p>
          )}
        </div>
      )}

      {checkError && (
        <div className="form-error" role="alert">
          {checkError}
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
        ) : (
          <button
            type="button"
            className="btn-primary btn-block"
            onClick={onContinue}
            disabled={submitting}
          >
            {submitting ? 'Scoring…' : isLast ? 'See results' : 'Continue'}
          </button>
        )}
      </div>
    </section>
  )
}
