import { Link } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader.jsx'
import { EmptyState } from '../components/ui/StateViews.jsx'

export default function NotFoundPage() {
  return (
    <div className="screen-stack">
      <PageHeader
        eyebrow="404"
        title="Page not found"
        subtitle="That trail does not lead anywhere."
      />
      <EmptyState
        title="Nothing on this path"
        message="The page may have moved, or the link may be incomplete."
        action={
          <Link to="/" className="btn-primary">
            Back to dashboard
          </Link>
        }
      />
    </div>
  )
}
