export default function XpBar({
  value = 0,
  max = 100,
  variant = '',
  label = 'Progress',
  height,
}) {
  const safeMax = Number(max) > 0 ? Number(max) : 1
  const safeValue = Math.max(0, Number(value) || 0)
  const percent = Math.min(100, (safeValue / safeMax) * 100)

  return (
    <div
      className={`prog-bar ${variant}`.trim()}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={safeMax}
      aria-valuenow={safeValue}
      style={height ? { height } : undefined}
    >
      <span className="prog-bar-fill" style={{ width: `${percent}%` }} />
    </div>
  )
}
