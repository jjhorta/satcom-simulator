import { Link } from 'react-router-dom'
import { BookOpen, Satellite, Radio, Globe, BarChart2, Map, Navigation, HelpCircle, ArrowLeft, Signal } from 'lucide-react'

// ── Reusable section card ─────────────────────────────────────────────────────
function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
      <div className="flex items-center gap-2 text-indigo-400">
        <Icon className="w-5 h-5 flex-shrink-0" />
        <h2 className="text-sm font-semibold text-white">{title}</h2>
      </div>
      <div className="text-sm text-gray-400 leading-relaxed space-y-2">{children}</div>
    </div>
  )
}

function Param({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <span className="font-mono text-xs text-indigo-300 bg-indigo-950/50 px-1.5 py-0.5 rounded flex-shrink-0 self-start mt-0.5">
        {name}
      </span>
      <span>{children}</span>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function HelpPage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Satellite className="w-5 h-5 text-indigo-400" />
          <span className="font-semibold text-white">Constellation Simulator</span>
        </div>
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to simulations
        </Link>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      {/* Hero */}
      <div className="flex items-center gap-3 mb-2">
        <BookOpen className="w-7 h-7 text-indigo-400 flex-shrink-0" />
        <div>
          <h1 className="text-xl font-bold text-white">Constellation Simulator — Guide</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            A plain-English introduction to satellite communication coverage analysis
          </p>
        </div>
      </div>

      {/* What is this? */}
      <Section icon={HelpCircle} title="What does this simulator do?">
        <p>
          This tool lets you design a satellite constellation — a fleet of spacecraft orbiting the
          Earth — and ask: <em className="text-gray-300">"How well will it cover the world's oceans?"</em>
        </p>
        <p>
          It answers that by simulating the orbital mechanics and calculating, for every point on
          the globe (or along a sea route), whether at least one satellite above a minimum elevation
          angle is visible at any given moment.
        </p>
        <p>
          The results help you compare different constellation designs before anyone builds a single
          satellite — saving millions in hardware while finding the optimal orbit geometry.
        </p>
      </Section>

      {/* Constellation basics */}
      <Section icon={Satellite} title="Constellation geometry — the basics">
        <p>
          A <span className="text-gray-300 font-medium">Walker constellation</span> is the most
          common satellite arrangement. It places satellites evenly across a set of orbital planes,
          like lanes around a spinning globe.
        </p>
        <div className="space-y-2 mt-1">
          <Param name="Satellites">
            Total number of spacecraft. More satellites → better coverage, higher cost.
            Typical values: 6 (sparse) to 648 (dense LEO megaconstellation).
          </Param>
          <Param name="Planes">
            Number of orbital lanes. Satellites are spread evenly across them.
            Must divide evenly into the total satellite count.
          </Param>
          <Param name="Altitude (km)">
            Height above the Earth's surface. Higher = wider coverage per satellite but
            higher signal delay. LEO is 200–2 000 km. Below ~400 km drag becomes a problem.
          </Param>
          <Param name="Inclination (°)">
            Tilt of the orbital plane relative to the equator. 0° = equatorial orbit (only
            covers tropics). 90° = polar orbit (covers everything). 87.4° is Iridium-like —
            near-polar, global coverage.
          </Param>
          <Param name="Phasing">
            Controls the relative angular offset between satellites in adjacent planes.
            Usually set to 1; rarely changes results significantly.
          </Param>
          <Param name="SSO">
            Sun-Synchronous Orbit — a special near-polar orbit where the spacecraft always
            crosses the equator at the same local solar time. Common for Earth observation;
            less useful for communication coverage.
          </Param>
        </div>
      </Section>

      {/* Min elevation */}
      <Section icon={Globe} title="Minimum elevation angle — why it matters">
        <p>
          A satellite is only useful if it's high enough above the horizon. Near the horizon,
          signals travel through more atmosphere, suffer from multipath, and get blocked by
          terrain or ship superstructures.
        </p>
        <p>
          The <span className="text-gray-300 font-medium">minimum elevation angle</span> (default
          10°) defines the cone above a receiver inside which a satellite must be to count as
          "visible". Raising it (e.g. to 20°) gives more reliable links but reduces coverage
          — fewer satellites will be above that threshold at any location.
        </p>
      </Section>

      {/* Comms payloads */}
      <Section icon={Radio} title="Communication payloads">
        <p>
          Each satellite carries a communication payload. The simulator checks whether the
          satellite–terminal geometry and link budget allow a successful data exchange.
        </p>
        <div className="space-y-2 mt-1">
          <Param name="AIS">
            Automatic Identification System. The current maritime standard — all vessels
            broadcast a short burst every few seconds. Very short range; simple receivers.
          </Param>
          <Param name="VDES">
            VHF Data Exchange System. The next-gen AIS successor endorsed by the IMO. Supports
            bidirectional data, longer messages, more bandwidth. Better suited for IoT/safety
            applications from space.
          </Param>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          "Bidirectional" (bidi) means the satellite both receives and transmits to the vessel —
          required for interactive applications like weather updates or route instructions.
        </p>
      </Section>

      {/* RF Link Budget */}
      <Section icon={Signal} title="RF Link Budget — what the simulator actually computes">
        <p>
          Every contact between a satellite and a ground terminal is validated against a full
          RF link budget. The simulator does not simply check whether a satellite is visible —
          it checks whether the <em className="text-gray-300">signal margin is positive</em>,
          meaning the received SNR exceeds the required threshold after accounting for all losses.
        </p>

        {/* Equation */}
        <div className="bg-gray-800/60 rounded-lg px-4 py-3 font-mono text-xs text-gray-300 leading-loose mt-1">
          <p className="text-indigo-300 font-semibold mb-1 font-sans">Downlink margin (dB)</p>
          <p>M = P<sub>tx,dBm</sub> + G<sub>tx</sub> + G<sub>rx</sub></p>
          <p className="pl-4">− FSPL &nbsp;(32.44 + 20·log d<sub>km</sub> + 20·log f<sub>MHz</sub>)</p>
          <p className="pl-4">− L<sub>rain</sub> &nbsp;(ITU-R P.838 model)</p>
          <p className="pl-4">− (−174 + 10·log B + NF) &nbsp;[noise floor]</p>
          <p className="pl-4">− SNR<sub>req</sub></p>
          <p className="mt-1 text-emerald-400">Link closes when M &gt; 0 dB</p>
        </div>

        <p className="mt-1">Every configurable parameter in Settings → Communications Link Budget feeds directly into this equation:</p>
        <div className="space-y-2 mt-1">
          <Param name="Sat Tx Power + Sat Tx Antenna Gain">
            Together these form the satellite <span className="text-gray-300">EIRP</span>{' '}
            (Effective Isotropic Radiated Power) — the transmit signal strength heading toward Earth.
          </Param>
          <Param name="Ground Rx Gain + Ground Noise Figure">
            These define the receiver <span className="text-gray-300">G/T</span>{' '}
            (antenna gain over noise temperature). Higher gain or lower noise figure = better
            sensitivity. Noise floor = −174 dBm/Hz + 10·log(bandwidth) + noise figure.
          </Param>
          <Param name="DL / UL Frequency (MHz)">
            Sets the free-space path loss (FSPL) and the ITU-R rain attenuation coefficients.
            Higher frequency = more rain loss. AIS/VDES at 162 MHz is almost unaffected by rain;
            Ka-band at 26 GHz can lose 20+ dB in tropical downpours.
          </Param>
          <Param name="Bandwidth (Hz)">
            Determines the thermal noise floor. Wider bandwidth = more noise power collected.
            AIS uses 25 kHz channels; VDES up to 100 kHz.
          </Param>
          <Param name="Required SNR DL / UL (dB)">
            The minimum signal-to-noise ratio at which the receiver can decode the signal.
            Equivalent to the C/N₀ or Eb/N₀ threshold for the chosen modulation and coding
            scheme — set this to match your modem's performance curve.
          </Param>
        </div>

        <p className="mt-2">
          The simulation runs this budget for <span className="text-gray-300">every grid point × every timestep</span>,
          across the entire simulation time window. The heatmap colour represents the fraction of
          timesteps where at least one satellite closed the link — not just whether one was geometrically visible.
        </p>

        <div className="bg-gray-800/60 rounded-lg px-3 py-2 text-xs mt-1">
          <p className="text-yellow-400 font-medium mb-1">What is and is not modelled</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <div>
              <p className="text-emerald-400 font-medium">✓ Included</p>
              <ul className="list-disc list-inside space-y-0.5 text-gray-400 mt-0.5">
                <li>EIRP (Tx power × antenna gain)</li>
                <li>Receiver G/T (gain, noise figure)</li>
                <li>Free-space path loss (FSPL)</li>
                <li>Rain attenuation (ITU-R P.838)</li>
                <li>Thermal noise floor</li>
                <li>Required SNR / Eb/N₀ threshold</li>
                <li>Slant range &amp; elevation geometry</li>
                <li>Bidirectional (uplink + downlink)</li>
              </ul>
            </div>
            <div>
              <p className="text-red-400 font-medium">✗ Not yet modelled</p>
              <ul className="list-disc list-inside space-y-0.5 text-gray-400 mt-0.5">
                <li>Ionospheric scintillation</li>
                <li>Pointing / implementation loss</li>
                <li>Auto-derived modulation coding gain</li>
                <li>Co-channel / adjacent-sat interference</li>
                <li>Doppler shift</li>
              </ul>
            </div>
          </div>
        </div>
      </Section>

      {/* Modes */}
      <Section icon={BarChart2} title="Simulation modes">
        <div className="space-y-3">
          <div>
            <p className="text-gray-200 font-medium flex items-center gap-1.5">
              <Map className="w-4 h-4 text-indigo-400" /> Coverage Heatmap
            </p>
            <p className="mt-0.5">
              Computes coverage for a global grid of points and draws a colour-coded map.
              Green = high availability, red = gap. Best for a quick global overview.
              Resolution controls the grid spacing (5° ≈ fast; 1° ≈ detailed but slow).
            </p>
          </div>
          <div>
            <p className="text-gray-200 font-medium flex items-center gap-1.5">
              <Globe className="w-4 h-4 text-indigo-400" /> Sky Coverage
            </p>
            <p className="mt-0.5">
              Animates the satellite sky above a fixed location (or a set of ocean waypoints)
              over time. Shows the fraction of time at least one satellite is visible. Good
              for evaluating a specific port or chokepoint like the Panama Canal.
            </p>
          </div>
          <div>
            <p className="text-gray-200 font-medium flex items-center gap-1.5">
              <Satellite className="w-4 h-4 text-indigo-400" /> Orbit 3-D View
            </p>
            <p className="mt-0.5">
              Renders the full constellation in a 3-D interactive globe. Useful for
              visually inspecting the geometry — gaps, coverage holes, and polar vs
              equatorial density.
            </p>
          </div>
          <div>
            <p className="text-gray-200 font-medium flex items-center gap-1.5">
              <Navigation className="w-4 h-4 text-indigo-400" /> Ground Track
            </p>
            <p className="mt-0.5">
              Draws the paths each satellite traces over the Earth's surface. Helps
              identify the repeat pattern and how often a satellite flies over any region.
            </p>
          </div>
          <div>
            <p className="text-gray-200 font-medium flex items-center gap-1.5">
              <Navigation className="w-4 h-4 text-indigo-400" /> Route Coverage
            </p>
            <p className="mt-0.5">
              Simulates a vessel sailing a real-world sea route (e.g. North Atlantic, Suez
              Canal corridor) and calculates communication availability along the voyage.
              Outputs a timeline of connected vs. disconnected periods.
            </p>
          </div>
        </div>
      </Section>

      {/* Typical workflow */}
      <Section icon={BookOpen} title="Typical workflow">
        <ol className="list-decimal list-inside space-y-1.5 ml-1">
          <li>
            Start with a <span className="text-gray-300">Coverage Heatmap</span> at 5° resolution
            to quickly compare constellation options (e.g. 66/6 vs 87/12).
          </li>
          <li>
            Increase resolution to 1–2° around the areas you care about (polar regions, shipping
            lanes) to find exact coverage gaps.
          </li>
          <li>
            Switch to <span className="text-gray-300">Sky Coverage</span> at key locations to
            see the time-series: is coverage continuous or patchy?
          </li>
          <li>
            Run <span className="text-gray-300">Route Coverage</span> on the most critical sea
            routes to quantify outage durations for your use case.
          </li>
          <li>
            Use the <span className="text-gray-300">Orbit 3-D view</span> to present results
            visually to stakeholders.
          </li>
        </ol>
      </Section>

      {/* Heatmap vs Route explanation */}
      <Section icon={BarChart2} title="Heatmap coverage vs. Route connectivity — what's the difference?">
        <p>
          These two simulations answer <em className="text-gray-300">different questions</em>. It is
          normal (and expected) to see a green heatmap cell at a location where Route simulation
          reports 0% connectivity.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse mt-1">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-1.5 pr-4 text-gray-300 font-medium"></th>
                <th className="text-left py-1.5 pr-4 text-indigo-300 font-medium">Coverage Heatmap</th>
                <th className="text-left py-1.5 text-emerald-300 font-medium">Route Connectivity</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-800">
                <td className="py-1.5 pr-4 text-gray-400 font-medium">Method</td>
                <td className="py-1.5 pr-4">Geometric elevation check only</td>
                <td className="py-1.5">Full RF link budget (SNR, noise, weather, margin)</td>
              </tr>
              <tr className="border-b border-gray-800">
                <td className="py-1.5 pr-4 text-gray-400 font-medium">Question answered</td>
                <td className="py-1.5 pr-4">"Is a satellite above the horizon?"</td>
                <td className="py-1.5">"Can the link actually close at the required data rate?"</td>
              </tr>
              <tr className="border-b border-gray-800">
                <td className="py-1.5 pr-4 text-gray-400 font-medium">Green / 100% means</td>
                <td className="py-1.5 pr-4">A satellite is above the elevation mask</td>
                <td className="py-1.5">Signal margin is positive — link is usable</td>
              </tr>
              <tr className="border-b border-gray-800">
                <td className="py-1.5 pr-4 text-gray-400 font-medium">Can they disagree?</td>
                <td className="py-1.5 pr-4 text-yellow-400">Yes — heatmap can be green where RF link fails</td>
                <td className="py-1.5 text-yellow-400">Yes — a geometrically visible sat may not close the link</td>
              </tr>
              <tr>
                <td className="py-1.5 pr-4 text-gray-400 font-medium">Use for</td>
                <td className="py-1.5 pr-4">Quick global overview, constellation sizing</td>
                <td className="py-1.5">Service availability planning, SLA estimates</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-1">
          <span className="text-gray-300 font-medium">Which to trust?</span>{' '}
          Route connectivity is the ground truth for real-world service availability — it models the
          full radio link including signal margins. The heatmap is an{' '}
          <span className="text-yellow-400">optimistic upper bound</span>: it shows the best possible
          coverage if the RF link were perfect. Use the heatmap for constellation comparison; use
          Route simulation when estimating actual service uptime.
        </p>
        <p>
          <span className="text-gray-300 font-medium">Typical example:</span>{' '}
          Near New York on the Titan corridor (~40°N), satellites may pass at low elevation angles
          that are geometrically "visible" (heatmap = green) but produce insufficient SNR margin
          for VDES — Route connectivity correctly reports 0%.
        </p>
      </Section>

      {/* Tips */}
      <Section icon={HelpCircle} title="Quick tips">
        <ul className="list-disc list-inside space-y-1.5 ml-1">
          <li>Iridium-like geometry: <span className="font-mono text-indigo-300">66 sats / 6 planes / 87.4° incl</span></li>
          <li>GlobalStar-like: <span className="font-mono text-indigo-300">48 sats / 8 planes / 52° incl / 1 414 km</span></li>
          <li>Polar gap appears if inclination is below ~80° — check arctic coverage separately.</li>
          <li>VDES bidirectional needs a stronger link — expect ~10–15% less coverage than AIS-only.</li>
          <li>Altitude above 800 km enters the Van Allen radiation belt — bad for electronics longevity.</li>
          <li>Give simulations a title after they finish so you can compare results later.</li>
        </ul>
      </Section>
        </div>
      </div>
    </div>
  )
}
