import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ReportState, ReportJobMap } from '../types'

interface ReportStore {
  reports:   ReportState[]
  viewingId: string | null

  loadReports:      (reports: ReportState[]) => void
  addReport:        (state: ReportState) => void
  updateJobId:      (reportId: string, field: keyof ReportJobMap, value: string, routeKey?: string) => void
  updateReportMeta: (reportId: string, patch: { title?: string; tags?: string[]; notes?: string; shareToken?: string }) => void
  setAiInsights:    (reportId: string, text: string) => void
  openViewer:       (id: string) => void
  closeViewer:      () => void
  removeReport:     (id: string) => void
}

export const useReportStore = create<ReportStore>()(
  persist(
    (set) => ({
      reports:   [],
      viewingId: null,

      loadReports: (reports) => set({ reports }),

      addReport: (state) =>
        set((s) => ({
          reports:   [state, ...s.reports],
          viewingId: state.reportId,
        })),

      openViewer:   (id) => set({ viewingId: id }),
      closeViewer:  ()   => set({ viewingId: null }),
      removeReport: (id) =>
        set((s) => ({
          reports:   s.reports.filter((r) => r.reportId !== id),
          viewingId: s.viewingId === id ? null : s.viewingId,
        })),

      updateReportMeta: (reportId, patch) =>
        set((s) => ({
          reports: s.reports.map((r) =>
            r.reportId === reportId ? { ...r, ...patch } : r,
          ),
        })),

      updateJobId: (reportId, field, value, routeKey) =>
        set((s) => ({
          reports: s.reports.map((r) => {
            if (r.reportId !== reportId) return r
            if (field === 'routes' && routeKey) {
              return { ...r, jobs: { ...r.jobs, routes: { ...r.jobs.routes, [routeKey]: value } } }
            }
            return { ...r, jobs: { ...r.jobs, [field]: value } }
          }),
        })),

      setAiInsights: (reportId, text) =>
        set((s) => ({
          reports: s.reports.map((r) =>
            r.reportId === reportId ? { ...r, aiInsights: text } : r,
          ),
        })),
    }),
    { name: 'constellation-report-store' },
  ),
)
