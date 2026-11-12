export default function ComingSoonPanel({
  kicker = 'Next up',
  title,
  children,
  action,
}) {
  return (
    <section className="card stub-card">
      <span className="stub-kicker">{kicker}</span>
      <h2>{title}</h2>
      <p>{children}</p>
      {action && <div className="stub-action">{action}</div>}
    </section>
  )
}
