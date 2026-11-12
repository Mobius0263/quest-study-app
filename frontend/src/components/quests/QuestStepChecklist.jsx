import { Link } from 'react-router-dom'
import { CheckIcon } from '../ui/icons.jsx'
import XpBar from '../ui/XpBar.jsx'
import {
  getBestAttemptLabel,
  getCompletedStepIds,
  getLinkedQuiz,
  getQuizStepLabel,
  getQuestSteps,
  isQuestCompleted,
} from '../../utils/questDetail.js'

export default function QuestStepChecklist({
  quest,
  isStudent,
  saving,
  error,
  onToggleStep,
  boardSearch = '',
}) {
  const steps = getQuestSteps(quest)
  const completedIds = new Set(getCompletedStepIds(quest))
  const linkedQuiz = getLinkedQuiz(quest)
  const completedQuest = isQuestCompleted(quest)
  const quizPassed = Boolean(linkedQuiz?.passed)
  const quizTicked = quizPassed || completedQuest
  const doneCount = steps.filter(
    (step) => completedQuest || completedIds.has(String(step.id)),
  ).length
  const totalRows = steps.length + (linkedQuiz ? 1 : 0)
  const doneRows = doneCount + (quizTicked ? 1 : 0)
  const bestLabel = getBestAttemptLabel(linkedQuiz)

  return (
    <section className="card detail-section" aria-labelledby="quest-steps-title">
      <div className="detail-section-head">
        <div>
          <div className="layout-note">Study steps</div>
          <h2 id="quest-steps-title" className="detail-section-title">
            Finish the study
          </h2>
        </div>
        <span className="attempt-pill">
          {doneRows} / {totalRows} done
        </span>
      </div>

      <XpBar
        value={doneRows}
        max={Math.max(totalRows, 1)}
        label="Quest step progress"
      />

      <div className="step-list">
        {steps.map((step) => {
          const ticked = completedQuest || completedIds.has(String(step.id))

          return (
            <button
              key={step.id}
              type="button"
              className={`step-row ${completedQuest ? 'locked' : ''}`.trim()}
              onClick={() => onToggleStep(step.id)}
              disabled={!isStudent || completedQuest || saving}
              aria-pressed={ticked}
            >
              <span className={`check-box ${ticked ? 'done' : ''}`.trim()} aria-hidden="true">
                {ticked && <CheckIcon size={14} />}
              </span>
              <span className={ticked ? 'done-label' : ''}>{step.label}</span>
            </button>
          )
        })}

        {linkedQuiz && (
          <div className={`step-row quiz-step-row ${completedQuest ? 'locked' : ''}`.trim()}>
            <span
              className={`check-box ${quizTicked ? 'done' : ''}`.trim()}
              aria-hidden="true"
            >
              {quizTicked && <CheckIcon size={14} />}
            </span>
            <span className="quiz-step-copy">
              <span className={`quiz-step-title ${quizTicked ? 'done-label' : ''}`.trim()}>
                {getQuizStepLabel(linkedQuiz)}
              </span>
              <span className="step-note">
                {bestLabel ? `${bestLabel} · ` : ''}
                Not self-ticked — this step ticks only when you pass the quiz.
              </span>
            </span>
            {isStudent && !completedQuest && (
              <Link
                to={`/quests/${quest.id}/quiz`}
                state={{ boardSearch }}
                className="btn-primary btn-sm quiz-start-btn"
              >
                {linkedQuiz.best_attempt ? 'Retry Quiz' : 'Start Quiz'}
              </Link>
            )}
          </div>
        )}
      </div>

      {saving && (
        <p className="detail-save-note" role="status">
          Saving your progress…
        </p>
      )}
      {error && (
        <div className="detail-inline-error" role="alert">
          {error}
        </div>
      )}
    </section>
  )
}
