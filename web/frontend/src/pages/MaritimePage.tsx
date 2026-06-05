import { useState } from 'react'
import { ArrowLeft, Ship, Radio, MapPin, Anchor } from 'lucide-react'
import { useNavigate, Link } from 'react-router-dom'

export default function MaritimePage() {
  const navigate = useNavigate()
  const [region, setRegion] = useState('north_atlantic')
  const [comms, setComms] = useState('vdes')
  const [bandwidthPerShip, setBandwidthPerShip] = useState(2.0)
  const [result, setResult] = useState<{ terminals: number; demand_mbps: number; ships_est: number } | null>(null)
  const [loading, setLoading] = useState(false)

  const REGIONS = [
    { id: 'north_atlantic', label: 'North Atlantic', lat: 40, lon: -50 },
    { id: 'mediterranean', label: 'Mediterranean', lat: 38, lon: 15 },
    { id: 'singapore_strait', label: 'Malacca Strait', lat: 2.5, lon: 102 },
    { id: 'panama_canal', label: 'Panama Canal', lat: 9, lon: -79.5 },
    { id: 'suez', label: 'Suez Canal', lat: 30, lon: 32.5 },
    { id: 'global', label: 'Global Maritime', lat: 0, lon: 0 },
  ]

  async function handleEvaluate() {
    setLoading(true)
    try {
      const regionInfo = REGIONS.find(r => r.id === region) ?? REGIONS[0]
      const res = await fetch('/constellation-simulator/api/sim/demand', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          lat: regionInfo.lat,
          lon: regionInfo.lon,
          profile: 'maritime',
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResult({
        terminals: data.terminals,
        demand_mbps: data.total_demand_mbps,
        ships_est: Math.round(data.terminals),
      })
    } catch (e: any) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        <h1 className="text-2xl font-bold mb-2">Maritime VDES Analysis</h1>
        <p className="text-sm text-gray-400 mb-8">
          AIS/VDES coverage and capacity analysis for maritime regions.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Region Config */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
              <Ship className="w-4 h-4 text-blue-400" /> Shipping Region
            </h2>
            <div className="grid grid-cols-2 gap-2 mb-4">
              {REGIONS.map(r => (
                <button
                  key={r.id}
                  onClick={() => setRegion(r.id)}
                  className={`p-3 rounded-lg border text-left text-sm transition-colors ${
                    region === r.id
                      ? 'border-blue-500 bg-blue-900/30 text-white'
                      : 'border-gray-800 bg-gray-800/50 text-gray-400 hover:border-gray-700'
                  }`}
                >
                  <div className="font-medium">{r.label}</div>
                  <div className="text-xs text-gray-500">{r.lat}°N, {Math.abs(r.lon)}°{' lon'}</div>
                </button>
              ))}
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500">Communication Payload</label>
                <select value={comms} onChange={e => setComms(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white">
                  <option value="vdes">VDES (50 kHz, Data)</option>
                  <option value="ais">AIS (25 kHz, Tracking)</option>
                  <option value="mss">MSS (100 kHz, SatPhone)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">Bandwidth per Ship (Mbps)</label>
                <input type="number" value={bandwidthPerShip}
                  onChange={e => setBandwidthPerShip(+e.target.value)} min={0.1} step={0.1}
                  className="w-full mt-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white" />
              </div>
              <button onClick={handleEvaluate} disabled={loading}
                className="w-full mt-3 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2">
                <Radio className="w-4 h-4" />
                {loading ? 'Evaluating...' : 'Evaluate Maritime Demand'}
              </button>
            </div>
          </div>

          {/* Right: Results */}
          <div className="space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Regional Demand</h2>
              {result ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-800 rounded-lg p-4 text-center">
                      <Ship className="w-5 h-5 mx-auto mb-2 text-blue-400" />
                      <div className="text-2xl font-bold text-white">{result.ships_est}</div>
                      <div className="text-xs text-gray-500">Estimated Vessels</div>
                    </div>
                    <div className="bg-gray-800 rounded-lg p-4 text-center">
                      <Radio className="w-5 h-5 mx-auto mb-2 text-emerald-400" />
                      <div className="text-2xl font-bold text-emerald-400">{result.demand_mbps.toFixed(1)}</div>
                      <div className="text-xs text-gray-500">VDES Demand (Mbps)</div>
                    </div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                      <Anchor className="w-3 h-3" /> VDES Channel Details
                    </div>
                    <div className="text-xs text-gray-500 space-y-1">
                      <div>VDES channel: 50 kHz per direction</div>
                      <div>VDES data rate: up to 307 kbps per channel</div>
                      <div>Capacity per vessel: {bandwidthPerShip} Mbps</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <MapPin className="w-10 h-10 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">Select a region and click evaluate</p>
                </div>
              )}
            </div>

            <div className="bg-blue-900/10 border border-blue-800/30 rounded-xl p-4">
              <div className="flex items-start gap-2">
                <Ship className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
                <p className="text-xs text-blue-300">
                  Maritime VDES is a core differentiator vs NCAT (which covers generic satcom).
                  Use the CLI for full AIS trajectory simulation: <code className="text-blue-200">satsim_radio.py throughput --comms vdes --grid h3</code>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
