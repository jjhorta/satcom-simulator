import { useState, useEffect, useMemo } from 'react'
import { CheckCircle, XCircle, Download, X, ZoomIn } from 'lucide-react'
import type { SweepResultEntry } from '../types'

interface Props {
  jobId: string
  apiBase: string
  summaryUrl: string
  gridUrl: string
  token: string
}

export default function BatchResultViewer({ jobId, apiBase, summaryUrl, gridUrl, token }: Props) {
  const [results, setResults] = useState<SweepResultEntry[]>([])
  const [sortKey, setSortKey] = useState<string>('mean_coverage_pct')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<{ label: string; url: string } | null>(null)

  useEffect(() => {
    fetch(summaryUrl, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => {
        setResults(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [summaryUrl, token])

  const sorted = useMemo(() => {
    return [...results].sort((a, b) => {
      const av = a.metrics?.[sortKey as keyof typeof a.metrics] ?? 0
      const bv = b.metrics?.[sortKey as keyof typeof b.metrics] ?? 0
      return sortDir === 'desc' ? bv - av : av - bv
    })
  }, [results, sortKey, sortDir])

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortDir('desc') }
  }

  // Build combo index lookup (index -> entry)
  const comboUrl = (idx: number, filename: string) =>
    `${apiBase}/jobs/${jobId}/combo/${idx}/${filename}`

  if (loading) return <div className="text-gray-400 text-sm p-4">Loading results...</div>
  if (results.length === 0) return <div className="text-gray-500 text-sm p-4">No results yet.</div>

  const sortArrow = (key: string) => sortKey === key ? (sortDir === 'desc' ? ' ▼' : ' ▲') : ''

  return (
    <div className="space-y-6">
      {/* Summary Table */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400">
            <tr>
              <th className="px-3 py-2 text-left">Config</th>
              {results[0]?.params && Object.keys(results[0].params).map(k => (
                <th key={k} className="px-3 py-2 text-left capitalize">{k}</th>
              ))}
              <th className="px-3 py-2 text-right cursor-pointer hover:text-white"
                  onClick={() => toggleSort('mean_coverage_pct')}>
                Mean Cov{sortArrow('mean_coverage_pct')}
              </th>
              <th className="px-3 py-2 text-right cursor-pointer hover:text-white"
                  onClick={() => toggleSort('coverage_above_90_pct')}>
                &gt;90%{sortArrow('coverage_above_90_pct')}
              </th>
              <th className="px-3 py-2 text-right cursor-pointer hover:text-white"
                  onClick={() => toggleSort('coverage_above_50_pct')}>
                &gt;50%{sortArrow('coverage_above_50_pct')}
              </th>
            </tr>
          </thead>
          <tbody className="text-gray-300">
            {sorted.map((r, i) => (
              <tr key={i} className="border-t border-gray-800 hover:bg-gray-800/50">
                <td className="px-3 py-1.5 flex items-center gap-1.5">
                  {r.success
                    ? <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                    : <XCircle className="w-3.5 h-3.5 text-red-500" />}
                  {r.label}
                </td>
                {r.params && Object.entries(r.params).map(([k, v]) => (
                  <td key={k} className="px-3 py-1.5">{typeof v === 'number' ? v.toFixed(1) : v}</td>
                ))}
                <td className="px-3 py-1.5 text-right font-mono">
                  {r.metrics ? `${r.metrics.mean_coverage_pct.toFixed(1)}%` : '—'}
                </td>
                <td className="px-3 py-1.5 text-right font-mono">
                  {r.metrics ? `${r.metrics.coverage_above_90_pct.toFixed(1)}%` : '—'}
                </td>
                <td className="px-3 py-1.5 text-right font-mono">
                  {r.metrics ? `${r.metrics.coverage_above_50_pct.toFixed(1)}%` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Heatmap Thumbnails — sorted to match table order */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <h4 className="text-sm text-gray-400 mb-4">Heatmaps — Side by Side</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {sorted.filter(r => r.success).map((r, idx) => {
            // Find which combo index this entry corresponds to
            const resultIndex = results.indexOf(r)
            const imgUrl = r.heatmap_png
              ? comboUrl(resultIndex, r.heatmap_png.split('/').pop() || '')
              : null
            const paramStr = r.params
              ? Object.entries(r.params).map(([k, v]) => `${k}=${v}`).join(', ')
              : ''

            return (
              <div key={idx} className="group relative">
                <div className="relative rounded overflow-hidden border border-gray-700 bg-gray-800 cursor-pointer"
                     onClick={() => imgUrl && setExpanded({ label: r.label, url: imgUrl })}>
                  {imgUrl ? (
                    <img src={imgUrl} alt={r.label}
                      className="w-full h-auto object-cover transition-transform duration-200 group-hover:scale-105" />
                  ) : (
                    <div className="w-full h-32 flex items-center justify-center text-gray-500 text-sm">
                      No image
                    </div>
                  )}
                  {/* Hover overlay with tooltip */}
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors duration-200 flex items-center justify-center">
                    <ZoomIn className="w-6 h-6 text-white/0 group-hover:text-white/80 transition-all duration-200" />
                  </div>
                  {/* Label bar at bottom */}
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                    <span className="text-xs text-white font-medium truncate block">{r.label}</span>
                  </div>
                </div>
                {/* Tooltip on hover */}
                <div className="absolute z-10 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2
                              bg-gray-800 text-gray-200 text-xs rounded-lg shadow-lg border border-gray-700
                              opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none
                              whitespace-nowrap">
                  <div className="font-medium mb-1">{r.label}</div>
                  <div className="text-gray-400">{paramStr}</div>
                  {r.metrics && (
                    <div className="text-gray-400 mt-1">
                      Mean: {r.metrics.mean_coverage_pct.toFixed(1)}% &middot;
                      &gt;90%: {r.metrics.coverage_above_90_pct.toFixed(1)}%
                    </div>
                  )}
                  <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0
                                border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Individual Results */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <h4 className="text-sm text-gray-400 mb-3">Individual Results</h4>
        <div className="space-y-1">
          {sorted.map((r, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-gray-500">
              {r.success ? '✅' : '❌'} {r.label}
              {r.metrics && (
                <span className="text-gray-600">
                  (mean {r.metrics.mean_coverage_pct.toFixed(1)}%)
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Downloads */}
      <div className="flex gap-3">
        <a href={summaryUrl} download
          className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
          <Download className="w-3.5 h-3.5" /> Download Summary JSON
        </a>
        <a href={gridUrl} download
          className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
          <Download className="w-3.5 h-3.5" /> Download Heatmap Grid
        </a>
      </div>

      {/* Expanded Image Modal */}
      {expanded && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
             onClick={() => setExpanded(null)}>
          <div className="relative max-w-[95vw] max-h-[95vh]"
               onClick={e => e.stopPropagation()}>
            <button onClick={() => setExpanded(null)}
              className="absolute -top-10 right-0 text-white/80 hover:text-white transition-colors">
              <X className="w-6 h-6" />
            </button>
            <img src={expanded.url} alt={expanded.label}
              className="max-w-full max-h-[90vh] rounded-lg shadow-2xl" />
            <div className="text-center text-white/70 text-sm mt-2">{expanded.label}</div>
          </div>
        </div>
      )}
    </div>
  )
}
