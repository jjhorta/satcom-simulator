import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { LogOut, Satellite, HelpCircle, Settings } from 'lucide-react'
import { useAuthStore }  from '../store/authStore'
import { useReportStore } from '../store/reportStore'
import { useAiStore }    from '../store/aiStore'
import { fetchAiConfig, fetchReports } from '../api/client'
import ConfigPanel      from '../components/ConfigPanel'
import JobList          from '../components/JobList'
import ReportList       from '../components/ReportList'
import JobDetail        from '../components/JobDetail'
import FullReportViewer from '../components/viewers/FullReportViewer'

export default function DashboardPage() {
  const logout      = useAuthStore((s) => s.logout)
  const reports     = useReportStore((s) => s.reports)
  const viewingId   = useReportStore((s) => s.viewingId)
  const loadReports = useReportStore((s) => s.loadReports)
  const aiStore     = useAiStore()
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [expanded,      setExpanded]      = useState(false)
  const [activeTab,     setActiveTab]     = useState<'simulations' | 'reports'>('simulations')

  // On login: load AI config + reports from server
  useEffect(() => {
    fetchAiConfig().then((cfg) => {
      aiStore.setStatus({
        keyIsSet:     cfg.key_is_set,
        maskedKey:    cfg.masked_key,
        model:        cfg.model,
        baseUrl:      cfg.base_url,
        systemPrompt: cfg.system_prompt,
      })
    }).catch(() => {})

    fetchReports().then(loadReports).catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Switch to Reports tab whenever a report is opened (new or existing)
  useEffect(() => {
    if (viewingId !== null) setActiveTab('reports')
  }, [viewingId])

  function handleClose() {
    setSelectedJobId(null)
    setExpanded(false)
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Satellite className="w-5 h-5 text-indigo-400" />
          <span className="font-semibold text-white">Constellation Simulator</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/settings"
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <Settings className="w-4 h-4" />
            Settings
          </Link>
          <Link
            to="/help"
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <HelpCircle className="w-4 h-4" />
            Help
          </Link>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </header>

      {/* ── Main layout ──────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Config panel — hidden when detail is expanded */}
        <aside className={`w-80 flex-shrink-0 border-r border-gray-800 overflow-y-auto bg-gray-900 ${expanded ? 'hidden' : ''}`}>
          <ConfigPanel />
        </aside>

        {/* Job list / Report list — hidden when detail is expanded */}
        <main className={`flex-1 overflow-y-auto p-6 flex flex-col ${expanded ? 'hidden' : ''}`}>
          {/* Tab bar */}
          <div className="flex gap-1 mb-5 flex-shrink-0">
            {(['simulations', 'reports'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                {tab === 'simulations' ? 'Simulations' : 'Reports'}
                {tab === 'reports' && reports.length > 0 && (
                  <span className="ml-0.5 bg-indigo-400/30 text-indigo-300 text-xs rounded-full px-1.5 py-0">
                    {reports.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Content */}
          {activeTab === 'simulations' ? (
            <JobList onSelectJob={setSelectedJobId} selectedJobId={selectedJobId} />
          ) : (
            <ReportList />
          )}
        </main>

        {/* Job detail — full width when expanded */}
        {selectedJobId && (
          <aside className={`flex-shrink-0 border-l border-gray-800 overflow-y-auto bg-gray-900 ${expanded ? 'flex-1 w-full' : 'w-[560px]'}`}>
            <JobDetail
              jobId={selectedJobId}
              onClose={handleClose}
              expanded={expanded}
              onToggleExpand={() => setExpanded((e) => !e)}
            />
          </aside>
        )}
      </div>

      {/* Full report viewer — overlays the entire viewport */}
      {viewingId && <FullReportViewer />}
    </div>
  )
}
