import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/client'
import { ArrowLeft, Mail, CheckCircle } from 'lucide-react'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent,  setSent]  = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await forgotPassword(email)
      setSent(true)
    } catch {
      setError('Failed to send reset email. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center max-w-sm">
          <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">Check your email</h1>
          <p className="text-sm text-gray-400 leading-relaxed">
            If <strong className="text-gray-300">{email}</strong> is registered,
            we've sent a password reset link. It expires in 1 hour.
          </p>
          <Link to="/login" className="inline-block mt-6 text-sm text-indigo-400 hover:text-indigo-300">
            Back to sign in
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Reset password</h1>
          <p className="text-sm text-gray-400 mt-1">Enter your email and we'll send you a reset link.</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-8 shadow-xl space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <input type="email" value={email}
              onChange={e => setEmail(e.target.value)} required
              className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white
                         placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="you@example.com" />
          </div>
          {error && <p className="text-sm text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">{error}</p>}
          <button type="submit" disabled={loading || !email}
            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500
                       disabled:opacity-50 font-medium text-white transition-colors">
            {loading ? 'Sending...' : 'Send reset link'}
          </button>
          <p className="text-center text-xs text-gray-500">
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1">
              <ArrowLeft className="w-3 h-3" /> Back to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
