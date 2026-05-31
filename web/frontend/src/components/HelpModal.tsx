import { X, MessageSquare, BarChart3, Globe, Radio, HelpCircle, BookOpen } from 'lucide-react'

const HELP_ITEMS = [
  {
    icon: Globe,
    title: 'Design a constellation for a region',
    examples: [
      'Design a VDES constellation for Panama Canal coverage',
      'What constellation would give good coverage around Mozambique?',
      'Design a constellation for the Portuguese EEZ',
    ],
  },
  {
    icon: Radio,
    title: 'Run simulations & check results',
    examples: [
      'Run a heatmap for 24 sats, 3 planes, 53°, 650km with VDES',
      'Run an RF heatmap for starlink ku with storm weather',
      'Run a latency simulation from Lisbon to Azores, 72 sats, 65°',
      'Check the status of job {job_id}',
      'Read the CSV data from my Mozambique simulation',
      'What does the RF link budget consider?',
    ],
  },
  {
    icon: Globe,
    title: 'Latency & ISL routing',
    examples: [
      'Compare fiber vs satellite latency between London and Singapore',
      'Run a latency simulation from Los Angeles to Tokyo',
      'What is the end-to-end latency for my constellation?',
      'How does ISL range affect latency?',
    ],
  },
  {
    icon: BarChart3,
    title: 'Parametric sweeps',
    examples: [
      'Sweep satellites from 12 to 48 and inclination from 53 to 87',
      'Compare coverage for 36 vs 72 vs 108 satellites',
      'Sweep weather conditions for starlink ku',
    ],
  },
  {
    icon: MessageSquare,
    title: 'Compare & iterate',
    examples: [
      'Now try 48 satellites instead',
      'What if I use 65° inclination instead?',
      'How does that compare to the Mozambique design?',
    ],
  },
  {
    icon: BookOpen,
    title: 'Understand the simulator',
    examples: [
      'Explain how the heatmap simulation works',
      'What parameters affect coverage?',
      'How is the RF link budget calculated?',
      'What does inclination do?',
    ],
  },
]

export default function HelpModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 rounded-2xl border border-gray-800 w-full max-w-2xl max-h-[85vh] flex flex-col"
           onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-semibold text-white">How to use CARL</h2>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          <p className="text-sm text-gray-400 leading-relaxed">
            CARL is your AI constellation engineer — inspired by Carl Sagan. 
            Tell him what you want to design in plain language, and he'll use the 
            Constellation Simulator to run real simulations, analyze results, and iterate on designs.
          </p>

          {HELP_ITEMS.map((section, i) => (
            <div key={i}>
              <div className="flex items-center gap-2 mb-2">
                <section.icon className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-medium text-white">{section.title}</h3>
              </div>
              <div className="space-y-1.5 ml-6">
                {section.examples.map((example, j) => (
                  <div key={j} className="text-xs text-gray-500 bg-gray-800/50 rounded-lg px-3 py-2 border border-gray-800/50">
                    <span className="text-indigo-400 mr-1">→</span>
                    "{example}"
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="bg-indigo-950/30 border border-indigo-800/40 rounded-lg p-4 mt-2">
            <p className="text-xs text-indigo-300 leading-relaxed">
              💡 <strong>Tip:</strong> CARL remembers your conversation. You can refine designs iteratively — 
              just say "Now try 48 satellites instead" and he'll adjust and re-run.
              All jobs appear in the <strong>Resources</strong> panel (sidebar) with live status.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
