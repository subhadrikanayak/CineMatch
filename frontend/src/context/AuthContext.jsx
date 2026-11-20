import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { fetchMe, loginUser, registerUser } from '../api/auth.js'
import { tokenStore } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false)
      return
    }
    fetchMe()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const onLogout = () => setUser(null)
    window.addEventListener('auth:logout', onLogout)
    return () => window.removeEventListener('auth:logout', onLogout)
  }, [])

  const login = useCallback(async (identifier, password) => {
    const data = await loginUser(identifier, password)
    tokenStore.set(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(
    async (email, username, password) => {
      await registerUser({ email, username, password })
      return login(email, password)
    },
    [login],
  )

  const logout = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)