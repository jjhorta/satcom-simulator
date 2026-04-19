import 'leaflet/dist/leaflet.css'
import { useQuery } from '@tanstack/react-query'
import { fetchCsv, fileUrl } from '../../api/client'
import {
  MapContainer, TileLayer, Polyline, CircleMarker, Tooltip, useMap,
} from 'react-leaflet'
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet'

// ── Types ─────────────────────────────────────────────────────────────────────

interface RouteRow {
  sequence:         number
  waypoint:         string
  latitude:         number
  longitude:        number
  connectivity_pct: number
  wkt_geom:         string
}

// ── Colour scale (0% red → 50% yellow → 100% green) — shared with HeatmapViewer
function pctToColour(pct: number): string {
  const t = Math.max(0, Math.min(100, pct)) / 100
  if (t < 0.5) {
    const g = Math.round(t * 2 * 200)
    return `rgb(220,${g},0)`
  }
  const r = Math.round((1 - (t - 0.5) * 2) * 200)
  return `rgb(${r},200,0)`
}

// ── Auto-fit to route extents ─────────────────────────────────────────────────
function FitRoute({ rows }: { rows: RouteRow[] }) {
  const map = useMap()
  if (rows.length) {
    const lats = rows.map((r) => r.latitude)
    const lons = rows.map((r) => r.longitude)
    const bounds: LatLngBoundsExpression = [
      [Math.min(...lats) - 2, Math.min(...lons) - 2],
      [Math.max(...lats) + 2, Math.max(...lons) + 2],
    ]
    map.fitBounds(bounds)
  }
  return null
}

// ── Main component ────────────────────────────────────────────────────────────

export default function RouteViewer({
  jobId, filename,
}: { jobId: string; filename: string }) {
  const { data = [], isLoading, isError } = useQuery<RouteRow[]>({
    queryKey: ['csv', jobId, filename],
    queryFn:  () => (fetchCsv(jobId, filename) as unknown) as Promise<RouteRow[]>,
  })

  const downloadUrl = fileUrl(jobId, filename)

  if (isLoading) return <p className="text-sm text-gray-500 animate-pulse">Loading route…</p>
  if (isError)   return <p className="text-sm text-red-400">Failed to load route data.</p>
  if (!data.length) return <p className="text-sm text-gray-500">No waypoints.</p>

  // Sort by sequence to ensure correct polyline order
  const sorted = [...data].sort((a, b) => a.sequence - b.sequence)
  const line: LatLngExpression[] = sorted.map((r) => [r.latitude, r.longitude])

  const avg = sorted.reduce((s, r) => s + r.connectivity_pct, 0) / sorted.length
  const min = Math.min(...sorted.map((r) => r.connectivity_pct))
  const max = Math.max(...sorted.map((r) => r.connectivity_pct))

  return (
    <div className="space-y-3">
      {/* Map */}
      <div className="rounded-lg overflow-hidden border border-gray-800" style={{ height: 420 }}>
        <MapContainer
          center={[sorted[0].latitude, sorted[0].longitude]}
          zoom={3}
          scrollWheelZoom
          className="w-full h-full"
          style={{ background: '#111827' }}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            maxZoom={14}
          />

          <FitRoute rows={sorted} />

          {/* Route polyline — neutral grey */}
          <Polyline
            positions={line}
            pathOptions={{ color: '#6b7280', weight: 2, dashArray: '6 4', opacity: 0.7 }}
          />

          {/* Waypoint markers coloured by connectivity */}
          {sorted.map((row) => (
            <CircleMarker
              key={row.sequence}
              center={[row.latitude, row.longitude]}
              radius={7}
              pathOptions={{
                fillColor:   pctToColour(row.connectivity_pct),
                fillOpacity: 0.9,
                color:       '#fff',
                weight:      1.5,
              }}
            >
              <Tooltip>
                <span className="font-mono text-xs">
                  <strong>{row.waypoint}</strong>
                  <br />
                  {row.latitude.toFixed(2)}°, {row.longitude.toFixed(2)}°
                  <br />
                  Connectivity: <strong>{row.connectivity_pct.toFixed(1)}%</strong>
                </span>
              </Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      {/* Stats + colour legend row */}
      <div className="flex items-center gap-4 px-1">
        <div className="flex gap-4 text-xs text-gray-400">
          <span>Avg: <strong className="text-white">{avg.toFixed(1)}%</strong></span>
          <span>Min: <strong style={{ color: pctToColour(min) }}>{min.toFixed(1)}%</strong></span>
          <span>Max: <strong style={{ color: pctToColour(max) }}>{max.toFixed(1)}%</strong></span>
          <span className="text-gray-600">{sorted.length} waypoints</span>
        </div>
        <div className="flex-1 mx-2 h-2.5 rounded"
          style={{ background: 'linear-gradient(to right, rgb(220,0,0), rgb(200,200,0), rgb(0,200,0))' }}
        />
        <span className="text-xs text-gray-500">0 → 100%</span>
      </div>

      {/* Waypoint table */}
      <div className="rounded-lg border border-gray-800 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-800/60 text-gray-500 uppercase tracking-wider">
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">Waypoint</th>
              <th className="px-3 py-2 text-right">Lat</th>
              <th className="px-3 py-2 text-right">Lon</th>
              <th className="px-3 py-2 text-right">Connectivity</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr key={row.sequence} className="border-t border-gray-800 hover:bg-gray-800/30">
                <td className="px-3 py-1.5 text-gray-600 font-mono">{row.sequence}</td>
                <td className="px-3 py-1.5 text-gray-300 font-mono">{row.waypoint}</td>
                <td className="px-3 py-1.5 text-gray-400 text-right tabular-nums">{row.latitude.toFixed(2)}°</td>
                <td className="px-3 py-1.5 text-gray-400 text-right tabular-nums">{row.longitude.toFixed(2)}°</td>
                <td className="px-3 py-1.5 text-right tabular-nums font-medium"
                  style={{ color: pctToColour(row.connectivity_pct) }}
                >
                  {row.connectivity_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Download link */}
      <div className="text-right">
        <a
          href={downloadUrl}
          download
          className="text-xs text-indigo-400 hover:text-indigo-300 underline transition-colors"
        >
          Download CSV
        </a>
      </div>
    </div>
  )
}
