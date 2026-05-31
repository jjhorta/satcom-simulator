import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { login } from '../api/client'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const { setToken, setUser } = useAuthStore()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const resp = await login({ username, password })
      setToken(resp.access_token)
      if (resp.user) setUser(resp.user)
      navigate('/')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail === 'Incorrect email or password' || detail === 'Incorrect username or password') {
        setError('Incorrect email or password. Please try again.')
      } else if (detail === 'Account deactivated') {
        setError('This account has been deactivated. Contact your administrator.')
      } else {
        setError('Sign-in failed. Please check your credentials.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm">
        {/* Logo / title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 mb-4">
            <svg viewBox="0 0 24 24" className="w-8 h-8 text-white fill-current">
              <circle cx="12" cy="12" r="2" />
              <path d="M12 2a10 10 0 100 20A10 10 0 0012 2zm0 18a8 8 0 110-16 8 8 0 010 16z"
                    opacity=".3" />
              <ellipse cx="12" cy="12" rx="10" ry="4" opacity=".5"
                       transform="rotate(-30 12 12)" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">Constellation Simulator</h1>
          <p className="text-sm text-gray-400 mt-1">Sign in to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-8 shadow-xl">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Email
              </label>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700
                           text-white placeholder-gray-500 focus:outline-none focus:ring-2
                           focus:ring-indigo-500 focus:border-transparent"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-300">Password</label>
                <Link to="/forgot-password" className="text-xs text-gray-500 hover:text-indigo-400 transition-colors">
                  Forgot?
                </Link>
              </div>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700
                           text-white placeholder-gray-500 focus:outline-none focus:ring-2
                           focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
          </div>

          {error && (
            <p className="mt-4 text-sm text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500
                       disabled:opacity-50 disabled:cursor-not-allowed font-medium text-white
                       transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="mt-4 text-center text-xs text-gray-500">
            Don't have an account?{' '}
            <Link to="/register" className="text-indigo-400 hover:text-indigo-300">Register</Link>
          </p>
        </form>
      </div>
    </div>
  )
}

