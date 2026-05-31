import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listJobs, deleteJob } from '../api/client'
import type { JobListItem, JobStatusValue } from '../types'
import { Trash2, RefreshCw, X, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import clsx from 'clsx'

const STATUS_COLORS: Record<JobStatusValue, string> = {
  queued:    'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
  running:   'bg-blue-500/20   text-blue-300   border-blue-500/40',
  completed: 'bg-green-500/20  text-green-300  border-green-500/40',
  failed:    'bg-red-500/20    text-red-300    border-red-500/40',
}

const MODE_LABELS: Record<string, string> = {
  heatmap: 'Heatmap', 'heatmap-rf': 'RF Heatmap', sky: 'Sky', orbit: 'Orbit', track: 'Track', route: 'Route',
}

// ── Sort types ────────────────────────────────────────────────────────────────

type SortCol = 'mode' | 'status' | 'created_at'
type SortDir = 'asc' | 'desc'

const STATUS_ORDER: Record<JobStatusValue, number> = {
  running: 0, queued: 1, completed: 2, failed: 3,
}

function sortJobs(jobs: JobListItem[], col: SortCol, dir: SortDir): JobListItem[] {
  return [...jobs].sort((a, b) => {
    let cmp = 0
    if (col === 'created_at') {
      cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    } else if (col === 'mode') {
      cmp = a.mode.localeCompare(b.mode)
    } else if (col === 'status') {
      cmp = (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9)
    }
    return dir === 'asc' ? cmp : -cmp
  })
}

// ── Sort header cell ──────────────────────────────────────────────────────────

function SortTh({
  col, label, active, dir, onSort, className,
}: {
  col: SortCol; label: string; active: boolean; dir: SortDir
  onSort: (col: SortCol) => void; className?: string
}) {
  const Icon = active ? (dir === 'asc' ? ChevronUp : ChevronDown) : ChevronsUpDown
  return (
    <th
      className={clsx('px-2 py-2 text-left select-none', className)}
      onClick={() => onSort(col)}
    >
      <button className="flex items-center gap-1 text-xs text-gray-500 uppercase tracking-wider hover:text-gray-300 transition-colors">
        {label}
        <Icon className={clsx('w-3 h-3', active ? 'text-indigo-400' : 'text-gray-600')} />
      </button>
    </th>
  )
}

// ── Row ───────────────────────────────────────────────────────────────────────

function JobRow({
  job, selected, onSelect, onDelete,
}: {
  job: JobListItem
  selected: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  const ts = new Date(job.created_at).toLocaleString()
  return (
    <tr
      className={clsx(
        'cursor-pointer transition-colors border-b border-gray-800',
        selected ? 'bg-indigo-600/20' : 'hover:bg-gray-800/50',
      )}
      onClick={onSelect}
    >
      <td className="px-4 py-3 text-sm font-mono text-gray-400 truncate max-w-[120px]">
        {job.job_id.slice(0, 8)}
      </td>
      <td className="px-2 py-3 text-sm text-gray-200">
        <span>{MODE_LABELS[job.mode] ?? job.mode}</span>
        {job.title && (
          <span className="block text-xs text-gray-500 truncate max-w-[160px]">{job.title}</span>
        )}
        {job.tags && job.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {job.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="px-1.5 py-0 rounded text-[10px] font-medium bg-gray-800 text-gray-500 border border-gray-700"
              >
                {tag}
              </span>
            ))}
            {job.tags.length > 4 && (
              <span className="text-[10px] text-gray-600">+{job.tags.length - 4}</span>
            )}
          </div>
        )}
      </td>
      <td className="px-2 py-3">
        <span className={clsx(
          'inline-block px-2 py-0.5 rounded-full text-xs font-medium border',
          STATUS_COLORS[job.status],
        )}>
          {job.status}
        </span>
      </td>
      <td className="px-2 py-3 text-xs text-gray-500 hidden sm:table-cell">{ts}</td>
      <td className="px-2 py-3">
        <button
          onClick={(e) => { e.stopPropagation(); onDelete() }}
          className="text-gray-600 hover:text-red-400 transition-colors"
          title="Delete job"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </td>
    </tr>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function JobList({
  onSelectJob,
  selectedJobId,
}: {
  onSelectJob: (id: string) => void
  selectedJobId: string | null
}) {
  const qc = useQueryClient()
  const [activeTag,   setActiveTag]   = useState<string | null>(null)
  const [sortCol,     setSortCol]     = useState<SortCol>('created_at')
  const [sortDir,     setSortDir]     = useState<SortDir>('desc')
  const [pageSize,    setPageSize]    = useState(20)
  const [page,        setPage]        = useState(1)

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn:  listJobs,
    refetchInterval: 3000,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })

  const handleSort = (col: SortCol) => {
    if (col === sortCol) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortCol(col)
      setSortDir(col === 'created_at' ? 'desc' : 'asc')
    }
  }

  // Collect all unique tags across all jobs
  const allTags = Array.from(new Set(jobs.flatMap((j) => j.tags ?? []))).sort()

  // Filter by active tag, then sort
  const filtered = activeTag ? jobs.filter((j) => (j.tags ?? []).includes(activeTag)) : jobs
  const sorted  = sortJobs(filtered, sortCol, sortDir)
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const visible = sorted.slice((safePage - 1) * pageSize, safePage * pageSize)

  if (isLoading) {
    return <p className="text-sm text-gray-500 animate-pulse">Loading jobs…</p>
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Simulations
        </h2>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ['jobs'] })}
          className="text-gray-500 hover:text-white transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Tag filter bar */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setActiveTag(activeTag === tag ? null : tag)}
              className={clsx(
                'flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors border',
                activeTag === tag
                  ? 'bg-indigo-600 text-white border-indigo-500'
                  : 'bg-gray-800 text-gray-400 border-gray-700 hover:text-white hover:border-gray-500',
              )}
            >
              {tag}
              {activeTag === tag && <X className="w-3 h-3" />}
            </button>
          ))}
        </div>
      )}

      {visible.length === 0 ? (
        <div className="rounded-lg border border-gray-800 p-8 text-center">
          <p className="text-sm text-gray-500">
            {activeTag ? `No simulations tagged "${activeTag}".` : 'No simulations yet.'}
          </p>
          {!activeTag && (
            <p className="text-xs text-gray-600 mt-1">
              Configure and run a simulation from the left panel.
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-800/60">
                <th className="px-4 py-2 text-left text-xs text-gray-500 uppercase tracking-wider">ID</th>
                <SortTh col="mode"       label="Mode"    active={sortCol === 'mode'}       dir={sortDir} onSort={handleSort} />
                <SortTh col="status"     label="Status"  active={sortCol === 'status'}     dir={sortDir} onSort={handleSort} />
                <SortTh col="created_at" label="Created" active={sortCol === 'created_at'} dir={sortDir} onSort={handleSort} className="hidden sm:table-cell" />
                <th className="px-2 py-2" />
              </tr>
            </thead>
            <tbody>
              {visible.map((j) => (
                <JobRow
                  key={j.job_id}
                  job={j}
                  selected={j.job_id === selectedJobId}
                  onSelect={() => onSelectJob(j.job_id)}
                  onDelete={() => deleteMutation.mutate(j.job_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {/* Pagination */}
      <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
        <div className="flex items-center gap-2">
          <span>Show</span>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300 focus:outline-none focus:border-indigo-500"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span>of {sorted.length} jobs</span>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            >
              ‹ Prev
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const start = Math.max(1, Math.min(safePage - 2, totalPages - 4))
              const p = start + i
              if (p > totalPages) return null
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-2 py-1 rounded transition-colors ${
                    p === safePage ? 'bg-indigo-600 text-white' : 'hover:bg-gray-800 text-gray-400'
                  }`}
                >
                  {p}
                </button>
              )
            })}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              className="px-2 py-1 rounded hover:bg-gray-800 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            >
              Next ›
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

