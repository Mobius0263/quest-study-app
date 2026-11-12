import { STATUS_LABELS } from '../../utils/quests.js'

const CLASS_BY_STATUS = {
  'not-started': '',
  'in-progress': 'prog',
  done: 'done',
}

export default function StatusPill({ status = 'not-started' }) {
  const key =
    status === 'done' || status === 'completed'
      ? 'done'
      : status === 'in-progress' || status === 'in_progress'
        ? 'in-progress'
        : 'not-started'

  return (
    <span className={`status-pill ${CLASS_BY_STATUS[key]}`.trim()}>
      {STATUS_LABELS[key]}
    </span>
  )
}
