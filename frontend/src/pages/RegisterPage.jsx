import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.js'
import { getApiErrorMessage } from '../api/errors.js'
import { LoadingState } from '../components/ui/StateViews.jsx'
import { ShieldIcon } from '../components/ui/icons.jsx'

const INITIAL_FORM = {
  first_name: '',
  last_name: '',
  username: '',
  email: '',
  password: '',
  role: 'student',
}

export default function RegisterPage() {
  const { user, loading, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(INITIAL_FORM)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (loading) {
    return (
      <div className="app-loading">
        <LoadingState label="Checking your session…" />
      </div>
    )
  }

  if (user) return <Navigate to="/" replace />

  function handleChange(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!form.username.trim() || !form.email.trim() || !form.password) {
      setError('Username, email and password are required.')
      return
    }

    if (form.password.length < 6) {
      setError('Use at least 6 characters for your password.')
      return
    }

    setSubmitting(true)
    try {
      await register({
        ...form,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
      })
      navigate('/', { replace: true })
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

        <h1 className="auth-title">Create your account</h1>
        <p className="auth-subtitle">
          Start with a study identity, then build your streak one quest at a time.
        </p>

        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="form-grid">
            <label className="form-group">
              <span className="form-label">First name</span>
              <input
                className="form-input"
                type="text"
                name="first_name"
                value={form.first_name}
                onChange={handleChange}
                autoComplete="given-name"
              />
            </label>

            <label className="form-group">
              <span className="form-label">Last name</span>
              <input
                className="form-input"
                type="text"
                name="last_name"
                value={form.last_name}
                onChange={handleChange}
                autoComplete="family-name"
              />
            </label>
          </div>

          <label className="form-group">
            <span className="form-label">Username</span>
            <input
              className="form-input"
              type="text"
              name="username"
              value={form.username}
              onChange={handleChange}
              autoComplete="username"
              required
            />
          </label>

          <label className="form-group">
            <span className="form-label">Email</span>
            <input
              className="form-input"
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
              required
            />
          </label>

          <label className="form-group">
            <span className="form-label">Password</span>
            <input
              className="form-input"
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              autoComplete="new-password"
              minLength={6}
              required
            />
            <span className="form-hint">At least 6 characters.</span>
          </label>

          <label className="form-group">
            <span className="form-label">Account type</span>
            <select
              className="form-select"
              name="role"
              value={form.role}
              onChange={handleChange}
            >
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
            </select>
          </label>

          <button type="submit" className="btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
