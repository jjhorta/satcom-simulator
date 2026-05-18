/**
 * SharedReportPage — public (no auth) read-only report viewer.
 * Route: /shared/:token
 * Shows a password gate; on success fetches and renders the report.
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Lock, Share2, AlertCircle } from 'lucide-react'
import { fetchSharedReport, fetchSharedJobFiles, fetchSharedCsv, sharedFileUrl, fetchSharedTco } from '../api/client'
import { TcoDashboardContent } from '../components/viewers/TcoDashboardModal'
import type { ReportState } from '../types'

// ── ReportSection ─────────────────────────────────────────────────────────────
function ReportSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold text-indigo-400 uppercase tracking-widest pb-2 border-b border-gray-800">
        {title}
      </h2>
      {children}
    </section>
  )
}

// ── Param table ───────────────────────────────────────────────────────────────
const SKIP_PARAM_KEYS = new Set(['shells', 'reportRoutes', 'constellation_name'])
function ParamTable({ params }: { params: Record<string, unknown> }) {
  const entries = Object.entries(params).filter(([k, v]) =>
    v !== null && v !== undefined && v !== '' &&
    !SKIP_PARAM_KEYS.has(k) &&
    typeof v !== 'object'
  )
  if (!entries.length) return <p className="text-sm text-gray-500">No parameters recorded.</p>
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-baseline gap-2 min-w-0">
          <span className="text-xs text-gray-500 capitalize flex-shrink-0">{k.replace(/_/g, ' ')}</span>
          <span className="text-xs text-gray-200 font-mono truncate">{String(v)}</span>
        </div>
      ))}
    </div>
  )
}

// ── TCO section with shared proxy ─────────────────────────────────────────────
function SharedTcoSection({
  token, jobId, password,
}: { token: string; jobId: string; password: string }) {
  const tcoQ = useQuery({
    queryKey: ['shared-tco', token, jobId],
    queryFn:  () => fetchSharedTco(token, jobId, password),
    retry: false,
  })
  if (tcoQ.isLoading) return <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse"><Loader2 className="w-4 h-4 animate-spin" /> Loading business plan…</div>
  if (tcoQ.isError)   return <p className="text-sm text-red-400">TCO data not available.</p>
  if (!tcoQ.data)     return null
  return <TcoDashboardContent data={tcoQ.data} />
}

// ── Tag colours ───────────────────────────────────────────────────────────────
const TAG_COLOURS = [
  'bg-indigo-900/60 text-indigo-300 border-indigo-700/60',
  'bg-teal-900/60 text-teal-300 border-teal-700/60',
  'bg-amber-900/60 text-amber-300 border-amber-700/60',
  'bg-pink-900/60 text-pink-300 border-pink-700/60',
  'bg-green-900/60 text-green-300 border-green-700/60',
]
function tagColour(tag: string) {
  let h = 0
  for (let i = 0; i < tag.length; i++) h = (h * 31 + tag.charCodeAt(i)) & 0xffff
  return TAG_COLOURS[h % TAG_COLOURS.length]
}

// ── SharedJobImage — resolves the actual PNG filename via file-list endpoint ──
function SharedJobImage({
  token, jobId, password, alt,
}: { token: string; jobId: string; password: string; alt: string }) {
  const filesQ = useQuery({
    queryKey: ['shared-files', token, jobId],
    queryFn:  () => fetchSharedJobFiles(token, jobId, password),
    retry: false,
  })
  if (filesQ.isLoading) return (
    <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse">
      <Loader2 className="w-4 h-4 animate-spin" /> Loading image…
    </div>
  )
  const pngFile = filesQ.data?.files.find((f) => f.endsWith('.png') || f.endsWith('.jpg'))
  if (!pngFile) return <p className="text-sm text-gray-500">Image not available.</p>
  return (
    <img
      src={sharedFileUrl(token, jobId, pngFile, password)}
      alt={alt}
      className="w-full rounded-lg border border-gray-800"
      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
    />
  )
}

// ── SharedRouteSummaryRow — fetches CSV and shows avg connectivity ─────────────
function pctToColour(pct: number): string {
  if (pct >= 90) return 'text-green-400'
  if (pct >= 70) return 'text-yellow-400'
  if (pct >= 50) return 'text-orange-400'
  return 'text-red-400'
}

function SharedRouteSummaryRow({
  token, jobId, routeName, password,
}: { token: string; jobId: string; routeName: string; password: string }) {
  // Get file list to find the CSV name
  const filesQ = useQuery({
    queryKey: ['shared-files', token, jobId],
    queryFn:  () => fetchSharedJobFiles(token, jobId, password),
    retry: false,
  })
  const csvFile = filesQ.data?.files.find((f) => f.endsWith('.csv'))

  const csvQ = useQuery({
    queryKey: ['shared-csv', token, jobId, csvFile],
    queryFn:  () => fetchSharedCsv(token, jobId, csvFile!, password),
    enabled:  !!csvFile,
    retry: false,
  })

  const rows = (csvQ.data ?? []) as Array<{ connectivity_pct: number }>
  const valid = rows.filter((r) => typeof r.connectivity_pct === 'number')
  const avg  = valid.length ? valid.reduce((s, r) => s + r.connectivity_pct, 0) / valid.length : null
  const min  = valid.length ? Math.min(...valid.map((r) => r.connectivity_pct)) : null
  const max  = valid.length ? Math.max(...valid.map((r) => r.connectivity_pct)) : null

  const loading = filesQ.isLoading || csvQ.isLoading

  return (
    <tr className="border-t border-gray-800">
      <td className="py-2.5 pr-4 text-sm text-gray-200 font-medium">{routeName}</td>
      <td className="py-2.5 pr-4 text-sm tabular-nums">
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-500" />
        ) : avg !== null ? (
          <span className={`font-semibold ${pctToColour(avg)}`}>{avg.toFixed(1)}%</span>
        ) : '—'}
      </td>
      <td className="py-2.5 pr-4 text-sm tabular-nums text-gray-400">
        {min !== null ? <span className={pctToColour(min)}>{min.toFixed(1)}%</span> : '—'}
      </td>
      <td className="py-2.5 text-sm tabular-nums text-gray-400">
        {max !== null ? <span className={pctToColour(max)}>{max.toFixed(1)}%</span> : '—'}
      </td>
      <td className="py-2.5 text-sm tabular-nums text-gray-500">
        {valid.length || '—'}
      </td>
    </tr>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function SharedReportPage() {
  const { token = '' } = useParams<{ token: string }>()

  const [password, setPassword] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [report, setReport] = useState<ReportState | null>(null)

  async function handleUnlock() {
    const pwd = password.trim()
    if (!pwd) { setError('Please enter the share password.'); return }
    setSubmitted(true); setError('')
    try {
      const data = await fetchSharedReport(token, pwd)
      setReport(data)
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      setError(status === 401 ? 'Incorrect password.' : 'Share link not found or expired.')
      setSubmitted(false)
    }
  }

  // ── Password gate ──────────────────────────────────────────────────────────
  if (!report) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-sm p-8 space-y-5">
          <div className="flex flex-col items-center gap-2 text-center">
            <div className="p-3 rounded-full bg-indigo-900/40 border border-indigo-700/40">
              <Share2 className="w-6 h-6 text-indigo-400" />
            </div>
            <h1 className="text-lg font-bold text-white">Shared Report</h1>
            <p className="text-sm text-gray-400">
              Enter the password to view this constellation simulation report.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2 rounded-lg bg-gray-800 border border-gray-700 px-3 py-2">
              <Lock className="w-4 h-4 text-gray-500 flex-shrink-0" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleUnlock() }}
                placeholder="Share password"
                className="flex-1 bg-transparent text-sm text-white placeholder-gray-600 focus:outline-none"
                autoFocus
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-xs text-red-400">
                <AlertCircle className="w-3.5 h-3.5" />
                {error}
              </div>
            )}

            <button
              onClick={handleUnlock}
              disabled={submitted}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600
                         text-white text-sm font-medium hover:bg-indigo-500 disabled:opacity-60 transition-colors"
            >
              {submitted
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : 'View Report'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Report view ────────────────────────────────────────────────────────────
  const heatmapJobId   = report.jobs.heatmap   ?? null
  const heatmapRfJobId = report.jobs.heatmapRf ?? null
  const orbitJobId     = report.jobs.orbit     ?? null

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Share2 className="w-4 h-4 text-indigo-400" />
                <span className="text-xs text-gray-500 uppercase tracking-wider">Shared Report</span>
              </div>
              <h1 className="text-xl font-bold text-white">{report.title ?? report.label}</h1>
              <p className="text-xs text-gray-500 mt-1">
                Created {new Date(report.createdAt).toLocaleString()}
                {report.label && report.title && report.title !== report.label && (
                  <span className="ml-2 text-indigo-400">{report.label}</span>
                )}
              </p>
              {(report.tags ?? []).length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {(report.tags ?? []).map((tag) => (
                    <span key={tag} className={`inline-flex px-2 py-0 rounded text-[11px] font-medium border ${tagColour(tag)}`}>
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-10">

        {/* Constellation Parameters */}
        <ReportSection title="Constellation Parameters">
          <ParamTable params={report.params as Record<string, unknown>} />
        </ReportSection>

        {/* Coverage Heatmap */}
        <ReportSection title="1 · Coverage Heatmap (Geometric)">
          {heatmapJobId
            ? <SharedJobImage token={token} jobId={heatmapJobId} password={password} alt="Coverage heatmap" />
            : <p className="text-sm text-gray-500">No heatmap available.</p>
          }
        </ReportSection>

        {/* RF Link Budget Heatmap */}
        {heatmapRfJobId && (
          <ReportSection title="1b · RF Link Budget Heatmap">
            <p className="text-xs text-gray-500 mb-3">
              % time the downlink RF link budget closes (FSPL + rain attenuation + noise figure vs required SNR).
            </p>
            <SharedJobImage token={token} jobId={heatmapRfJobId} password={password} alt="RF link budget heatmap" />
          </ReportSection>
        )}

        {/* Business Plan */}
        {orbitJobId && (
          <ReportSection title="3 · Business Plan (TCO)">
            <SharedTcoSection token={token} jobId={orbitJobId} password={password} />
          </ReportSection>
        )}

        {/* Maritime Routes */}
        {report.selectedRoutes.length > 0 && (
          <ReportSection title="4 · Maritime Routes">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase tracking-wider">
                    <th className="pb-2 pr-4">Route</th>
                    <th className="pb-2 pr-4">Avg. Connectivity</th>
                    <th className="pb-2 pr-4">Min</th>
                    <th className="pb-2 pr-4">Max</th>
                    <th className="pb-2">Waypoints</th>
                  </tr>
                </thead>
                <tbody>
                  {report.selectedRoutes.map((r) => {
                    const jobId = report.jobs.routes[r]
                    if (!jobId) return (
                      <tr key={r} className="border-t border-gray-800">
                        <td className="py-2 pr-4 text-sm text-gray-400">{r}</td>
                        <td className="py-2 text-sm text-gray-600" colSpan={4}>No job data</td>
                      </tr>
                    )
                    return (
                      <SharedRouteSummaryRow
                        key={r}
                        token={token}
                        jobId={jobId}
                        routeName={r}
                        password={password}
                      />
                    )
                  })}
                </tbody>
              </table>
            </div>
          </ReportSection>
        )}

        {/* Notes */}
        {report.notes && (
          <ReportSection title="Notes">
            <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap bg-gray-900 rounded-lg p-4 border border-gray-800">
              {report.notes}
            </div>
          </ReportSection>
        )}

        <p className="text-center text-xs text-gray-700 pb-4">
          Generated by NOS Constellation Simulator
        </p>
      </div>
    </div>
  )
}
