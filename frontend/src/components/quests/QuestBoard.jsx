import QuestCard from '../ui/QuestCard.jsx'
import { EmptyState, ErrorState, LoadingState } from '../ui/StateViews.jsx'
import { MapIcon, PlusIcon } from '../ui/icons.jsx'

function getCountLine(status, visibleCount, totalCount) {
  if (status === 'loading') return 'Loading quests…'
  if (status === 'ready') {
    if (Number.isFinite(totalCount)) {
      const label = totalCount === 1 ? 'quest' : 'quests'
      return `Showing ${visibleCount} of ${totalCount} ${label}`
    }
    return `Showing ${visibleCount} ${visibleCount === 1 ? 'quest' : 'quests'}`
  }
  return 'Quest board'
}

export default function QuestBoard({
  quests,
  status,
  error,
  totalCount,
  hasActiveFilters,
  notice,
  onRetry,
  onClearFilters,
  onCreate,
  canCreate,
  canManage,
  onEdit,
  onDelete,
}) {
  const countLine = getCountLine(status, quests.length, totalCount)

  let emptyTitle = 'No quests yet'
  let emptyMessage = canCreate
    ? 'Create your first Revision Quest and it will show up on this board.'
    : 'Quests assigned to you will appear here.'
  let emptyAction = canCreate ? (
    <button type="button" className="btn-primary" onClick={onCreate}>
      <PlusIcon size={16} />
      New Revision Quest
    </button>
  ) : null

  if (hasActiveFilters) {
    emptyTitle = 'No quests match these filters'
    emptyMessage = 'Try a different combination, or clear the filters to see every quest.'
    emptyAction = (
      <button type="button" className="btn-primary" onClick={onClearFilters}>
        Clear filters
      </button>
    )
  } else if (Number.isFinite(totalCount) && totalCount > 0) {
    emptyTitle = 'No quests to show'
    emptyMessage = 'The board came back empty. Try loading it again.'
    emptyAction = (
      <button type="button" className="btn-primary" onClick={onRetry}>
        Try again
      </button>
    )
  }

  return (
    <section className="quest-board" aria-labelledby="quest-list-title">
      {notice && (
        <div className="board-notice" role="status">
          {notice}
        </div>
      )}

      <div className="board-list-head">
        <h2 id="quest-list-title" className="board-count" aria-live="polite">
          {countLine}
        </h2>
        {hasActiveFilters && (
          <button type="button" className="board-clear" onClick={onClearFilters}>
            Clear filters
          </button>
        )}
      </div>

      {status === 'loading' && (
        <div className="card board-state">
          <LoadingState label="Loading quests…" />
        </div>
      )}

      {status === 'error' && (
        <div className="card board-state">
          <ErrorState
            title="Quest board unavailable"
            message={error}
            onRetry={onRetry}
          />
        </div>
      )}

      {status === 'ready' && quests.length === 0 && (
        <div className="card board-state">
          <EmptyState
            icon={MapIcon}
            title={emptyTitle}
            message={emptyMessage}
            action={emptyAction}
          />
        </div>
      )}

      {status === 'ready' && quests.length > 0 && (
        <div className="board-list">
          {quests.map((quest) => {
            const manageable = canManage ? canManage(quest) : false
            return (
              <QuestCard
                key={quest.id}
                quest={quest}
                onEdit={manageable ? onEdit : undefined}
                onDelete={manageable ? onDelete : undefined}
              />
            )
          })}
        </div>
      )}
    </section>
  )
}
