function IconBase({ size = 24, className, children, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  )
}

export function ShieldIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M12 22s8-3.6 8-10V5l-8-3-8 3v7c0 6.4 8 10 8 10z" />
    </IconBase>
  )
}

export function FlameIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
    </IconBase>
  )
}

export function ZapIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
    </IconBase>
  )
}

export function CheckIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M20 6 9 17l-5-5" />
    </IconBase>
  )
}

export function ClockIcon(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </IconBase>
  )
}

export function SwordIcon(props) {
  return (
    <IconBase {...props}>
      <path d="m14.5 12.5-8 8a2.12 2.12 0 1 1-3-3l8-8" />
      <path d="m16 16 2-2" />
      <path d="m17 11 4.3-4.3a2.41 2.41 0 0 0-3.4 0L13.5 11z" />
    </IconBase>
  )
}

export function StarIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </IconBase>
  )
}

export function PlusIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M12 5v14M5 12h14" />
    </IconBase>
  )
}

export function TargetIcon(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1" />
    </IconBase>
  )
}

export function HomeIcon(props) {
  return (
    <IconBase {...props}>
      <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V10z" />
    </IconBase>
  )
}

export function MapIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M9 18 3 21V6l6-3 6 3 6-3v15l-6 3-6-3z" />
      <path d="M9 3v15M15 6v15" />
    </IconBase>
  )
}

export function UserIcon(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </IconBase>
  )
}

export function SigmaIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M18 5H7l6 7-6 7h11" />
      <path d="M7 5v0" strokeWidth="3" />
    </IconBase>
  )
}

export function LeafIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M11 20A7 7 0 0 1 4 13c0-5 4-9 16-9 0 12-4 16-9 16z" />
      <path d="M4 21c4-6 8-9 12-11" />
    </IconBase>
  )
}

export function AtomIcon(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="2" />
      <ellipse cx="12" cy="12" rx="10" ry="4" />
      <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(65 12 12)" />
    </IconBase>
  )
}

export function BookIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4a2 2 0 0 0-2-2H6.5A2.5 2.5 0 0 0 4 4.5v15z" />
      <path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5" />
    </IconBase>
  )
}

export function TrophyIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M8 4h8v5a4 4 0 0 1-8 0V4z" />
      <path d="M8 6H4v1a4 4 0 0 0 4 4M16 6h4v1a4 4 0 0 1-4 4" />
      <path d="M12 13v4M8 21h8M9 17h6" />
    </IconBase>
  )
}

export function AlertCircleIcon(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v5M12 16h.01" />
    </IconBase>
  )
}

export function ChevronLeftIcon(props) {
  return (
    <IconBase {...props}>
      <path d="m15 18-6-6 6-6" />
    </IconBase>
  )
}

export function ChevronRightIcon(props) {
  return (
    <IconBase {...props}>
      <path d="m9 18 6-6-6-6" />
    </IconBase>
  )
}

export function MoreIcon(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="5" r="1" fill="currentColor" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
      <circle cx="12" cy="19" r="1" fill="currentColor" />
    </IconBase>
  )
}

export function EditIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" />
    </IconBase>
  )
}

export function TrashIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
      <path d="M10 11v5M14 11v5" />
    </IconBase>
  )
}

export function CloseIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M18 6 6 18M6 6l12 12" />
    </IconBase>
  )
}

export function LockIcon(props) {
  return (
    <IconBase {...props}>
      <rect x="4" y="10" width="16" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </IconBase>
  )
}

export function LogOutIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </IconBase>
  )
}

export function RefreshIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M21 2v6h-6" />
      <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
      <path d="M3 22v-6h6" />
      <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
    </IconBase>
  )
}

export function UploadIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </IconBase>
  )
}

export function GemIcon({ size = 13, className }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <path d="M7 3h10l4 6-9 12L3 9z" />
      <path d="M3 9h18M12 21L8 9l4-6 4 6z" stroke="#fff" strokeWidth="1.2" fill="none" />
    </svg>
  )
}
