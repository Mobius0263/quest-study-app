export function GolemSprite({ size = '', className = '', label = 'Granite Golem boss' }) {
  const classes = ['boss-sprite', size, className].filter(Boolean).join(' ')

  return (
    <div className={classes} data-boss-sprite>
      <svg viewBox="0 0 120 120" role="img" aria-label={label}>
        <path d="M60 8l10 14-10 6-10-6z" fill="#a855f7" />
        <path d="M38 30l22-10 22 10 8 22-10 28H40L30 52z" fill="#64748b" />
        <path d="M38 30l22 8 22-8-8 18H46z" fill="#7d8da3" />
        <circle cx="48" cy="48" r="6" fill="#fbbf24" className="boss-eyes" />
        <circle cx="72" cy="48" r="6" fill="#fbbf24" className="boss-eyes" />
        <circle cx="48" cy="48" r="2.5" fill="#111" />
        <circle cx="72" cy="48" r="2.5" fill="#111" />
        <path d="M48 66h24l-4 6H52z" fill="#1f2937" />
        <path d="M30 52L12 72l8 22 16-4-4-24zM90 52l18 20-8 22-16-4 4-24z" fill="#55677e" />
        <path d="M45 82h30l6 22H39z" fill="#475569" />
        <path d="M42 96h14v14H44zM64 96h14v14H66z" fill="#334155" />
        <path d="M40 34l-6-10M82 32l8-12" stroke="#22c55e" strokeWidth="5" strokeLinecap="round" />
        <path d="M52 78l8-8 6 10" stroke="#fbbf24" strokeWidth="3" fill="none" />
      </svg>
    </div>
  )
}

export function HeroSprite({ size = 64, className = '', label = 'Student hero' }) {
  const classes = ['hero-mini', className].filter(Boolean).join(' ')

  return (
    <svg
      viewBox="0 0 120 120"
      className={classes}
      style={{ width: size, height: size }}
      role="img"
      aria-label={label}
    >
      <circle cx="60" cy="34" r="18" fill="#fbbf24" />
      <path d="M42 34a18 18 0 0 1 36 0l-6-16H48z" fill="#2563eb" />
      <circle cx="53" cy="34" r="2.5" fill="#111" />
      <circle cx="67" cy="34" r="2.5" fill="#111" />
      <path d="M60 52l-22 34 14 24h16l14-24z" fill="#16a34a" />
      <path d="M82 58l18 10-6 8-16-8z" fill="#94a3b8" />
      <rect x="50" y="72" width="20" height="14" rx="2" fill="#fff" />
      <path d="M54 79h12" stroke="#2563eb" strokeWidth="2" />
    </svg>
  )
}
