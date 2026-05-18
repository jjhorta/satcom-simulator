/**
 * ShareReportModal — generate a password-protected public link for a report.
 */
import { useEffect, useState } from 'react'
import { X, Share2, Copy, Check, Loader2 } from 'lucide-react'
import { shareReport, getShareSettings } from '../api/client'
import { useReportStore } from '../store/reportStore'
import { saveReport } from '../api/client'

interface Props {
  reportId: string
  onClose:  () => void
}

export default function ShareReportModal({ reportId, onClose }: Props) {
  const reports          = useReportStore((s) => s.reports)
  const updateReportMeta = useReportStore((s) => s.updateReportMeta)
  const report           = reports.find((r) => r.reportId === reportId)

  const [password,   setPassword]   = useState('')
  const [url,        setUrl]        = useState(report?.shareToken
    ? `${window.location.origin}/constellation-simulator/shared/${report.shareToken}`
    : ''
  )
  const [copying,    setCopying]    = useState(false)
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState('')

  // Pre-fill with a hint if a default password is set
  useEffect(() => {
    getShareSettings()
      .then((s) => { if (s.has_default_password) setPassword('') })
      .catch(() => {/* ignore */})
  }, [])

  async function handleGenerate() {
    const pwd = password.trim()
    if (pwd.length < 4) { setError('Password must be at least 4 characters.'); return }
    setLoading(true); setError('')
    try {
      const { token } = await shareReport(reportId, pwd)
      const newUrl = `${window.location.origin}/constellation-simulator/shared/${token}`
      setUrl(newUrl)
      if (report) {
        updateReportMeta(reportId, { shareToken: token })
        saveReport({ ...report, shareToken: token }).catch(console.error)
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? (e as Error)?.message
        ?? 'Failed to generate link.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(url)
    setCopying(true)
    setTimeout(() => setCopying(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Share2 className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">Share Report</h2>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-gray-400 mb-4">
          Generate a password-protected public link. Anyone with the link and password can view this report
          (AI insights are excluded from the public view).
        </p>

        {/* Password */}
        <label className="block text-xs text-gray-400 mb-1">Share password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleGenerate() }}
          placeholder="At least 4 characters"
          className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white
                     placeholder-gray-600 focus:outline-none focus:border-indigo-500 mb-3"
        />

        {error && (
          <p className="text-xs text-red-400 mb-3">{error}</p>
        )}

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-indigo-600
                     text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-60 transition-colors mb-4"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share2 className="w-4 h-4" />}
          {url ? 'Regenerate link' : 'Generate link'}
        </button>

        {/* Generated URL */}
        {url && (
          <div className="space-y-2">
            <label className="block text-xs text-gray-400">Public link</label>
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={url}
                className="flex-1 min-w-0 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700
                           text-xs text-indigo-300 font-mono focus:outline-none"
              />
              <button
                onClick={handleCopy}
                className={`flex-shrink-0 px-3 py-2 rounded-lg border text-xs font-medium transition-colors ${
                  copying
                    ? 'bg-green-600/20 border-green-600/40 text-green-300'
                    : 'border-gray-700 text-gray-300 hover:bg-gray-800'
                }`}
              >
                {copying ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
            <p className="text-xs text-gray-600">
              Share this link together with the password you set above.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
