import 'leaflet/dist/leaflet.css'
import { useQuery } from '@tanstack/react-query'
import { fetchCsv, fileUrl } from '../../api/client'
import type { HeatmapRow } from '../../types'
import { MapContainer, TileLayer, Rectangle, Tooltip, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression } from 'leaflet'

// ── Colour scale: 0 % → red, 50 % → yellow, 100 % → green ───────────────────

function pctToColour(pct: number): string {
  const t = Math.max(0, Math.min(100, pct)) / 100
  if (t < 0.5) {
    // red → yellow
    const r = 220
    const g = Math.round(t * 2 * 200)
    return `rgb(${r},${g},0)`
  }
  // yellow → green
  const r = Math.round((1 - (t - 0.5) * 2) * 200)
  const g = 200
  return `rgb(${r},${g},0)`
}

// ── Auto-fit bounds after data loads ──────────────────────────────────────────
function FitBounds({ rows, cellDeg }: { rows: HeatmapRow[]; cellDeg: number }) {
  const map = useMap()
  if (rows.length) {
    const lats = rows.map((r) => r.latitude)
    const lons = rows.map((r) => r.longitude)
    const half = cellDeg / 2
    map.fitBounds([
      [Math.min(...lats) - half, Math.min(...lons) - half],
      [Math.max(...lats) + half, Math.max(...lons) + half],
    ])
  }
  return null
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function HeatmapViewer({ jobId, filename }: { jobId: string; filename: string }) {
  const downloadUrl = fileUrl(jobId, filename)
  const { data = [], isLoading, isError } = useQuery({
    queryKey: ['csv', jobId, filename],
    queryFn:  () => fetchCsv(jobId, filename),
  })

  if (isLoading) return <p className="text-sm text-gray-500 animate-pulse">Loading map…</p>
  if (isError)   return <p className="text-sm text-red-400">Failed to load CSV data.</p>
  if (!data.length) return <p className="text-sm text-gray-500">No data.</p>

  // Infer grid resolution from data delta (fallback 5°)
  const sortedLats = Array.from(new Set(data.map((r) => r.latitude))).sort((a, b) => a - b)
  const cellDeg = sortedLats.length > 1 ? Math.abs(sortedLats[1] - sortedLats[0]) : 5
  const half = cellDeg / 2

  return (
    <div className="rounded-lg overflow-hidden border border-gray-800" style={{ height: 440 }}>
      <MapContainer
        center={[20, 0]}
        zoom={2}
        scrollWheelZoom
        className="w-full h-full"
        style={{ background: '#111827' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          maxZoom={10}
        />

        <FitBounds rows={data} cellDeg={cellDeg} />

        {data.map((row, i) => {
          const bounds: LatLngBoundsExpression = [
            [row.latitude  - half, row.longitude - half],
            [row.latitude  + half, row.longitude + half],
          ]
          const colour = pctToColour(row.availability_pct)
          return (
            <Rectangle
              key={i}
              bounds={bounds}
              pathOptions={{
                color:       'transparent',
                fillColor:   colour,
                fillOpacity: 0.65,
                weight:      0,
              }}
            >
              <Tooltip sticky>
                <span className="font-mono text-xs">
                  {row.latitude.toFixed(1)}°, {row.longitude.toFixed(1)}°
                  <br />
                  Coverage: <strong>{row.availability_pct.toFixed(1)}%</strong>
                </span>
              </Tooltip>
            </Rectangle>
          )
        })}
      </MapContainer>

      {/* Colour legend + download */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-t border-gray-800 text-xs text-gray-400">
        <span>0 %</span>
        <div
          className="flex-1 mx-3 h-3 rounded"
          style={{ background: 'linear-gradient(to right, rgb(220,0,0), rgb(200,200,0), rgb(0,200,0))' }}
        />
        <span>100 %</span>
      </div>
      <div className="flex justify-end px-3 py-2 bg-gray-900 border-t border-gray-800">
        <a
          href={downloadUrl}
          download
          className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          ↓ Download CSV
        </a>
      </div>
    </div>
  )
}
