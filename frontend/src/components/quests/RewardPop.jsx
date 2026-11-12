export default function RewardPop({ show, xp }) {
  return (
    <div
      className={`reward-pop ${show ? 'show' : ''}`.trim()}
      role="status"
      aria-live="polite"
    >
      {show ? `+${xp} XP · Quest complete` : ''}
    </div>
  )
}
