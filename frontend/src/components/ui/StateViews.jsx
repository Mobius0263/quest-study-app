import { AlertCircleIcon, MapIcon } from './icons.jsx'

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div className="state-view" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  )
}

export function EmptyState({
  icon: Icon = MapIcon,
  title = 'Nothing here yet',
  message,
  action,
}) {
  return (
    <div className="state-view">
      <span className="state-view-icon" aria-hidden="true">
        <Icon size={26} />
      </span>
      <h3>{title}</h3>
      {message && <p>{message}</p>}
      {action && <div className="state-view-action">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'Please try again in a moment.',
  onRetry,
}) {
  return (
    <div className="state-view" role="alert">
      <span className="state-view-icon danger" aria-hidden="true">
        <AlertCircleIcon size={26} />
      </span>
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry && (
        <div className="state-view-action">
          <button type="button" className="btn-primary" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}
    </div>
  )
}
