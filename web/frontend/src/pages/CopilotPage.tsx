import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import CopilotChat from '../components/CopilotChat'

export default function CopilotPage() {
  const navigate = useNavigate()

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Top bar */}
      <header className="flex items-center gap-3 px-4 py-2 bg-gray-900 border-b border-gray-800 flex-shrink-0">
        <button onClick={() => navigate('/')}
          className="text-gray-400 hover:text-white transition-colors flex items-center gap-1.5 text-sm">
          <ArrowLeft className="w-4 h-4" /> Dashboard
        </button>
        <div className="flex items-center gap-2 ml-2">
          <span className="text-sm font-semibold text-white">CARL</span>
          <span className="text-xs text-gray-500">Constellation AI Reasoning Layer</span>
        </div>
      </header>
      <div className="flex-1 overflow-hidden relative">
        <CopilotChat />
      </div>
    </div>
  )
}
