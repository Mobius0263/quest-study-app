export default function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  children,
  valueClassName = '',
}) {
  return (
    <div className="stat-tile">
      <div className="k">
        {Icon && <Icon size={12} />}
        {label}
      </div>
      <div className={`v ${valueClassName}`.trim()}>{value}</div>
      {sub && <div className="s">{sub}</div>}
      {children}
    </div>
  )
}
