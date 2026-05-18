import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { X, FileText, Loader2 } from 'lucide-react'
import { submitJob, saveReport } from '../api/client'
import { useReportStore } from '../store/reportStore'
import type { OptionsResponse, HeatmapRequest, HeatmapRfRequest, OrbitRequest, RouteRequest, ShellDef } from '../types'
import type { ReportState } from '../types'

// ── helpers ────────────────────────────────────────────────────────────────────
type Backend = 'matplotlib' | 'plotly' | 'bokeh'

function buildConstellationBase(params: Record<string, unknown>) {
  const backendRaw = params.backend as string | undefined
  const backend: Backend = (backendRaw === 'plotly' || backendRaw === 'bokeh')
    ? backendRaw : 'matplotlib'
  return {
    sats:         params.sats         as number,
    planes:       params.planes       as number,
    altitude:     params.altitude     as number,
    inclination:  params.inclination  as number,
    phasing:      params.phasing      as number,
    sso:          (params.sso         as boolean) ?? false,
    backend,
    constellation:      (params.constellation      as string | null) || undefined,
    constellation_name: (params.constellation_name as string | null) || undefined,
    shells:             (params.shells as ShellDef[] | null) || undefined,
    max_sats:     (params.max_sats as number) || 250,
  }
}

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  params: Record<string, unknown>
  opts:   OptionsResponse
  onClose: () => void
}

export default function ReportConfirmModal({ params, opts, onClose }: Props) {
  const qc            = useQueryClient()
  const { addReport, updateJobId } = useReportStore()
  const [running,   setRunning]   = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [failed,    setFailed]    = useState(false)

  const selectedRoutes = (params.reportRoutes as string[]) ?? ['titan_corridor', 'roaring_passage', 'borealis_run']
  const comms          = (params.comms as string) || opts.comms_payloads[0]
  const label          = (params.constellation_name as string)
                      || (params.constellation    as string)
                      || 'custom'

  const allJobs = [
    { key: 'heatmap',     label: 'Coverage Heatmap' },
    { key: 'heatmapRf',  label: 'RF Link Budget Heatmap' },
    { key: 'orbit',       label: 'Orbit Animation + Business Plan' },
    ...selectedRoutes.map((r) => ({ key: `route:${r}`, label: `Route: ${r}` })),
  ]

  async function handleConfirm() {
    setRunning(true)
    setFailed(false)
    const base = buildConstellationBase(params)

    const reportId = `report-${Date.now()}`
    const initial: ReportState = {
      reportId,
      label,
      createdAt:      new Date().toISOString(),
      params:         { ...params },
      selectedRoutes,
      jobs: { heatmap: null, heatmapRf: null, orbit: null, routes: {} },
    }
    addReport(initial)
    saveReport(initial).catch(console.error)  // visible on other devices immediately

    try {
      // 1 — heatmap (geometric)
      setStatusMsg('Submitting heatmap…')
      const heatmapBody: HeatmapRequest = {
        ...base,
        comms,
        weather:  (params.weather as string) || opts.weather_scenarios[0],
        res:      (params.res     as number) || 5,
        min_elev: (params.min_elev as number) || 10,
        bidi:     false,
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const hmRes = await submitJob({ mode: 'heatmap', ...heatmapBody } as any)
      updateJobId(reportId, 'heatmap', hmRes.job_id)

      // 1b — heatmap-rf (RF link budget)
      setStatusMsg('Submitting RF heatmap…')
      const heatmapRfBody: HeatmapRfRequest = {
        ...base,
        comms,
        weather:  (params.weather as string) || opts.weather_scenarios[0],
        res:      (params.res     as number) || 5,
        min_elev: (params.min_elev as number) || 10,
        bidi:     false,
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const hmRfRes = await submitJob({ mode: 'heatmap-rf', ...heatmapRfBody } as any)
      updateJobId(reportId, 'heatmapRf', hmRfRes.job_id)

      // 2 — orbit
      setStatusMsg('Submitting orbit…')
      const orbitBody: OrbitRequest = {
        ...base,
        comms,
        platform: (params.platform as string) || opts.platforms[0],
        min_elev: (params.min_elev as number) || 10,
        duration: 120,   // 2 h in minutes
        trails:   true,
        map:      true,
        beams:    false,
        fill:     false,
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const orRes = await submitJob({ mode: 'orbit', ...orbitBody } as any)
      updateJobId(reportId, 'orbit', orRes.job_id)

      // 3 — routes (parallel)
      setStatusMsg('Submitting routes…')
      await Promise.all(
        selectedRoutes.map(async (route) => {
          const routeBody: RouteRequest = {
            ...base,
            route,
            comms,
            weather:  (params.weather as string) || opts.weather_scenarios[0],
            duration: 86400,  // 24 h in seconds
            speed:    12,
            min_elev: (params.min_elev as number) || 10,
            bidi:     false,
            trails:   false,
          }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rRes = await submitJob({ mode: 'route', ...routeBody } as any)
          updateJobId(reportId, 'routes', rRes.job_id, route)
        }),
      )

      qc.invalidateQueries({ queryKey: ['jobs'] })

      // Persist final report (with all job IDs) to server
      const finalReport = useReportStore.getState().reports.find((r) => r.reportId === reportId)
      if (finalReport) saveReport(finalReport).catch(console.error)

      setStatusMsg('All jobs submitted!')
      onClose()
    } catch (err) {
      console.error(err)
      setFailed(true)
      setStatusMsg('A submission failed — check the console.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !running) onClose() }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">Generate Full Report</h2>
          </div>
          <button
            onClick={onClose}
            disabled={running}
            className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors disabled:opacity-40"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          <p className="text-sm text-gray-400">
            The following jobs will be submitted for{' '}
            <span className="text-indigo-300 font-medium">{label}</span>:
          </p>

          <ul className="space-y-2">
            {allJobs.map(({ key, label: jl }) => (
              <li key={key} className="flex items-center gap-2 text-sm text-gray-300">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
                {jl}
              </li>
            ))}
          </ul>

          {statusMsg && (
            <p className={`text-xs px-3 py-2 rounded-lg ${failed ? 'text-red-400 bg-red-900/30' : 'text-indigo-300 bg-indigo-900/30'}`}>
              {statusMsg}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 pb-5">
          <button
            onClick={onClose}
            disabled={running}
            className="flex-1 py-2 rounded-lg border border-gray-700 text-sm text-gray-300 hover:bg-gray-800 transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={running}
            className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm text-white font-medium transition-colors disabled:opacity-60"
          >
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
            {running ? 'Submitting…' : 'Confirm & Submit'}
          </button>
        </div>
      </div>
    </div>
  )
}
