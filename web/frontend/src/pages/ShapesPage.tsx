import { useState } from 'react'
import { ArrowLeft, Plus, Trash2, Download, Globe } from 'lucide-react'
import { Link } from 'react-router-dom'

interface Shape {
  id: string
  name: string
  type: 'polygon' | 'circle' | 'corridor'
  color: string
}

export default function ShapesPage() {
  
  const [shapes, setShapes] = useState<Shape[]>([])
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState<'polygon' | 'circle' | 'corridor'>('polygon')

  const addShape = () => {
    if (!newName.trim()) return
    const shape: Shape = {
      id: crypto.randomUUID(),
      name: newName,
      type: newType,
      color: ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][shapes.length % 5],
    }
    setShapes([...shapes, shape])
    setNewName('')
  }

  const removeShape = (id: string) => {
    setShapes(shapes.filter(s => s.id !== id))
  }

  const exportGeoJSON = () => {
    const features = shapes.map(s => ({
      type: 'Feature' as const,
      geometry: {
        type: s.type === 'corridor' ? 'LineString' as const : 'Polygon' as const,
        coordinates: [[]],
      },
      properties: { name: s.name, type: s.type, color: s.color },
    }))
    const gj = { type: 'FeatureCollection' as const, features }
    const blob = new Blob([JSON.stringify(gj, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'shapes.geojson'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Custom Shapes</h1>
            <p className="text-sm text-gray-400">Define analysis regions for simulations.</p>
          </div>
          <button onClick={exportGeoJSON} disabled={shapes.length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm hover:bg-gray-700 disabled:opacity-50">
            <Download className="w-4 h-4" /> Export GeoJSON
          </button>
        </div>

        {/* Shape Creator */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-xs text-gray-500 mb-1 block">Shape Name</label>
              <input value={newName} onChange={e => setNewName(e.target.value)}
                placeholder="e.g. North Atlantic Corridor"
                className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white"
                onKeyDown={e => e.key === 'Enter' && addShape()} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Type</label>
              <select value={newType} onChange={e => setNewType(e.target.value as any)}
                className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white">
                <option value="polygon">Polygon</option>
                <option value="circle">Circle</option>
                <option value="corridor">Corridor</option>
              </select>
            </div>
            <button onClick={addShape}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm">
              <Plus className="w-4 h-4" /> Add
            </button>
          </div>
        </div>

        {/* Shape List */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          {shapes.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Globe className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No shapes defined yet.</p>
              <p className="text-xs text-gray-600 mt-1">Add a polygon, circle, or corridor above.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {shapes.map(s => (
                <div key={s.id} className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 border border-gray-700/50">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.color }} />
                    <div>
                      <span className="text-sm">{s.name}</span>
                      <span className="text-xs text-gray-500 ml-2 uppercase">{s.type}</span>
                    </div>
                  </div>
                  <button onClick={() => removeShape(s.id)}
                    className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-red-400">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-indigo-900/10 border border-indigo-800/30 rounded-xl p-4 mt-4">
          <p className="text-xs text-indigo-300">
            Note: Interactive map drawing is available in the full Leaflet integration.
            Shape data exports as GeoJSON for use with <code className="text-indigo-200">satsim_radio.py --shapes shapes.geojson</code>.
          </p>
        </div>
      </div>
    </div>
  )
}
