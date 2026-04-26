import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { loginUser, registerUser, getCurrentUser, clearTokens, getAccessToken, setUnauthorizedHandler } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  // On mount, check if there's a stored token and load the user
  useEffect(() => {
    setUnauthorizedHandler(logout)

    const token = getAccessToken()
    if (!token) {
      setIsLoading(false)
      return
    }

    getCurrentUser()
      .then((userData) => setUser(userData))
      .catch(() => {
        clearTokens()
      })
      .finally(() => setIsLoading(false))
  }, [logout])

  const login = useCallback(async (email, password) => {
    const data = await loginUser(email, password)
    setUser(data.user)
    return data
  }, [])

  const register = useCallback(async (userData) => {
    const data = await registerUser(userData)
    setUser(data.user)
    return data
  }, [])

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    register,
    setUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
