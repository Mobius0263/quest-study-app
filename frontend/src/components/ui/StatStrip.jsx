import StatCard from './StatCard.jsx'

export default function StatStrip({ stats, children }) {
  if (stats) {
    return (
      <div className="stat-strip">
        {stats.map((stat, index) => (
          <StatCard key={stat.key ?? stat.label ?? index} {...stat} />
        ))}
      </div>
    )
  }

  return <div className="stat-strip">{children}</div>
}
