export default function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <header className="page-head">
      <div className="page-head-copy">
        {eyebrow && <div className="layout-note">{eyebrow}</div>}
        <h1 className="screen-title">{title}</h1>
        {subtitle && <p className="screen-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-head-actions">{actions}</div>}
    </header>
  )
}
