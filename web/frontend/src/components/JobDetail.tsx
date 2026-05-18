import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getJob, fileUrl, updateJobMeta } from '../api/client'
import type { JobFile } from '../types'
import { X, FileText, Image, Code2, Table2, Pencil, Check, Maximize2, Minimize2, BarChart2, Sparkles, Globe } from 'lucide-react'
import HeatmapViewer from './viewers/HeatmapViewer'
import RouteViewer from './viewers/RouteViewer'
import TextViewer from './viewers/TextViewer'
import OrbitViewer3D from './viewers/OrbitViewer3D'
import TcoDashboardModal from './viewers/TcoDashboardModal'
import AiAnalysisModal from './viewers/AiAnalysisModal'
import { useAiStore, isAiConfigured } from '../store/aiStore'

// ── File type → viewer ─────────────────────────────────────────────────────────

function fileIcon(type: string) {
  if (type === 'csv') return <Table2 className="w-4 h-4" />
  if (['png', 'gif'].includes(type)) return <Image className="w-4 h-4" />
  if (type === 'html') return <Code2 className="w-4 h-4" />
  return <FileText className="w-4 h-4" />
}

function FileViewer({ jobId, file }: { jobId: string; file: JobFile }) {
  const url = fileUrl(jobId, file.name)

  if (file.type === 'csv' && (file.name.startsWith('heatmap_') || file.name.startsWith('heatmap_rf_'))) {
    return <HeatmapViewer jobId={jobId} filename={file.name} />
  }
  if (file.type === 'csv' && file.name.startsWith('route_')) {
    return <RouteViewer jobId={jobId} filename={file.name} />
  }
  if (['png', 'gif'].includes(file.type)) {
    return (
      <div className="rounded-lg overflow-hidden bg-gray-950 border border-gray-800">
        <img
          src={url}
          alt={file.name}
          className="w-full h-auto"
          style={{ imageRendering: file.type === 'gif' ? 'auto' : 'crisp-edges' }}
        />
      </div>
    )
  }
  if (file.type === 'html') {
    return (
      <div className="rounded-lg overflow-hidden border border-gray-800" style={{ height: 480 }}>
        <iframe
          src={url}
          title={file.name}
          className="w-full h-full bg-white"
          sandbox="allow-scripts allow-same-origin"
        />
      </div>
    )
  }
  if (['txt', 'log'].includes(file.type)) {
    return <TextViewer jobId={jobId} filename={file.name} />
  }
  return (
    <a href={url} download className="text-sm text-indigo-400 underline">
      Download {file.name}
    </a>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function JobDetail({
  jobId, onClose, expanded = false, onToggleExpand,
}: {
  jobId: string
  onClose: () => void
  expanded?: boolean
  onToggleExpand?: () => void
}) {
  const qc = useQueryClient()
  const { data: job, isLoading } = useQuery({
    queryKey:        ['job', jobId],
    queryFn:         () => getJob(jobId),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'queued' || s === 'running' ? 2000 : false
    },
  })

  const [editingMeta, setEditingMeta]     = useState(false)
  const [draftTitle, setDraftTitle]       = useState('')
  const [draftDesc,  setDraftDesc]        = useState('')
  const [savingMeta, setSavingMeta]       = useState(false)
  const [tagInput,   setTagInput]         = useState('')
  const [showTco,    setShowTco]          = useState(false)
  const [showAi,     setShowAi]           = useState(false)

  const aiCfg   = useAiStore()
  const aiReady = isAiConfigured(aiCfg) && job?.status === 'completed'

  if (isLoading || !job) {
    return (
      <div className="p-6 text-sm text-gray-500 animate-pulse">Loading…</div>
    )
  }

  const outputFiles = job.files.filter((f) => f.type !== 'log')
  const logFile     = job.files.find(  (f) => f.type === 'log')
  const hasTco      = job.mode === 'orbit' && job.status === 'completed' &&
                      job.files.some((f) => f.name.startsWith('tco_') && f.name.endsWith('.json'))
  const hasTles     = job.mode === 'orbit' && job.status === 'completed' &&
                      job.files.some((f) => f.name.startsWith('tles_') && f.name.endsWith('.json'))

  const startEdit = () => {
    setDraftTitle(job.title ?? '')
    setDraftDesc(job.description ?? '')
    setEditingMeta(true)
  }

  const saveMeta = async () => {
    setSavingMeta(true)
    await updateJobMeta(jobId, { title: draftTitle || undefined, description: draftDesc || undefined })
    await qc.invalidateQueries({ queryKey: ['job', jobId] })
    await qc.invalidateQueries({ queryKey: ['jobs'] })
    setSavingMeta(false)
    setEditingMeta(false)
  }

  const addTag = async (tag: string) => {
    const trimmed = tag.trim().toLowerCase().replace(/\s+/g, '-').slice(0, 40)
    if (!trimmed) return
    const current = job.tags ?? []
    if (current.includes(trimmed)) return
    await updateJobMeta(jobId, { tags: [...current, trimmed] })
    await qc.invalidateQueries({ queryKey: ['job', jobId] })
    await qc.invalidateQueries({ queryKey: ['jobs'] })
  }

  const removeTag = async (tag: string) => {
    const updated = (job.tags ?? []).filter((t) => t !== tag)
    await updateJobMeta(jobId, { tags: updated })
    await qc.invalidateQueries({ queryKey: ['job', jobId] })
    await qc.invalidateQueries({ queryKey: ['jobs'] })
  }

  return (
    <div className="relative p-5 space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500 font-mono truncate">{job.job_id}</p>

          {editingMeta ? (
            <div className="space-y-2 mt-1">
              <input
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-2.5 py-1.5
                           text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                placeholder="Title (optional)"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                maxLength={120}
              />
              <textarea
                rows={3}
                className="w-full bg-gray-800 border border-gray-700 rounded-md px-2.5 py-1.5
                           text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500
                           resize-none leading-relaxed"
                placeholder="Description (optional)"
                value={draftDesc}
                onChange={(e) => setDraftDesc(e.target.value)}
                maxLength={800}
              />
              <div className="flex gap-2">
                <button
                  onClick={saveMeta}
                  disabled={savingMeta}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium
                             bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  {savingMeta ? 'Saving…' : 'Save'}
                </button>
                <button
                  onClick={() => setEditingMeta(false)}
                  className="px-3 py-1.5 rounded-md text-xs font-medium text-gray-400
                             hover:text-white bg-gray-800 hover:bg-gray-700 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group flex items-start gap-2 mt-0.5">
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-white capitalize">
                  {job.title ?? `${job.mode} Simulation`}
                </h3>
                {job.description && (
                  <p className="text-xs text-gray-400 mt-1 leading-relaxed whitespace-pre-wrap">
                    {job.description}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-1">
                  Created {new Date(job.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={startEdit}
                title="Edit title & description"
                className="mt-1 flex-shrink-0 text-gray-600 hover:text-indigo-400 transition-colors opacity-0 group-hover:opacity-100"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
        {/* Action buttons: expand + close — never overlap pencil */}
        <div className="flex items-center gap-1 flex-shrink-0 mt-0.5">
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              title={expanded ? 'Collapse viewer' : 'Expand viewer'}
              className="text-gray-500 hover:text-indigo-400 transition-colors p-0.5"
            >
              {expanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          )}
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors p-0.5">
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* ── Status ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={job.status} />
        {hasTco && (
          <button
            onClick={() => setShowTco(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       bg-indigo-600/20 text-indigo-300 border border-indigo-600/40
                       hover:bg-indigo-600/40 hover:text-white transition-colors"
          >
            <BarChart2 className="w-3.5 h-3.5" />
            Business Plan
          </button>
        )}
        {aiReady && (
          <button
            onClick={() => setShowAi(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       bg-violet-600/20 text-violet-300 border border-violet-600/40
                       hover:bg-violet-600/40 hover:text-white transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            AI Assist
          </button>
        )}
      </div>

      {/* ── Tags ────────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-1.5">
        {(job.tags ?? []).map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
                       bg-indigo-950 text-indigo-300 border border-indigo-800"
          >
            {tag}
            <button
              onClick={() => removeTag(tag)}
              className="text-indigo-500 hover:text-red-400 transition-colors"
              title="Remove tag"
            >×</button>
          </span>
        ))}
        <input
          className="h-6 w-28 px-2 rounded-full text-xs bg-gray-800 border border-gray-700
                     text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
          placeholder="+ add tag"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault()
              addTag(tagInput)
              setTagInput('')
            }
          }}
          maxLength={40}
        />
      </div>

      {/* ── Error ───────────────────────────────────────────────────────────── */}
      {job.error && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-lg p-3">
          <p className="text-xs font-medium text-red-400 mb-1">Error</p>
          <pre className="text-xs text-red-300 whitespace-pre-wrap break-words font-mono">
            {job.error}
          </pre>
        </div>
      )}

      {/* ── 3D Orbit Viewer ──────────────────────────────────────────────── */}
      {hasTles && (
        <section className="space-y-2">
          <h4 className="flex items-center gap-1.5 text-xs font-medium text-gray-500 uppercase tracking-wider">
            <Globe className="w-3.5 h-3.5" />
            Interactive 3D Orbit
          </h4>
          <OrbitViewer3D jobId={jobId} />
        </section>
      )}

      {/* ── Output files ────────────────────────────────────────────────────── */}
      {outputFiles.length > 0 && (
        <section className="space-y-4">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Output files</h4>
          <FileTabs jobId={jobId} files={outputFiles} />
        </section>
      )}

      {/* ── Log ─────────────────────────────────────────────────────────────── */}
      {logFile && (
        <section className="space-y-2">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Log</h4>
          <TextViewer jobId={jobId} filename={logFile.name} />
        </section>
      )}

      {/* ── Live log tail while running ─────────────────────────────────────── */}
      {(job.status === 'queued' || job.status === 'running') && job.log_tail && (
        <section className="space-y-2">
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider animate-pulse">
            Live output
          </h4>
          <pre className="text-xs text-gray-400 bg-gray-950 rounded-lg p-3 max-h-48 overflow-auto font-mono whitespace-pre-wrap">
            {job.log_tail}
          </pre>
        </section>
      )}

      {/* ── TCO Business Plan Modal ─────────────────────────────────────────── */}
      {showTco && <TcoDashboardModal jobId={jobId} onClose={() => setShowTco(false)} />}

      {/* ── AI Analysis Modal ────────────────────────────────────────────── */}
      {showAi && (
        <AiAnalysisModal
          jobId={jobId}
          onClose={() => setShowAi(false)}
        />
      )}
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued:    'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    running:   'bg-blue-500/20   text-blue-300   border-blue-500/30',
    completed: 'bg-green-500/20  text-green-300  border-green-500/30',
    failed:    'bg-red-500/20    text-red-300    border-red-500/30',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${colors[status] ?? ''}`}>
      {status === 'running' && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
      )}
      {status}
    </span>
  )
}

function FileTabs({ jobId, files }: { jobId: string; files: JobFile[] }) {
  const [active, setActive] = useActiveFile(files)

  return (
    <div>
      {/* Tab bar */}
      <div className="flex gap-1 flex-wrap mb-3">
        {files.map((f) => (
          <button
            key={f.name}
            onClick={() => setActive(f.name)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs transition-colors ${
              active === f.name
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {fileIcon(f.type)}
            {f.name}
          </button>
        ))}
      </div>

      {/* Viewer */}
      {files.map((f) =>
        f.name === active ? <FileViewer key={f.name} jobId={jobId} file={f} /> : null,
      )}
    </div>
  )
}

function useActiveFile(files: JobFile[]): [string | undefined, (n: string) => void] {
  return useState<string | undefined>(files[0]?.name)
}
