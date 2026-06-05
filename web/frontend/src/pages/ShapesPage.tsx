import { useState, useRef } from 'react'
import { MapContainer, TileLayer, FeatureGroup, useMapEvents } from 'react-leaflet'
import { EditControl } from 'react-leaflet-draw'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import { ArrowLeft, Plus, Trash2, Download, Globe } from 'lucide-react'
import { Link } from 'react-router-dom'

// Fix leaflet default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface Shape {
  id: string
  name: string
  type: 'polygon' | 'circle' | 'rectangle' | 'polyline'
  geojson: any
  color: string
}

function MapEvents({ onShapeCreated }: { onShapeCreated: (layer: any) => void }) {
  useMapEvents({
    draw: {
      created: (e) => {
        onShapeCreated(e.layer)
      },
    },
  })
  return null
}

export default function ShapesPage() {
  const [shapes, setShapes] = useState<Shape[]>([])
  const [newName, setNewName] = useState('')
  const [selectedShapeId, setSelectedShapeId] = useState<string | null>(null)
  const featureGroupRef = useRef<any>(null)

  const addShape = (layer: any) => {
    if (!newName.trim()) {
      alert('Please enter a shape name first')
      return
    }

    const type = layer instanceof L.Polygon && !(layer instanceof L.Rectangle)
      ? 'polygon'
      : layer instanceof L.Rectangle
      ? 'rectangle'
      : layer instanceof L.Polyline
      ? 'polyline'
      : 'circle'

    const geojson = layer.toGeoJSON()
    const shape: Shape = {
      id: crypto.randomUUID(),
      name: newName,
      type,
      geojson,
      color: ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][shapes.length % 5],
    }

    setShapes([...shapes, shape])
    setNewName('')
    setSelectedShapeId(shape.id)
  }

  const removeShape = (id: string) => {
    setShapes(shapes.filter(s => s.id !== id))
    if (selectedShapeId === id) setSelectedShapeId(null)
  }

  const exportGeoJSON = () => {
    const features = shapes.map(s => ({
      type: 'Feature' as const,
      geometry: s.geojson.geometry,
      properties: { name: s.name, type: s.type, color: s.color },
    }))
    const gj = { type: 'FeatureCollection' as const, features }
    const blob = new Blob([JSON.stringify(gj, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'shapes.geojson'
    a.click()
    URL.revokeObjectURL(url)
  }

  const fitToShape = (shape: Shape) => {
    if (!featureGroupRef.current) return
    const layer = featureGroupRef.current.getLayers().find((l: any) => {
      const gj = l.toGeoJSON()
      return gj.properties?.name === shape.name
    })
    if (layer) {
      const bounds = layer.getBounds()
      if (bounds.isValid()) {
        const map = featureGroupRef.current._map
        map.fitBounds(bounds, { padding: [20, 20] })
      }
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Custom Shapes</h1>
            <p className="text-sm text-gray-400">Draw analysis regions on the map for simulations.</p>
          </div>
          <button
            onClick={exportGeoJSON}
            disabled={shapes.length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm hover:bg-gray-700 disabled:opacity-50"
          >
            <Download className="w-4 h-4" /> Export GeoJSON
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Shape List */}
          <div className="space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Shape Name</h2>
              <div className="flex gap-2">
                <input
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  placeholder="e.g. North Atlantic Corridor"
                  className="flex-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white"
                  onKeyDown={e => e.key === 'Enter' && newName.trim() && alert('Draw on the map to create the shape')}
                />
                <button
                  onClick={() => newName.trim() && alert('Draw on the map to create the shape')}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                1. Enter name → 2. Use map tools to draw → 3. Shape appears in list
              </p>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Shapes ({shapes.length})</h2>
              {shapes.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Globe className="w-10 h-10 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No shapes yet. Draw on the map!</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {shapes.map(s => (
                    <div
                      key={s.id}
                      className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedShapeId === s.id
                          ? 'bg-indigo-900/30 border-indigo-500'
                          : 'bg-gray-800/50 border-gray-700/50 hover:border-gray-600'
                      }`}
                      onClick={() => {
                        setSelectedShapeId(s.id)
                        fitToShape(s)
                      }}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.color }} />
                        <div>
                          <span className="text-sm">{s.name}</span>
                          <span className="text-xs text-gray-500 ml-2 uppercase">{s.type}</span>
                        </div>
                      </div>
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          removeShape(s.id)
                        }}
                        className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-red-400"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Map */}
          <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <MapContainer
              center={[20, 0]}
              zoom={2}
              style={{ height: '500px', width: '100%' }}
              className="z-0"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <FeatureGroup ref={featureGroupRef}>
                <EditControl
                  position="topright"
                  draw={{
                    rectangle: true,
                    polygon: true,
                    circle: true,
                    polyline: true,
                    marker: false,
                    circlemarker: false,
                  }}
                  edit={{
                    featureGroup: featureGroupRef.current,
                  }}
                />
                <MapEvents onShapeCreated={addShape} />
              </FeatureGroup>
            </MapContainer>
            <div className="p-3 bg-gray-800/50 text-xs text-gray-400">
              <strong>Tools:</strong> Rectangle, Polygon, Circle, Polyline. Click a shape in the list to zoom to it.
            </div>
          </div>
        </div>

        <div className="bg-indigo-900/10 border border-indigo-800/30 rounded-xl p-4 mt-6">
          <p className="text-xs text-indigo-300">
            Shapes are exported as GeoJSON for use with the CLI: <code className="text-indigo-200">satsim_radio.py --shapes shapes.geojson</code>
          </p>
        </div>
      </div>
    </div>
  )
}
