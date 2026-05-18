/**
 * FullReportViewer — assembles all sub-jobs into a pageable report.
 * Polling is done with TanStack Query (refetchInterval).
 * PDF export uses window.print() + @media print CSS.
 */
import { useEffect, useRef, useState } from 'react'
import { useQuery }                    from '@tanstack/react-query'
import {
  X, Printer, Loader2, CheckCircle2, AlertCircle, Sparkles,
  Pencil, Check, Tag, Share2, StickyNote, ChevronDown, ChevronRight,
} from 'lucide-react'
import { getJob, fetchTco, fetchCsv, fileUrl, aiStreamUrl, fetchAiAnalysis, saveReport } from '../../api/client'
import { useReportStore }              from '../../store/reportStore'
import { useAiStore }                  from '../../store/aiStore'
import { useAuthStore }                from '../../store/authStore'
import OrbitViewer3D                   from './OrbitViewer3D'
import { TcoDashboardContent }         from './TcoDashboardModal'
import ShareReportModal                from '../ShareReportModal'
import type { JobStatus }              from '../../types'

// ── helpers ────────────────────────────────────────────────────────────────────
function statusDone(s: JobStatus | undefined)   { return s?.status === 'completed' }
function statusFailed(s: JobStatus | undefined) { return s?.status === 'failed' }

function JobStatusBadge({ status }: { status: string | undefined }) {
  if (!status) return <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
  if (status === 'completed')
    return <CheckCircle2 className="w-4 h-4 text-emerald-400" />
  if (status === 'failed')
    return <AlertCircle className="w-4 h-4 text-red-400" />
  return <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
}

// ── Route summary row ──────────────────────────────────────────────────────────
interface RouteRow {
  sequence:         number
  waypoint:         string
  connectivity_pct: number
}

function RouteSummaryRow({ jobId, routeName }: { jobId: string; routeName: string }) {
  const jobQ = useQuery<JobStatus>({
    queryKey: ['job', jobId],
    queryFn:  () => getJob(jobId),
    refetchInterval: (q) => (q.state.data?.status === 'completed' || q.state.data?.status === 'failed') ? false : 4000,
  })
  const csvFile = jobQ.data?.files?.find((f) => f.name.endsWith('.csv'))
  const csvQ = useQuery<RouteRow[]>({
    queryKey: ['csv', jobId, csvFile?.name],
    queryFn:  () => fetchCsv(jobId, csvFile!.name) as unknown as Promise<RouteRow[]>,
    enabled:  !!csvFile,
  })

  const rows  = csvQ.data ?? []
  const avg   = rows.length ? rows.reduce((s, r) => s + r.connectivity_pct, 0) / rows.length : null
  const wpts  = rows.length

  return (
    <tr className="border-t border-gray-800">
      <td className="py-2 pr-4 text-sm text-gray-300">{routeName}</td>
      <td className="py-2 pr-4">
        <JobStatusBadge status={jobQ.data?.status} />
      </td>
      <td className="py-2 pr-4 text-sm tabular-nums text-gray-300">
        {avg !== null ? `${avg.toFixed(1)}%` : '—'}
      </td>
      <td className="py-2 text-sm tabular-nums text-gray-500">{wpts || '—'}</td>
    </tr>
  )
}

// ── Section wrapper ────────────────────────────────────────────────────────────
function ReportSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="report-section print:break-before-page">
      <h2 className="text-sm font-semibold text-indigo-400 uppercase tracking-widest mb-4 pb-2 border-b border-gray-800">
        {title}
      </h2>
      {children}
    </section>
  )
}

// ── Simple inline markdown renderer ─────────────────────────────────────────
function MarkdownContent({ text }: { text: string }) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    // Skip blank lines between blocks
    if (line.trim() === '') { i++; continue }
    // Headings
    if (line.startsWith('### ')) {
      elements.push(<h3 key={i} className="text-sm font-semibold text-indigo-300 mt-4 mb-1">{inlineFormat(line.slice(4))}</h3>)
      i++; continue
    }
    if (line.startsWith('## ')) {
      elements.push(<h2 key={i} className="text-base font-semibold text-indigo-200 mt-5 mb-2 border-b border-gray-800 pb-1">{inlineFormat(line.slice(3))}</h2>)
      i++; continue
    }
    if (line.startsWith('# ')) {
      elements.push(<h1 key={i} className="text-lg font-bold text-white mt-5 mb-2">{inlineFormat(line.slice(2))}</h1>)
      i++; continue
    }
    // Unordered list — collect consecutive items
    if (line.match(/^[-*] /)) {
      const items: React.ReactNode[] = []
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        items.push(<li key={i} className="text-sm text-gray-300 leading-relaxed">{inlineFormat(lines[i].slice(2))}</li>)
        i++
      }
      elements.push(<ul key={`ul-${i}`} className="list-disc list-inside space-y-0.5 my-2 pl-1">{items}</ul>)
      continue
    }
    // Numbered list
    if (line.match(/^\d+\. /)) {
      const items: React.ReactNode[] = []
      while (i < lines.length && lines[i].match(/^\d+\. /)) {
        items.push(<li key={i} className="text-sm text-gray-300 leading-relaxed">{inlineFormat(lines[i].replace(/^\d+\. /, ''))}</li>)
        i++
      }
      elements.push(<ol key={`ol-${i}`} className="list-decimal list-inside space-y-0.5 my-2 pl-1">{items}</ol>)
      continue
    }
    // Paragraph
    elements.push(<p key={i} className="text-sm text-gray-300 leading-relaxed my-1.5">{inlineFormat(line)}</p>)
    i++
  }
  return <div className="space-y-0.5">{elements}</div>
}

function inlineFormat(text: string): React.ReactNode {
  // Handle **bold** and *italic* inline
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={idx} className="text-white font-semibold">{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*'))
      return <em key={idx} className="text-gray-200 italic">{part.slice(1, -1)}</em>
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={idx} className="px-1 py-0.5 rounded bg-gray-800 text-indigo-300 text-xs font-mono">{part.slice(1, -1)}</code>
    return part
  })
}

// ── AI Insights panel ─────────────────────────────────────────────────────────
function AiInsightsPanel({ orbitJobId, reportId }: { orbitJobId: string; reportId: string }) {
  const ai     = useAiStore()
  const token  = useAuthStore((s) => s.token)
  const { setAiInsights } = useReportStore()

  const [text,    setText]    = useState('')
  const [status,  setStatus]  = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [errMsg,  setErrMsg]  = useState('')
  const accumRef = useRef('')

  // Load cached on mount
  useEffect(() => {
    fetchAiAnalysis(orbitJobId).then((saved) => {
      if (saved) { setText(saved); setStatus('done'); setAiInsights(reportId, saved) }
      else if (ai.keyIsSet) runAnalysis()
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orbitJobId])

  async function runAnalysis() {
    setStatus('loading'); setText(''); setErrMsg(''); accumRef.current = ''
    try {
      const url  = aiStreamUrl(orbitJobId)
      const resp = await fetch(url, {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (!resp.ok) {
        const body = await resp.text().catch(() => '')
        let detail = body
        try { detail = JSON.parse(body).detail ?? body } catch { /* ignore */ }
        throw new Error(detail.slice(0, 300))
      }
      const reader  = resp.body?.getReader()
      const decoder = new TextDecoder()
      let   buf     = ''
      while (reader) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n'); buf = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') break
          try {
            const chunk = JSON.parse(data)
            if (chunk.error) throw new Error(chunk.error)
            const delta = chunk.delta ?? ''
            if (delta) { accumRef.current += delta; setText((t) => t + delta) }
          } catch (e) {
            if ((e as Error).message !== 'Unexpected token') throw e
          }
        }
      }
      setStatus('done')
      setAiInsights(reportId, accumRef.current)
    } catch (e) {
      setErrMsg((e as Error).message ?? 'Unknown error.')
      setStatus('error')
    }
  }

  if (!ai.keyIsSet) {
    return (
      <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-gray-800/60 border border-gray-700/50 text-sm text-gray-400">
        <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0" />
        <span>AI insights are not configured. Add an OpenAI API key in Settings to enable this section.</span>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="px-4 py-3 rounded-lg bg-red-900/20 border border-red-700/40 text-sm text-red-400">
        AI error: {errMsg}
        <button onClick={runAnalysis} className="ml-3 underline hover:no-underline">Retry</button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {status === 'loading' && (
        <div className="flex items-center gap-2 text-sm text-indigo-300">
          <Loader2 className="w-4 h-4 animate-spin" />
          Generating AI analysis…
        </div>
      )}
      {text && <MarkdownContent text={text} />}
    </div>
  )
}

// ── Tag chip colours ───────────────────────────────────────────────────────────
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

// ── Main component ─────────────────────────────────────────────────────────────
export default function FullReportViewer() {
  const reports          = useReportStore((s) => s.reports)
  const viewingId        = useReportStore((s) => s.viewingId)
  const closeViewer      = useReportStore((s) => s.closeViewer)
  const updateReportMeta = useReportStore((s) => s.updateReportMeta)
  const report           = reports.find((r) => r.reportId === viewingId) ?? null

  // Editable title
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft,   setTitleDraft]   = useState('')
  const titleInputRef = useRef<HTMLInputElement>(null)

  // Editable tags
  const [tagInput, setTagInput] = useState('')

  // Notes section
  const [notesOpen, setNotesOpen] = useState(false)
  const [notesDraft, setNotesDraft] = useState('')
  const notesTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Share modal
  const [showShare, setShowShare] = useState(false)

  useEffect(() => {
    if (report) setNotesDraft(report.notes ?? '')
  }, [report?.reportId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (editingTitle) titleInputRef.current?.select()
  }, [editingTitle])

  function commitTitle() {
    if (!report) return
    const title = titleDraft.trim() || report.label
    setEditingTitle(false)
    updateReportMeta(report.reportId, { title })
    saveReport({ ...report, title }).catch(console.error)
  }

  function addTag() {
    if (!report) return
    const tag = tagInput.trim()
    if (!tag) return
    const tags = [...new Set([...(report.tags ?? []), tag])]
    updateReportMeta(report.reportId, { tags })
    saveReport({ ...report, tags }).catch(console.error)
    setTagInput('')
  }

  function removeTag(tag: string) {
    if (!report) return
    const tags = (report.tags ?? []).filter((t) => t !== tag)
    updateReportMeta(report.reportId, { tags })
    saveReport({ ...report, tags }).catch(console.error)
  }

  function handleNotesChange(value: string) {
    setNotesDraft(value)
    if (notesTimerRef.current) clearTimeout(notesTimerRef.current)
    notesTimerRef.current = setTimeout(() => {
      if (!report) return
      updateReportMeta(report.reportId, { notes: value })
      saveReport({ ...report, notes: value }).catch(console.error)
    }, 800)
  }

  const heatmapJobId   = report?.jobs.heatmap   ?? null
  const heatmapRfJobId = report?.jobs.heatmapRf ?? null
  const orbitJobId     = report?.jobs.orbit      ?? null
  const routeJobs      = report?.jobs.routes     ?? {}

  // Poll heatmap job
  const heatmapQ = useQuery<JobStatus>({
    queryKey: ['job', heatmapJobId],
    queryFn:  () => getJob(heatmapJobId!),
    enabled:  !!heatmapJobId,
    refetchInterval: (q) => (statusDone(q.state.data) || statusFailed(q.state.data)) ? false : 4000,
  })

  // Poll heatmap-rf job
  const heatmapRfQ = useQuery<JobStatus>({
    queryKey: ['job', heatmapRfJobId],
    queryFn:  () => getJob(heatmapRfJobId!),
    enabled:  !!heatmapRfJobId,
    refetchInterval: (q) => (statusDone(q.state.data) || statusFailed(q.state.data)) ? false : 4000,
  })

  // Poll orbit job
  const orbitQ = useQuery<JobStatus>({
    queryKey: ['job', orbitJobId],
    queryFn:  () => getJob(orbitJobId!),
    enabled:  !!orbitJobId,
    refetchInterval: (q) => (statusDone(q.state.data) || statusFailed(q.state.data)) ? false : 4000,
  })

  // TCO data (once orbit is done)
  const tcoQ = useQuery({
    queryKey: ['tco', orbitJobId],
    queryFn:  () => fetchTco(orbitJobId!),
    enabled:  !!orbitJobId && statusDone(orbitQ.data),
  })

  if (!report) return null

  const heatmapImgFile = heatmapQ.data?.files?.find(
    (f) => f.name.endsWith('.png') || f.name.endsWith('.jpg'),
  )
  const heatmapImgUrl = heatmapImgFile && heatmapJobId
    ? fileUrl(heatmapJobId, heatmapImgFile.name)
    : null

  const heatmapRfImgFile = heatmapRfQ.data?.files?.find(
    (f) => f.name.endsWith('.png') || f.name.endsWith('.jpg'),
  )
  const heatmapRfImgUrl = heatmapRfImgFile && heatmapRfJobId
    ? fileUrl(heatmapRfJobId, heatmapRfImgFile.name)
    : null

  const totalRoutes   = report.selectedRoutes.length
  const completedRte  = report.selectedRoutes.filter(
    (r) => routeJobs[r] !== undefined,
  ).length

  // Progress stepper
  const steps = [
    { label: 'Heatmap',        status: heatmapQ.data?.status },
    { label: 'RF Heatmap',     status: heatmapRfQ.data?.status },
    { label: 'Orbit / TCO',    status: orbitQ.data?.status },
    { label: `Routes (${completedRte}/${totalRoutes})`, status:
      report.selectedRoutes.every((r) => routeJobs[r] !== undefined) ? 'queued' : 'queued' },
  ]

  return (
    <>
      {/* ── @media print styles ───────────────────────────────────────────── */}
      <style>{`
        @media print {
          body > * { display: none !important; }
          #full-report-print { display: block !important; }
          .no-print { display: none !important; }
          .report-section { page-break-before: always; }
          .report-section:first-of-type { page-break-before: avoid; }
          .orbit-viewer-note { display: block !important; }
        }
        #full-report-print { display: flex; flex-direction: column; }
        .orbit-viewer-note { display: none; }
      `}</style>

      <div
        id="full-report-print"
        className="fixed inset-0 z-40 bg-gray-950 flex flex-col overflow-hidden"
      >
        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="no-print border-b border-gray-800 flex-shrink-0">
          {/* Top row */}
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex-1 min-w-0">
              {/* Editable title */}
              {editingTitle ? (
                <div className="flex items-center gap-2">
                  <input
                    ref={titleInputRef}
                    value={titleDraft}
                    onChange={(e) => setTitleDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitTitle()
                      if (e.key === 'Escape') setEditingTitle(false)
                    }}
                    onBlur={commitTitle}
                    className="flex-1 max-w-xs px-2 py-0.5 rounded bg-gray-800 border border-indigo-600 text-base font-semibold text-white focus:outline-none"
                  />
                  <button onMouseDown={(e) => { e.preventDefault(); commitTitle() }} className="text-green-400">
                    <Check className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 group">
                  <h1 className="text-base font-semibold text-white truncate">
                    {report.title ?? report.label}
                    {report.title && report.title !== report.label && (
                      <span className="ml-2 text-xs text-indigo-400 font-normal">{report.label}</span>
                    )}
                  </h1>
                  <button
                    onClick={() => { setTitleDraft(report.title ?? report.label); setEditingTitle(true) }}
                    className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-gray-300 transition-opacity"
                    title="Rename"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
              <p className="text-xs text-gray-500 mt-0.5">
                Created {new Date(report.createdAt).toLocaleString()}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 ml-4">
              {/* Progress pills */}
              <div className="flex items-center gap-2 text-xs">
                {steps.map((s, i) => (
                  <div key={i} className="flex items-center gap-1 text-gray-400">
                    <JobStatusBadge status={s.status} />
                    <span>{s.label}</span>
                  </div>
                ))}
              </div>
              {/* Share */}
              <button
                onClick={() => setShowShare(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-300 hover:bg-gray-800 transition-colors"
                title="Share this report"
              >
                <Share2 className="w-3.5 h-3.5" />
                Share
              </button>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-300 hover:bg-gray-800 transition-colors"
              >
                <Printer className="w-3.5 h-3.5" />
                Export PDF
              </button>
              <button
                onClick={closeViewer}
                className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
                title="Close viewer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Tags row */}
          <div className="flex items-center gap-2 px-6 pb-2.5 flex-wrap">
            <Tag className="w-3.5 h-3.5 text-gray-600 flex-shrink-0" />
            {(report.tags ?? []).map((tag) => (
              <span
                key={tag}
                className={`inline-flex items-center gap-1 px-2 py-0 rounded text-[11px] font-medium border ${tagColour(tag)}`}
              >
                {tag}
                <button onClick={() => removeTag(tag)} className="opacity-60 hover:opacity-100 ml-0.5">
                  <X className="w-2.5 h-2.5" />
                </button>
              </span>
            ))}
            {/* Tag input */}
            <input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag() } }}
              onBlur={addTag}
              placeholder="Add tag…"
              className="px-2 py-0.5 text-[11px] bg-transparent border border-dashed border-gray-700 rounded text-gray-500 placeholder-gray-700 focus:outline-none focus:border-indigo-600 focus:text-white w-20"
            />
          </div>
        </div>

        {/* ── Body (scrollable) ───────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 space-y-10">

          {/* 1. Coverage Heatmap */}
          <ReportSection title="1 · Coverage Heatmap (Geometric)">
            {!heatmapJobId && (
              <p className="text-sm text-gray-500">No heatmap job submitted.</p>
            )}
            {heatmapJobId && !statusDone(heatmapQ.data) && !statusFailed(heatmapQ.data) && (
              <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin" />
                Heatmap running… (job {heatmapJobId.slice(0, 8)})
              </div>
            )}
            {statusFailed(heatmapQ.data) && (
              <p className="text-sm text-red-400">Heatmap simulation failed.</p>
            )}
            {heatmapImgUrl && (
              <img
                src={heatmapImgUrl}
                alt="Coverage heatmap"
                className="w-full rounded-lg border border-gray-800"
              />
            )}
          </ReportSection>

          {/* 1b. RF Link Budget Heatmap */}
          <ReportSection title="1b · RF Link Budget Heatmap">
            <p className="text-xs text-gray-500 mb-3">
              % time the downlink RF link budget closes (FSPL + rain attenuation + noise figure vs required SNR).
              Same geometry as heatmap but filtered by actual radio link feasibility.
            </p>
            {!heatmapRfJobId && (
              <p className="text-sm text-gray-500">No RF heatmap job submitted.</p>
            )}
            {heatmapRfJobId && !statusDone(heatmapRfQ.data) && !statusFailed(heatmapRfQ.data) && (
              <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin" />
                RF heatmap running… (job {heatmapRfJobId.slice(0, 8)})
              </div>
            )}
            {statusFailed(heatmapRfQ.data) && (
              <p className="text-sm text-red-400">RF heatmap simulation failed.</p>
            )}
            {heatmapRfImgUrl && (
              <img
                src={heatmapRfImgUrl}
                alt="RF link budget heatmap"
                className="w-full rounded-lg border border-gray-800"
              />
            )}
          </ReportSection>

          {/* 2. Orbit Visualisation */}
          <ReportSection title="2 · Orbit Visualisation">
            {!orbitJobId && (
              <p className="text-sm text-gray-500">No orbit job submitted.</p>
            )}
            {orbitJobId && !statusDone(orbitQ.data) && !statusFailed(orbitQ.data) && (
              <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin" />
                Orbit simulation running… (job {orbitJobId.slice(0, 8)})
              </div>
            )}
            {statusFailed(orbitQ.data) && (
              <p className="text-sm text-red-400">Orbit simulation failed.</p>
            )}
            {statusDone(orbitQ.data) && orbitJobId && (
              <>
                <div className="orbit-viewer-note text-xs text-gray-500 mb-2 hidden print:block">
                  [3D orbit viewer — interactive in browser]
                </div>
                <div className="print:hidden">
                  <OrbitViewer3D jobId={orbitJobId} />
                </div>
              </>
            )}
          </ReportSection>

          {/* 3. Business Plan */}
          <ReportSection title="3 · Business Plan (TCO)">
            {!orbitJobId && (
              <p className="text-sm text-gray-500">No orbit job — TCO unavailable.</p>
            )}
            {orbitJobId && !statusDone(orbitQ.data) && (
              <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin" />
                Waiting for orbit simulation to complete…
              </div>
            )}
            {tcoQ.isError && (
              <p className="text-sm text-red-400">TCO data not available for this job.</p>
            )}
            {tcoQ.data && <TcoDashboardContent data={tcoQ.data} />}
          </ReportSection>

          {/* 4. Maritime Routes */}
          <ReportSection title="4 · Maritime Route Analysis">
            {report.selectedRoutes.length === 0 ? (
              <p className="text-sm text-gray-500">No routes selected.</p>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase tracking-wider">
                    <th className="pb-2 pr-4">Route</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 pr-4">Avg. Connectivity</th>
                    <th className="pb-2">Waypoints</th>
                  </tr>
                </thead>
                <tbody>
                  {report.selectedRoutes.map((r) => {
                    const jobId = routeJobs[r]
                    if (!jobId) {
                      return (
                        <tr key={r} className="border-t border-gray-800">
                          <td className="py-2 pr-4 text-sm text-gray-300">{r}</td>
                          <td className="py-2 pr-4"><Loader2 className="w-4 h-4 animate-spin text-gray-600" /></td>
                          <td className="py-2 text-sm text-gray-600" colSpan={2}>—</td>
                        </tr>
                      )
                    }
                    return <RouteSummaryRow key={r} jobId={jobId} routeName={r} />
                  })}
                </tbody>
              </table>
            )}
          </ReportSection>

          {/* 5. AI Insights */}
          <ReportSection title="5 · AI Insights">
            {statusDone(orbitQ.data) && orbitJobId ? (
              <AiInsightsPanel orbitJobId={orbitJobId} reportId={report.reportId} />
            ) : (
              <p className="text-sm text-gray-500 animate-pulse">
                Waiting for orbit job to complete before running AI analysis…
              </p>
            )}
          </ReportSection>

          {/* 6. Notes */}
          <ReportSection title="6 · Notes">
            <div>
              <button
                onClick={() => setNotesOpen((o) => !o)}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-3 no-print"
              >
                {notesOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <StickyNote className="w-4 h-4 text-amber-400" />
                {notesOpen ? 'Hide notes' : 'Add / view notes'}
              </button>
              {notesOpen && (
                <textarea
                  value={notesDraft}
                  onChange={(e) => handleNotesChange(e.target.value)}
                  rows={6}
                  placeholder="Write your observations, conclusions, or follow-up actions here…"
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-200
                             placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-none no-print"
                />
              )}
              {report.notes && (
                <div className="prose-sm text-gray-300 text-sm leading-relaxed whitespace-pre-wrap print:block hidden print:visible">
                  {report.notes}
                </div>
              )}
            </div>
          </ReportSection>

        </div>
      </div>

      {/* Share modal */}
      {showShare && (
        <ShareReportModal reportId={report.reportId} onClose={() => setShowShare(false)} />
      )}
    </>
  )
}
