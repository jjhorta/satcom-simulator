import { useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { resetPassword } from '../api/client'
import { CheckCircle, AlertCircle } from 'lucide-react'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    if (!token) { setError('Missing reset token'); return }
    setLoading(true)
    try {
      await resetPassword(token, password)
      setDone(true)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Reset failed. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center max-w-sm">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">Invalid link</h1>
          <p className="text-sm text-gray-400">This password reset link is missing or invalid.</p>
          <Link to="/forgot-password" className="inline-block mt-6 text-sm text-indigo-400 hover:text-indigo-300">
            Request a new reset link
          </Link>
        </div>
      </div>
    )
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center max-w-sm">
          <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">Password updated!</h1>
          <p className="text-sm text-gray-400">You can now sign in with your new password.</p>
          <Link to="/login" className="inline-block mt-6 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 transition-colors">
            Sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Set new password</h1>
          <p className="text-sm text-gray-400 mt-1">Choose a strong password for your account.</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-8 shadow-xl space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">New password</label>
            <input type="password" value={password}
              onChange={e => setPassword(e.target.value)} required minLength={8}
              className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white
                         focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Confirm password</label>
            <input type="password" value={confirm}
              onChange={e => setConfirm(e.target.value)} required
              className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white
                         focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          {error && <p className="text-sm text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">{error}</p>}
          <button type="submit" disabled={loading || !password || !confirm}
            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500
                       disabled:opacity-50 font-medium text-white transition-colors">
            {loading ? 'Resetting...' : 'Reset password'}
          </button>
        </form>
      </div>
    </div>
  )
}
