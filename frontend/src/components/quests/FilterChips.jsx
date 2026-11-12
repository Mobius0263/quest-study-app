import { useId } from 'react'

export default function FilterChips({
  label,
  options,
  value,
  onChange,
  className = '',
}) {
  const labelId = useId()

  return (
    <div className={`filter-block ${className}`.trim()}>
      <span id={labelId} className="filter-label">
        {label}
      </span>
      <div className="filter-row" role="group" aria-labelledby={labelId}>
        {options.map((option) => {
          const active = value === option.value
          const Icon = option.icon

          return (
            <button
              key={option.value}
              type="button"
              className={`filter-chip ${active ? 'active' : ''}`.trim()}
              onClick={() => {
                if (!active) onChange(option.value)
              }}
              aria-pressed={active}
            >
              {Icon && <Icon size={14} />}
              {option.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
