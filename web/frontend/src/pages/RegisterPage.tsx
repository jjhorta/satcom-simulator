import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { register } from '../api/client'

export default function RegisterPage() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [orgName,  setOrgName]  = useState('')
  const [role,     setRole]     = useState<'creator' | 'demo'>('creator')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const { setToken, setUser } = useAuthStore()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const resp = await register({ email, password, org_name: orgName || undefined, role })
      setToken(resp.access_token)
      if (resp.user) setUser(resp.user)
      navigate('/')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (detail === 'Email already registered') {
        setError('This email is already registered. Try signing in instead.')
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Registration failed. Please check your details and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const inputCls = "w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"

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
          <p className="text-sm text-gray-400 mt-1">Create your account</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-8 shadow-xl space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <input type="email" autoComplete="email" value={email}
              onChange={(e) => setEmail(e.target.value)} required className={inputCls}
              placeholder="you@example.com" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password <span className="text-gray-500 font-normal text-xs">(min. 8 chars)</span></label>
            <input type="password" autoComplete="new-password" value={password}
              onChange={(e) => setPassword(e.target.value)} required minLength={8} className={inputCls} />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Organization name <span className="text-gray-500 font-normal text-xs">(optional)</span></label>
            <input type="text" value={orgName}
              onChange={(e) => setOrgName(e.target.value)} className={inputCls}
              placeholder="My Team" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Account type</label>
            <div className="grid grid-cols-2 gap-2">
              {(['creator', 'demo'] as const).map((r) => (
                <button key={r} type="button" onClick={() => setRole(r)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    role === r
                      ? 'bg-indigo-600 border-indigo-500 text-white'
                      : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white'
                  }`}>
                  {r === 'creator' ? 'Full access' : 'Demo (14 days)'}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">{error}</p>
          )}

          <button type="submit" disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500
                       disabled:opacity-50 disabled:cursor-not-allowed font-medium text-white transition-colors">
            {loading ? 'Creating account…' : 'Create account'}
          </button>

          <p className="text-center text-xs text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
