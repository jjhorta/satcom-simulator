import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { twofaVerify } from '../api/client'
import { ShieldCheck, Loader2 } from 'lucide-react'

export default function TwoFactorForm({ token: initialToken }: { token?: string }) {
  const [searchParams] = useSearchParams()
  const token = initialToken || searchParams.get('twofa') || ''
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setToken, setUser } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const resp = await twofaVerify(token, code)
      setToken(resp.access_token)
      if (resp.user) setUser(resp.user)
      navigate('/')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'Verification failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 rounded-2xl p-8 shadow-xl">
      <div className="text-center mb-6">
        <ShieldCheck className="w-10 h-10 text-indigo-400 mx-auto mb-2" />
        <h2 className="text-lg font-semibold text-white">Two-Factor Authentication</h2>
        <p className="text-xs text-gray-400 mt-1">Enter the 6-digit code sent to your email.</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          inputMode="numeric"
          autoFocus
          value={code}
          onChange={e => setCode(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
          placeholder="000000"
          className="w-full text-center text-2xl tracking-widest px-3 py-3 rounded-lg bg-gray-800 border border-gray-700
                     text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          maxLength={6}
        />
        {error && <p className="text-sm text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">{error}</p>}
        <button type="submit" disabled={loading || code.length !== 6}
          className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500
                     disabled:opacity-50 font-medium text-white transition-colors">
          {loading ? 'Verifying...' : 'Verify'}
        </button>
        <p className="text-center text-xs text-gray-500">
          Didn't receive the code? <a href={`/login?twofa=${token}`} className="text-indigo-400 hover:text-indigo-300">Send again</a>
        </p>
      </form>
    </div>
  )
}
