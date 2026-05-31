import { useState, useEffect } from 'react'
import { X, ExternalLink, Loader2, CheckCircle, Clock, AlertCircle, Satellite } from 'lucide-react'

const API_BASE = `${import.meta.env.BASE_URL?.replace(/\/$/, '')}/api`

interface Resource {
  job_id: string
  mode?: string
  status?: string
  fetched: boolean
  error?: string
}

export default function ResourcesModal({ messages, token, onClose }: { messages: { role: string; content: string }[]; token: string | null; onClose: () => void }) {
  const [resources, setResources] = useState<Resource[]>([])

  useEffect(() => {
    // Extract all UUIDs from assistant messages that look like job IDs
    const uuids = new Set<string>()
    const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi
    for (const msg of messages) {
      if (msg.role === 'assistant') {
        const matches = msg.content.match(uuidRegex)
        if (matches) matches.forEach(id => uuids.add(id.toLowerCase()))
      }
    }

    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const results: Resource[] = []
    const fetches: Promise<void>[] = []

    uuids.forEach(jobId => {
      const r: Resource = { job_id: jobId, fetched: false }
      results.push(r)
      fetches.push(
        fetch(`${API_BASE}/jobs/${jobId}`, { headers })
          .then(res => res.ok ? res.json() : null)
          .then(data => {
            if (data) {
              r.mode = data.mode || '?'
              r.status = data.status || '?'
              r.fetched = true
            } else {
              r.error = 'not found'
              r.fetched = true
            }
          })
          .catch(() => { r.error = 'error'; r.fetched = true })
      )
    })

    Promise.all(fetches).then(() => setResources([...results]))
  }, [messages])

  const statusIcon = (status?: string) => {
    if (!status) return <Clock className="w-3.5 h-3.5 text-gray-500" />
    switch (status) {
      case 'completed': return <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
      case 'running': case 'queued': return <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
      case 'failed': return <AlertCircle className="w-3.5 h-3.5 text-red-400" />
      default: return <Clock className="w-3.5 h-3.5 text-gray-500" />
    }
  }

  const statusLabel = (status?: string) => {
    if (!status) return 'checking...'
    return status
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 rounded-2xl border border-gray-800 w-full max-w-lg max-h-[80vh] flex flex-col"
           onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Satellite className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-semibold text-white">Resources</h2>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {resources.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">
              No simulation jobs found in this conversation.
              <br />Ask CARL to run a simulation and resources will appear here.
            </p>
          ) : (
            resources.map((r, i) => (
              <div key={i}
                className="flex items-center gap-3 bg-gray-800/60 rounded-lg px-4 py-3 border border-gray-700/50 hover:border-gray-600 transition-colors">
                {statusIcon(r.status)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-300 truncate">{r.job_id.slice(0, 12)}...</span>
                    {r.mode && <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">{r.mode}</span>}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {r.fetched ? statusLabel(r.status) : 'checking...'}
                    {r.error && <span className="text-red-400 ml-1">({r.error})</span>}
                  </div>
                </div>
                <a href={`/constellation-simulator/?job=${r.job_id}`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-indigo-400 hover:text-indigo-300 transition-colors flex-shrink-0"
                  title="Open in dashboard">
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
