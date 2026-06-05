import { useState } from 'react'
import { ArrowLeft, MapPin, Ship, Radio } from 'lucide-react'
import { useNavigate, Link } from 'react-router-dom'

const DEMAND_PROFILES = [
  { id: 'rural',      label: 'Rural Broadband',     desc: '5 Mbps per 100 km²',      icon: '🏘️', terminals: 0.05, bw: 5 },
  { id: 'urban',      label: 'Urban Broadband',     desc: '50 Mbps per km²',          icon: '🏙️', terminals: 10,   bw: 50 },
  { id: 'maritime',   label: 'Maritime AIS/VDES',   desc: '1 terminal per 10 km²',    icon: '🚢', terminals: 0.1,  bw: 2 },
  { id: 'aviation',   label: 'Aviation IFC',        desc: '200 Mbps per aircraft',     icon: '✈️', terminals: 0.001, bw: 200 },
  { id: 'mixed',      label: 'Mixed Profile',       desc: 'Weighted average',          icon: '🌐', terminals: 1.0,  bw: 10 },
]

export default function DemandPage() {
  const navigate = useNavigate()
  const [selectedProfile, setSelectedProfile] = useState('maritime')
  const [customTerminals, setCustomTerminals] = useState('')
  const [customBW, setCustomBW] = useState('')
  const [gridRes, setGridRes] = useState(5)
  const [totalCapacity, setTotalCapacity] = useState(1000)
  const [fairness, setFairness] = useState('proportional')
  const [result, setResult] = useState<{ supplied: number; unmet: number; satisfaction: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleEvaluate() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/constellation-simulator/api/sim/supply-demand', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify({
          profile: selectedProfile,
          grid_res: gridRes,
          fairness,
          total_capacity_mbps: totalCapacity,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResult({
        supplied: data.total_supplied_mbps,
        unmet: data.total_unmet_mbps,
        satisfaction: data.satisfaction_pct,
      })
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const profile = DEMAND_PROFILES.find(p => p.id === selectedProfile)!

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        <h1 className="text-2xl font-bold mb-2">Demand Model Configuration</h1>
        <p className="text-sm text-gray-400 mb-8">
          Configure bandwidth demand profiles and match supply to demand.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Profile Selection */}
          <div className="space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Demand Profile</h2>
              <div className="grid grid-cols-1 gap-2">
                {DEMAND_PROFILES.map(p => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedProfile(p.id)}
                    className={`flex items-center gap-3 p-3 rounded-lg border text-left transition-colors ${
                      selectedProfile === p.id
                        ? 'border-indigo-500 bg-indigo-900/30 text-white'
                        : 'border-gray-800 bg-gray-800/50 text-gray-400 hover:border-gray-700'
                    }`}
                  >
                    <span className="text-xl">{p.icon}</span>
                    <div>
                      <div className="text-sm font-medium">{p.label}</div>
                      <div className="text-xs text-gray-500">{p.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Custom Override</h2>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500">Terminals/km²</label>
                  <input
                    type="number"
                    value={customTerminals}
                    onChange={e => setCustomTerminals(e.target.value)}
                    placeholder={String(profile.terminals)}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Mbps per terminal</label>
                  <input
                    type="number"
                    value={customBW}
                    onChange={e => setCustomBW(e.target.value)}
                    placeholder={String(profile.bw)}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right: Simulation Config + Results */}
          <div className="space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Supply Configuration</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500">Total Capacity (Mbps)</label>
                  <input
                    type="number"
                    value={totalCapacity}
                    onChange={e => setTotalCapacity(+e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Grid Resolution (°)</label>
                  <input
                    type="number"
                    value={gridRes}
                    onChange={e => setGridRes(+e.target.value)}
                    min={0.5} max={10} step={0.5}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Fairness Criterion</label>
                  <select
                    value={fairness}
                    onChange={e => setFairness(e.target.value)}
                    className="w-full mt-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white"
                  >
                    <option value="proportional">Proportional</option>
                    <option value="max-min">Max-Min</option>
                    <option value="priority-weighted">Priority-Weighted</option>
                  </select>
                </div>
                <button
                  onClick={handleEvaluate}
                  disabled={loading}
                  className="w-full mt-3 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium transition-colors"
                >
                  {loading ? 'Computing...' : 'Evaluate Supply-Demand'}
                </button>
                {error && <p className="text-xs text-red-400">{error}</p>}
              </div>
            </div>

            {result && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-gray-300 mb-4">Results</h2>
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-gray-800 rounded-lg p-3 text-center">
                    <div className="text-lg font-bold text-emerald-400">
                      {result.supplied.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Supplied Mbps</div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3 text-center">
                    <div className="text-lg font-bold text-amber-400">
                      {result.unmet.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Unmet Mbps</div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-3 text-center">
                    <div className="text-lg font-bold text-indigo-400">
                      {result.satisfaction}%
                    </div>
                    <div className="text-xs text-gray-500">Satisfaction</div>
                  </div>
                </div>
              </div>
            )}

            <div className="bg-indigo-900/10 border border-indigo-800/30 rounded-xl p-4">
              <p className="text-xs text-indigo-300">
                Tip: Use a coarser grid resolution for global estimates,
                finer for regional analysis. Maritime profile is pre-tuned for VDES/AIS shipping lane modeling.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
