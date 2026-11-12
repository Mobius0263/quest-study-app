import { useCallback, useEffect, useMemo, useState } from 'react'
import { clearToken, getToken, setToken } from '../api/client.js'
import { loginRequest, meRequest, registerRequest } from '../api/auth.js'
import { AuthContext } from './AuthContext.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      if (!getToken()) {
        if (cancelled) return
        setLoading(false)
        return
      }

      try {
        const currentUser = await meRequest()
        if (!cancelled) setUser(currentUser)
      } catch {
        if (!cancelled) {
          clearToken()
          setUser(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    restoreSession()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    function handleUnauthorized() {
      setUser(null)
    }

    window.addEventListener('quest-study:unauthorized', handleUnauthorized)
    return () => {
      window.removeEventListener('quest-study:unauthorized', handleUnauthorized)
    }
  }, [])

  const login = useCallback(async (credentials) => {
    const data = await loginRequest(credentials)
    setToken(data.token)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (payload) => {
    const data = await registerRequest(payload)
    setToken(data.token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      register,
      logout,
      isTeacher: user?.role === 'teacher',
      isStudent: user?.role === 'student',
    }),
    [user, loading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
