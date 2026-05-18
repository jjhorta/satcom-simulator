import { useState, useRef, useEffect } from 'react'
import { FileText, Trash2, ExternalLink, Pencil, Check, X, Tag } from 'lucide-react'
import { useReportStore } from '../store/reportStore'
import { deleteReport, saveReport } from '../api/client'
import type { ReportState } from '../types'

// ── helpers ───────────────────────────────────────────────────────────────────

function countJobs(report: ReportState): { total: number; submitted: number } {
  const total     = 3 + report.selectedRoutes.length  // heatmap + heatmapRf + orbit + routes
  const submitted = [
    report.jobs.heatmap,
    report.jobs.heatmapRf,
    report.jobs.orbit,
    ...Object.values(report.jobs.routes),
  ].filter(Boolean).length
  return { total, submitted }
}

function StatusBadge({ submitted, total }: { submitted: number; total: number }) {
  const done = submitted === total
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
        done
          ? 'bg-green-500/20 text-green-300 border-green-500/40'
          : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
      }`}
    >
      {submitted}/{total} jobs
      {done && ' ✓'}
    </span>
  )
}

// Tag chip colours — cycle through a small palette
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

// ── Inline title editor ───────────────────────────────────────────────────────

function TitleCell({
  report,
  onChange,
}: {
  report:   ReportState
  onChange: (title: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft,   setDraft]   = useState(report.title ?? report.label)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) inputRef.current?.select()
  }, [editing])

  function commit() {
    const trimmed = draft.trim() || report.label
    setDraft(trimmed)
    setEditing(false)
    onChange(trimmed)
  }

  const display = report.title ?? report.label
  const tags    = report.tags ?? []

  return (
    <div className="flex flex-col gap-1 min-w-0">
      {editing ? (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit()
              if (e.key === 'Escape') { setEditing(false); setDraft(report.title ?? report.label) }
            }}
            onBlur={commit}
            className="flex-1 min-w-0 px-2 py-0.5 rounded bg-gray-800 border border-indigo-600 text-sm text-white focus:outline-none"
          />
          <button onMouseDown={(e) => { e.preventDefault(); commit() }} className="text-green-400">
            <Check className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 group">
          <FileText className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
          <span className="text-sm font-medium text-gray-200 truncate max-w-[160px]">{display}</span>
          <button
            onClick={(e) => { e.stopPropagation(); setEditing(true) }}
            className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-gray-300 transition-opacity"
            title="Rename"
          >
            <Pencil className="w-3 h-3" />
          </button>
        </div>
      )}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 pl-5">
          {tags.map((tag) => (
            <span
              key={tag}
              className={`inline-flex items-center px-1.5 py-0 rounded text-[10px] font-medium border ${tagColour(tag)}`}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Row ───────────────────────────────────────────────────────────────────────

function ReportRow({
  report,
  viewing,
  onOpen,
  onDelete,
  onTitleChange,
}: {
  report:        ReportState
  viewing:       boolean
  onOpen:        () => void
  onDelete:      () => void
  onTitleChange: (title: string) => void
}) {
  const { total, submitted } = countJobs(report)
  const ts = new Date(report.createdAt).toLocaleString()

  return (
    <tr
      className={`cursor-pointer transition-colors border-b border-gray-800 ${
        viewing ? 'bg-indigo-600/20' : 'hover:bg-gray-800/50'
      }`}
      onClick={onOpen}
    >
      {/* Name + tags */}
      <td className="px-4 py-3">
        <TitleCell report={report} onChange={onTitleChange} />
      </td>

      {/* Routes */}
      <td className="px-2 py-3 text-sm text-gray-400 hidden sm:table-cell">
        {report.selectedRoutes.length} route{report.selectedRoutes.length !== 1 ? 's' : ''}
      </td>

      {/* Status */}
      <td className="px-2 py-3">
        <StatusBadge submitted={submitted} total={total} />
      </td>

      {/* Created */}
      <td className="px-2 py-3 text-xs text-gray-500 hidden md:table-cell">{ts}</td>

      {/* Actions */}
      <td className="px-2 py-3">
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); onOpen() }}
            className="text-gray-500 hover:text-indigo-400 transition-colors"
            title="Open report"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            className="text-gray-600 hover:text-red-400 transition-colors"
            title="Delete report"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  )
}

// ── Tag filter bar ────────────────────────────────────────────────────────────

function TagFilterBar({
  allTags,
  activeTags,
  onToggle,
  onClear,
}: {
  allTags:   string[]
  activeTags: string[]
  onToggle:  (t: string) => void
  onClear:   () => void
}) {
  if (allTags.length === 0) return null
  return (
    <div className="flex items-center gap-2 flex-wrap mb-3">
      <Tag className="w-3.5 h-3.5 text-gray-600 flex-shrink-0" />
      {allTags.map((tag) => {
        const active = activeTags.includes(tag)
        return (
          <button
            key={tag}
            onClick={() => onToggle(tag)}
            className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border transition-all ${
              active
                ? tagColour(tag) + ' ring-1 ring-inset ring-white/20'
                : 'bg-gray-800/60 text-gray-500 border-gray-700 hover:text-gray-300'
            }`}
          >
            {tag}
          </button>
        )
      })}
      {activeTags.length > 0 && (
        <button onClick={onClear} className="text-xs text-gray-500 hover:text-white flex items-center gap-0.5">
          <X className="w-3 h-3" /> Clear
        </button>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReportList() {
  const reports         = useReportStore((s) => s.reports)
  const viewingId       = useReportStore((s) => s.viewingId)
  const openViewer      = useReportStore((s) => s.openViewer)
  const removeReport    = useReportStore((s) => s.removeReport)
  const updateReportMeta = useReportStore((s) => s.updateReportMeta)

  const [filterTags, setFilterTags] = useState<string[]>([])

  // Collect all unique tags across all reports
  const allTags = Array.from(
    new Set(reports.flatMap((r) => r.tags ?? []))
  ).sort()

  // Filter reports by active tags
  const visible = filterTags.length > 0
    ? reports.filter((r) => filterTags.every((t) => (r.tags ?? []).includes(t)))
    : reports

  function handleTitleChange(reportId: string, title: string) {
    const report = reports.find((r) => r.reportId === reportId)
    if (!report) return
    updateReportMeta(reportId, { title })
    saveReport({ ...report, title }).catch(console.error)
  }

  if (reports.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800 p-8 text-center">
        <FileText className="w-8 h-8 text-gray-700 mx-auto mb-3" />
        <p className="text-sm text-gray-500">No reports yet.</p>
        <p className="text-xs text-gray-600 mt-1">
          Select <span className="text-indigo-400">Full Report</span> mode from the left panel to generate one.
        </p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Reports
        </h2>
        <span className="text-xs text-gray-600">{reports.length} saved</span>
      </div>

      <TagFilterBar
        allTags={allTags}
        activeTags={filterTags}
        onToggle={(t) => setFilterTags((p) => p.includes(t) ? p.filter((x) => x !== t) : [...p, t])}
        onClear={() => setFilterTags([])}
      />

      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900 border-b border-gray-800">
            <tr>
              <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase tracking-wider">Name</th>
              <th className="px-2 py-2 text-left text-xs text-gray-500 uppercase tracking-wider hidden sm:table-cell">Routes</th>
              <th className="px-2 py-2 text-left text-xs text-gray-500 uppercase tracking-wider">Jobs</th>
              <th className="px-2 py-2 text-left text-xs text-gray-500 uppercase tracking-wider hidden md:table-cell">Created</th>
              <th className="px-2 py-2" />
            </tr>
          </thead>
          <tbody className="bg-gray-950/40">
            {visible.map((report) => (
              <ReportRow
                key={report.reportId}
                report={report}
                viewing={report.reportId === viewingId}
                onOpen={() => openViewer(report.reportId)}
                onDelete={() => {
                  removeReport(report.reportId)
                  deleteReport(report.reportId).catch(console.error)
                }}
                onTitleChange={(title) => handleTitleChange(report.reportId, title)}
              />
            ))}
          </tbody>
        </table>
        {visible.length === 0 && filterTags.length > 0 && (
          <div className="py-8 text-center text-sm text-gray-500">
            No reports match the selected tags.
          </div>
        )}
      </div>
    </div>
  )
}

