const VARIANT_CLASS = {
  assignment: 'assign',
  revision: 'revision',
  xp: 'xp',
}

export default function Tag({ variant = 'default', className = '', children }) {
  const variantClass = VARIANT_CLASS[variant] || ''
  return <span className={`tag ${variantClass} ${className}`.trim()}>{children}</span>
}
