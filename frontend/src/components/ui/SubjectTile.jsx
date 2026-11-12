import { getSubjectConfig } from '../../utils/subjects.js'

export default function SubjectTile({
  subject,
  variant = 'tile',
  size,
  iconSize = 26,
}) {
  const { color, Icon } = getSubjectConfig(subject)
  const isDot = variant === 'dot'
  const dimension = size ?? (isDot ? 52 : 46)

  return (
    <span
      className={isDot ? 'path-dot' : 'subj-tile'}
      style={{ background: color, width: dimension, height: dimension }}
      aria-hidden="true"
    >
      <Icon size={iconSize} />
    </span>
  )
}
