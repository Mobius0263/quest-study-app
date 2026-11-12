import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'
import { getApiErrorMessage } from '../api/errors.js'
import { LoadingState } from '../components/ui/StateViews.jsx'
import { ShieldIcon } from '../components/ui/icons.jsx'

export default function LoginPage() {
  const { user, loading, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const from = location.state?.from || '/'

  if (loading) {
    return (
      <div className="app-loading">
        <LoadingState label="Checking your session…" />
      </div>
    )
  }

  if (user) return <Navigate to={from} replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!username.trim() || !password) {
      setError('Enter your username and password.')
      return
    }

    setSubmitting(true)
    try {
      await login({ username: username.trim(), password })
      navigate(from, { replace: true })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <Link to="/login" className="auth-brand" aria-label="Quest Study">
          <span className="topbar-crest" aria-hidden="true">
            <ShieldIcon size={18} />
          </span>
          Quest Study
        </Link>

        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-subtitle">Sign in to keep your streak and quests moving.</p>

        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label className="form-group">
            <span className="form-label">Username</span>
            <input
              className="form-input"
              type="text"
              name="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </label>

          <label className="form-group">
            <span className="form-label">Password</span>
            <input
              className="form-input"
              type="password"
              name="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" className="btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="auth-switch">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  )
}
