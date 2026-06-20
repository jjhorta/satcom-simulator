import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Tooltip, Popup } from 'react-leaflet'
import { getGroundStations } from '../api/client'
import type { LatLngExpression } from 'leaflet'

interface GroundStation {
  id: string
  name: string
  latitude: number
  longitude: number
  freq_bands: string[]
  min_elevation: number
  enabled: boolean
  tags: string[]
}

const BAND_COLORS: Record<string, string> = {
  vdes: '#22c55e',
  ais:  '#3b82f6',
  ku:   '#f59e0b',
}

export default function GroundStationMap({ height = '400px' }: { height?: string }) {
  const { data: stations = [], isLoading } = useQuery({
    queryKey: ['groundStations'],
    queryFn: getGroundStations,
    staleTime: 60_000,
  })

  if (isLoading) return <div className="text-sm text-gray-500 animate-pulse">Loading gateways...</div>

  const center: LatLngExpression = [20, 0]

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {stations.map((s: GroundStation) => (
          <span key={s.id}
            className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
                       bg-gray-800 text-gray-300 border border-gray-700">
            <span className="w-2 h-2 rounded-full"
              style={{ backgroundColor: BAND_COLORS[s.freq_bands?.[0]] || '#6b7280' }} />
            {s.name}
          </span>
        ))}
      </div>
      <div className="rounded-lg border border-gray-800 overflow-hidden" style={{ height }}>
        <MapContainer center={center} zoom={2} className="h-full w-full"
          scrollWheelZoom={true}>
          <TileLayer
            attribution='&copy; <a href="https://openstreetmap.org">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {stations.map((s: GroundStation) => (
            <CircleMarker
              key={s.id}
              center={[s.latitude, s.longitude]}
              radius={8}
              pathOptions={{
                color: BAND_COLORS[s.freq_bands?.[0]] || '#6b7280',
                fillColor: BAND_COLORS[s.freq_bands?.[0]] || '#6b7280',
                fillOpacity: 0.6,
                weight: 2,
              }}
            >
              <Tooltip direction="top" offset={[0, -10]}>
                <strong>{s.name}</strong>
                <br />
                <span className="text-xs">
                  {s.latitude.toFixed(2)}°, {s.longitude.toFixed(2)}°
                </span>
              </Tooltip>
              <Popup>
                <div className="text-xs space-y-1">
                  <div className="font-semibold">{s.name}</div>
                  <div>📍 {s.latitude.toFixed(2)}°, {s.longitude.toFixed(2)}°</div>
                  <div>📡 Bands: {s.freq_bands.join(', ')}</div>
                  <div>📐 Min elev: {s.min_elevation}°</div>
                  <div>🏷️ {s.tags.join(' · ')}</div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
