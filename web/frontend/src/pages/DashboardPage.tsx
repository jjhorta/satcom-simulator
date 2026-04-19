import { useState } from 'react'
import { Link } from 'react-router-dom'
import { LogOut, Satellite, HelpCircle, Settings } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import ConfigPanel from '../components/ConfigPanel'
import JobList from '../components/JobList'
import JobDetail from '../components/JobDetail'

export default function DashboardPage() {
  const logout   = useAuthStore((s) => s.logout)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [expanded,      setExpanded]      = useState(false)

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

        {/* Job list — hidden when detail is expanded */}
        <main className={`flex-1 overflow-y-auto p-6 ${expanded ? 'hidden' : ''}`}>
          <JobList onSelectJob={setSelectedJobId} selectedJobId={selectedJobId} />
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
    </div>
  )
}
