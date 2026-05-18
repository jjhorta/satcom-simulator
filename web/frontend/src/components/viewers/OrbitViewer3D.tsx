/**
 * OrbitViewer3D — interactive Three.js / satellite.js orbit visualiser
 *
 * Features:
 *  • Textured Earth sphere (fallback solid colour)
 *  • Animated satellite dots propagated via satellite.js (SGP4)
 *  • Orbit trail lines per satellite (past N minutes)
 *  • Coverage footprint circles (if constellation data present)
 *  • Time scrubber, play/pause, speed selector
 *  • Rotate / zoom via OrbitControls
 */

import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'
import * as THREE from 'three'
import * as satellite from 'satellite.js'
import { useQuery } from '@tanstack/react-query'
import { fetchTles } from '../../api/client'
import { Play, Pause, RotateCcw, Zap } from 'lucide-react'

// ── Constants ─────────────────────────────────────────────────────────────────
const RE = 6378.137        // km
const SCALE = 1 / RE       // 1 unit = 1 Re in scene
const TRAIL_MINUTES = 20   // how many minutes of trail to show
const TRAIL_STEPS = 80     // points in trail

// ── Helpers ───────────────────────────────────────────────────────────────────
function latLonAltToVec3(lat_rad: number, lon_rad: number, alt_km: number) {
  const r = (RE + alt_km) * SCALE
  return new THREE.Vector3(
    r * Math.cos(lat_rad) * Math.cos(lon_rad),
    r * Math.sin(lat_rad),
    -r * Math.cos(lat_rad) * Math.sin(lon_rad),  // Z flipped for Three.js convention
  )
}

function propagate(satrec: satellite.SatRec, date: Date) {
  const posVel = satellite.propagate(satrec, date)
  if (!posVel || typeof posVel.position === 'boolean' || !posVel.position) return null
  const gmst = satellite.gstime(date)
  const geo = satellite.eciToGeodetic(posVel.position as satellite.EciVec3<number>, gmst)
  return latLonAltToVec3(geo.latitude, geo.longitude, geo.height)
}

// ── Earth ────────────────────────────────────────────────────────────────────
function Earth() {
  const meshRef = useRef<THREE.Mesh>(null!)
  const texture = useMemo(() => {
    const loader = new THREE.TextureLoader()
    // Use NASA Blue Marble texture via public CDN; fallback handled by error event
    return loader.load(
      'https://cdn.jsdelivr.net/gh/mrdoob/three.js@r128/examples/textures/planets/earth_atmos_2048.jpg',
    )
  }, [])

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1, 64, 64]} />
      <meshStandardMaterial map={texture} metalness={0.1} roughness={0.8} />
    </mesh>
  )
}

// ── Satellite dot ─────────────────────────────────────────────────────────────
function SatDot({ position, color }: { position: THREE.Vector3; color: string }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.008, 6, 6]} />
      <meshBasicMaterial color={color} />
    </mesh>
  )
}

// ── Orbit trail ───────────────────────────────────────────────────────────────
function OrbitTrail({ points, color }: { points: THREE.Vector3[]; color: string }) {
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry()
    if (points.length >= 2) g.setFromPoints(points)
    return g
  }, [points])

  return (
    <primitive object={new THREE.Line(geo, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.35 }))} />
  )
}

// ── Coverage fill (spherical cap) ────────────────────────────────────────────
function CoverageFill({ center, radiusKm }: { center: THREE.Vector3; radiusKm: number }) {
  const geo = useMemo(() => {
    const angRadius = radiusKm / RE
    const axis = center.clone().normalize()
    const perp = new THREE.Vector3(1, 0, 0)
    if (Math.abs(axis.dot(perp)) > 0.9) perp.set(0, 1, 0)
    const u = new THREE.Vector3().crossVectors(axis, perp).normalize()
    const v = new THREE.Vector3().crossVectors(axis, u).normalize()
    const N = 64
    const vertices: number[] = []
    const indices: number[] = []
    // Centre vertex (index 0)
    const centre = axis.clone().multiplyScalar(1.001)
    vertices.push(centre.x, centre.y, centre.z)
    // Ring vertices
    for (let i = 0; i <= N; i++) {
      const angle = (i / N) * 2 * Math.PI
      const pt = axis.clone()
        .multiplyScalar(Math.cos(angRadius))
        .addScaledVector(u, Math.sin(angRadius) * Math.cos(angle))
        .addScaledVector(v, Math.sin(angRadius) * Math.sin(angle))
        .normalize()
        .multiplyScalar(1.001)
      vertices.push(pt.x, pt.y, pt.z)
    }
    // Fan triangles: centre (0) → ring[i] → ring[i+1]
    for (let i = 1; i <= N; i++) {
      indices.push(0, i, i + 1)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
    g.setIndex(indices)
    return g
  }, [center, radiusKm])

  return (
    <mesh geometry={geo} renderOrder={1}>
      <meshBasicMaterial
        color="#facc15"
        transparent
        opacity={0.28}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}

// ── Coverage circle ────────────────────────────────────────────────────────────
function CoverageCircle({ center, radiusKm }: { center: THREE.Vector3; radiusKm: number }) {
  const points = useMemo(() => {
    const pts: THREE.Vector3[] = []
    const angRadius = radiusKm / RE  // radians
    const axis = center.clone().normalize()
    // Build a reference frame perpendicular to axis
    const perp = new THREE.Vector3(1, 0, 0)
    if (Math.abs(axis.dot(perp)) > 0.9) perp.set(0, 1, 0)
    const u = new THREE.Vector3().crossVectors(axis, perp).normalize()
    const v = new THREE.Vector3().crossVectors(axis, u).normalize()
    const N = 64
    for (let i = 0; i <= N; i++) {
      const angle = (i / N) * 2 * Math.PI
      const pt = axis.clone()
        .multiplyScalar(Math.cos(angRadius))
        .addScaledVector(u, Math.sin(angRadius) * Math.cos(angle))
        .addScaledVector(v, Math.sin(angRadius) * Math.sin(angle))
        .normalize()
        .multiplyScalar(1.001)   // just above surface
      pts.push(pt)
    }
    return pts
  }, [center, radiusKm])

  const geo = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points])
  return (
    <primitive object={new THREE.Line(geo, new THREE.LineBasicMaterial({ color: '#60a5fa', transparent: true, opacity: 0.2 }))} />
  )
}

// ── Animated scene ─────────────────────────────────────────────────────────────
interface TleEntry { name: string; line1: string; line2: string }

const PLANE_COLORS = [
  '#f87171', '#fb923c', '#facc15', '#4ade80',
  '#22d3ee', '#818cf8', '#e879f9', '#f472b6',
  '#a3e635', '#34d399', '#38bdf8', '#c084fc',
]

function Scene({
  tles,
  coverageRadiusKm,
  simTime,
  showTrails,
  showCoverage,
  showFill,
}: {
  tles: TleEntry[]
  coverageRadiusKm: number
  simTime: Date
  showTrails: boolean
  showCoverage: boolean
  showFill: boolean
}) {
  const satrecs = useMemo(
    () => tles.map((t) => satellite.twoline2satrec(t.line1, t.line2)),
    [tles],
  )

  // Compute per-satellite current position
  const positions = useMemo(
    () => satrecs.map((sr) => propagate(sr, simTime)),
    [satrecs, simTime],
  )

  // Compute trails (last TRAIL_MINUTES)
  const trails = useMemo(() => {
    if (!showTrails) return []
    return satrecs.map((sr) => {
      const pts: THREE.Vector3[] = []
      for (let i = TRAIL_STEPS; i >= 0; i--) {
        const t = new Date(simTime.getTime() - i * (TRAIL_MINUTES / TRAIL_STEPS) * 60000)
        const p = propagate(sr, t)
        if (p) pts.push(p)
      }
      return pts
    })
  }, [satrecs, simTime, showTrails])

  // Assign plane index from SAT-NNN numbering
  const planeOf = (idx: number) => {
    const satsPerPlane = Math.ceil(tles.length / Math.max(1, PLANE_COLORS.length))
    return Math.floor(idx / satsPerPlane) % PLANE_COLORS.length
  }

  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={1.2} />
      <Stars radius={200} depth={50} count={3000} factor={3} fade />

      <Earth />

      {positions.map((pos, i) => {
        if (!pos) return null
        const color = PLANE_COLORS[planeOf(i)]
        return (
          <group key={i}>
            <SatDot position={pos} color={color} />
            {showTrails && trails[i]?.length >= 2 && (
              <OrbitTrail points={trails[i]} color={color} />
            )}
            {showCoverage && (
              <CoverageCircle center={pos} radiusKm={coverageRadiusKm} />
            )}
            {showFill && (
              <CoverageFill center={pos} radiusKm={coverageRadiusKm} />
            )}
          </group>
        )
      })}
    </>
  )
}

// ── Time controller ─────────────────────────────────────────────────────────
function useSimClock(epochISO: string) {
  const epochMs = useMemo(() => new Date(epochISO).getTime(), [epochISO])
  const [offsetMin, setOffsetMin] = useState(0)
  const [playing, setPlaying]   = useState(true)
  const [speed, setSpeed]       = useState(60)   // 1 real second = N sim seconds
  const lastRealRef = useRef<number | null>(null)

  useEffect(() => {
    if (!playing) { lastRealRef.current = null; return }
    let rafId: number
    const tick = (now: number) => {
      if (lastRealRef.current !== null) {
        const dtReal = (now - lastRealRef.current) / 1000
        setOffsetMin((m) => m + (dtReal * speed) / 60)
      }
      lastRealRef.current = now
      rafId = requestAnimationFrame(tick)
    }
    rafId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafId)
  }, [playing, speed])

  const simTime = useMemo(
    () => new Date(epochMs + offsetMin * 60000),
    [epochMs, offsetMin],
  )

  return { simTime, offsetMin, setOffsetMin, playing, setPlaying, speed, setSpeed }
}

// ── Coverage radius util ─────────────────────────────────────────────────────
function coverageRadius(altKm: number, minElevDeg = 10) {
  const elRad = (minElevDeg * Math.PI) / 180
  const r = RE + altKm
  const sinRho = (RE / r) * Math.cos(elRad)
  const rho = Math.asin(Math.min(1, sinRho))
  const lambda = Math.PI / 2 - elRad - rho
  return RE * lambda
}

// ── Main component ────────────────────────────────────────────────────────────
export default function OrbitViewer3D({ jobId }: { jobId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['tles', jobId],
    queryFn:  () => fetchTles(jobId),
  })

  const [showTrails,   setShowTrails]   = useState(true)
  const [showCoverage, setShowCoverage] = useState(false)
  const [showFill,     setShowFill]     = useState(false)

  const epoch = data?.epoch ?? '2024-01-01T12:00:00Z'
  const { simTime, offsetMin, setOffsetMin, playing, setPlaying, speed, setSpeed } =
    useSimClock(epoch)

  const tles: TleEntry[] = data?.tles ?? []
  const altKm: number    = data?.altitude_km ?? 600
  const covRadius        = coverageRadius(altKm)

  // Total simulation window for the scrubber: 1 orbital period * 2
  const periodMin = useMemo(() => {
    const mu = 398600.4418
    const a  = RE + altKm
    return (2 * Math.PI * Math.sqrt(a ** 3 / mu)) / 60
  }, [altKm])
  const windowMin = periodMin * 2

  if (isLoading) return (
    <div className="flex items-center justify-center h-64 text-sm text-gray-500 animate-pulse">
      Loading 3D orbit data…
    </div>
  )
  if (isError || !data) return (
    <div className="flex items-center justify-center h-64 text-sm text-gray-400">
      No 3D data available — re-run this orbit simulation to generate it.
    </div>
  )

  const simDateStr = simTime.toUTCString().replace(' GMT', ' UTC')

  return (
    <div className="rounded-xl overflow-hidden border border-gray-700 bg-gray-950 select-none">
      {/* 3D canvas */}
      <div style={{ height: 480 }}>
        <Canvas camera={{ position: [0, 0, 3.2], fov: 45 }} gl={{ antialias: true }}>
          <Suspense fallback={null}>
            <Scene
              tles={tles}
              coverageRadiusKm={covRadius}
              simTime={simTime}
              showTrails={showTrails}
              showCoverage={showCoverage}
              showFill={showFill}
            />
          </Suspense>
          <OrbitControls enablePan={false} minDistance={1.4} maxDistance={8} />
        </Canvas>
      </div>

      {/* Controls bar */}
      <div className="bg-gray-900 border-t border-gray-800 px-4 py-3 space-y-2">
        {/* Time display + play/pause */}
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-mono text-gray-400">{simDateStr}</span>
          <div className="flex items-center gap-2">
            {/* Speed selector */}
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Zap className="w-3.5 h-3.5" />
              {[10, 60, 300, 600].map((s) => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  className={`px-1.5 py-0.5 rounded text-xs transition-colors ${
                    speed === s
                      ? 'bg-indigo-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {s < 60 ? `${s}s` : `${s / 60}m`}/s
                </button>
              ))}
            </div>
            {/* Reset */}
            <button
              onClick={() => setOffsetMin(0)}
              className="p-1 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            {/* Play/Pause */}
            <button
              onClick={() => setPlaying((p) => !p)}
              className="p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
            >
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Time scrubber */}
        <input
          type="range"
          min={0}
          max={windowMin}
          step={0.1}
          value={Math.min(offsetMin, windowMin)}
          onChange={(e) => { setOffsetMin(parseFloat(e.target.value)); setPlaying(false) }}
          className="w-full accent-indigo-500 h-1.5 rounded cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-600">
          <span>Epoch</span>
          <span>+{(windowMin / 60).toFixed(1)} h</span>
        </div>

        {/* Toggles */}
        <div className="flex items-center gap-4 pt-1">
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showTrails}
              onChange={(e) => setShowTrails(e.target.checked)}
              className="accent-indigo-500 w-3.5 h-3.5"
            />
            Orbit trails
          </label>
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showCoverage}
              onChange={(e) => setShowCoverage(e.target.checked)}
              className="accent-indigo-500 w-3.5 h-3.5"
            />
            Coverage footprints
          </label>
          <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showFill}
              onChange={(e) => setShowFill(e.target.checked)}
              className="accent-yellow-500 w-3.5 h-3.5"
            />
            <span className="flex items-center gap-1">
              Fill
              <span className="inline-block w-3 h-3 rounded-sm" style={{ background: 'rgba(250,204,21,0.45)' }} />
            </span>
          </label>
          <span className="ml-auto text-xs text-gray-600">
            {tles.length} satellites · {altKm} km
          </span>
        </div>
      </div>
    </div>
  )
}
