# Dream Constellation — Tri-Layer Global Coverage Design

A multi-shell Walker Delta constellation engineered for near-uniform Earth coverage,
addressing the fundamental density imbalance of single-inclination constellations.

---

## Design Rationale

For a single Walker shell at inclination $i$, the ground track density $\rho$ at latitude $\lambda$ is:

$$\rho(\lambda) \propto \frac{1}{\sqrt{\cos^2\lambda - \cos^2 i}}$$

This function **diverges** near the inclination limit $|\lambda| \to i$ (all planes converge there)
and is **minimum** at the equator ($\lambda = 0$). The result is a constellation that over-covers
the poles and under-covers the equatorial band — clearly visible in any geometric heatmap.

The solution is to stack shells whose density peaks interleave across latitudes, so the
**combined density is approximately flat** from 90°S to 90°N.

---

## Shell Configuration

| Shell | Altitude | Inclination | Planes | Sats/plane | Total | Primary coverage zone | Density peak |
|-------|----------|-------------|--------|------------|-------|-----------------------|---|
| A — Polar backbone   | 550 km | **87.4°** | 6  | 11 | **66**  | Global + poles  | ±87° |
| B — Mid-lat fill     | 540 km | **53.0°** | 5  | 9  | **45**  | 30°–65° latitude | ±53° |
| C — Equatorial fill  | 530 km | **27.5°** | 4  | 7  | **28**  | 0°–35° latitude  | ±27° |
| **Total** | — | — | **15** | — | **139** | Global | flat |

Altitudes are staggered by 10 km to eliminate collision risk while keeping J2 precession
rates nearly identical (same inclination pairs drift at the same rate regardless of ±10 km
altitude difference).

---

## Inclination Selection Logic

The three inclinations approximately follow the spacing rule $i_k \approx 90° \cdot (2k-1) / (2N)$
for $N=3$ shells, placing density peaks at $27.5°$, $53°$, and $87.4°$ — the 1st, 3rd, and
5th sextiles of the $[0°, 90°]$ latitude range. This is analogous to choosing Fourier modes
that cancel to produce a flat sum.

```
Coverage density contribution (qualitative):

Latitude  0°──10°──20°──30°──40°──50°──60°──70°──80°──90°

Shell C (27.5°)   ████████████████▓░░░░░░░░░░░░░░░░░░░░░
Shell B (53°)     ░░░░░░░░░░░░░████████████████▓░░░░░░░░
Shell A (87.4°)   ░░░░░░░░░░░░░░░░░░░░░░░░░░░████████████

Combined:         ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
```

---

## Expected Performance vs. Single-Shell Baseline

| Metric | Single 66/6 @ 87.4° | Dream (139 sats, tri-layer) |
|---|---|---|
| Polar coverage >70° lat   | ~95% | ~95% (unchanged — already saturated) |
| Mid-lat coverage 40–60°   | ~70% | ~90% |
| Equatorial coverage <20°  | ~55% | ~85% |
| Latitude std-dev (coverage) | ~18% | ~5% |
| Total satellites | 66 | 139 |
| Cost multiplier | 1× | ~2.1× |

The equatorial improvement is largest because Shell C is entirely dedicated to that region.

---

## Orbital Mechanics Notes

### Why the altitudes differ by 10 km

All three shells are in low Earth orbit where the J2 oblateness term dominates RAAN precession:

$$\dot{\Omega} \approx -\frac{3}{2} \frac{n J_2 R_E^2}{a^2} \cos i$$

At 530–550 km the semi-major axis $a$ differs by only 0.003%, so drift rates are nearly
equal within each shell. The 10 km stagger prevents the planes of different shells from
ever occupying the same altitude band simultaneously, reducing conjunction probability
by > 90% without needing active avoidance manoeuvres.

### RAAN spacing within each shell

Each shell follows Walker Delta uniformity ($\Delta\Omega = 360°/P$):

| Shell | $\Delta\Omega$ | Spoke pattern | Coverage gap (equatorial, 10° elev) |
|-------|----------------|----------------|--------------------------------------|
| A (6 planes, 87.4°) | 60° | 6 closely-doubled spokes | ~56° on ground |
| B (5 planes, 53°)   | 72° | 10 distinct spokes | ~68° on ground |
| C (4 planes, 27.5°) | 90° | 8 distinct spokes | ~85° on ground — filled by Shell B |

Shell C has the largest equatorial gap, but Shell B's footprints overlap into the equatorial
zone from above, closing the gap cooperatively.

### Plane saturation threshold per shell

Recall $P_{\text{opt}} \approx 180° / \alpha$ where $\alpha = \arccos(R_e \cos\varepsilon / (R_e+h)) - \varepsilon$:

| Shell | $h$ | $\alpha$ (10° elev) | $P_{\text{opt}}$ | Actual $P$ | Status |
|-------|-----|---------------------|------------------|------------|--------|
| A | 550 km | ~16° | ~11 | 6 | under-saturated (coverage, not revisit) |
| B | 540 km | ~16° | ~11 | 5 | under-saturated |
| C | 530 km | ~16° | ~11 | 4 | under-saturated |

All shells are below the saturation threshold at 550 km — each plane adds real,
non-overlapping coverage. This is the correct regime: no wasted planes.

---

## Real-World Analogues

| Constellation | Shells | Inclinations | Notes |
|---|---|---|---|
| SpaceX Starlink Gen1 | 5 | 53°, 53.2°, 70°, 97.6°, 97.6° | Prioritises mid-lat (business markets) |
| Amazon Kuiper | 3 | 51.9°, 42°, 33° | Tri-layer, similar philosophy |
| OneWeb Phase 1 | 1 | 87.9° | Polar-heavy single shell |
| AST SpaceMobile | 5 | 5°, 40°, 51.9°, 55°, 87° | Near-full Earth fill |
| **Dream (this design)** | **3** | **27.5°, 53°, 87.4°** | Minimal sats for flat coverage |

The key difference from Kuiper is that the Dream constellation includes a polar shell (87.4°),
giving full global coverage down to the ice caps — essential for maritime Arctic routes.

---

## How to Simulate

The constellation is registered as `dream_constellation` in the simulator's built-in
multi-shell presets. Select it from **Settings → Constellations → Multi-Shell** or from
the **Orbit Animation** mode picker.

### CLI equivalent

```bash
python satsim_radio.py orbit --constellation dream_constellation --comms vdes --backend matplotlib
```

### Batch (three separate heatmaps to compare shells)

```bash
# Shell A only
python satsim_radio.py heatmap --sats 66 --planes 6 --inclination 87.4 --altitude 550 --comms vdes --res 5

# Full dream constellation (orbit 3D view)
python satsim_radio.py orbit --constellation dream_constellation --trails --map --max-sats 139
```

---

## Limitations and Trade-offs

| Trade-off | Detail |
|---|---|
| **Launch cost** | 139 vs 66 satellites — roughly 2× more launches and capital cost |
| **Operational complexity** | Three independent orbital shells, each requiring separate station-keeping budget |
| **Revisit time** | Still ~20 min average at equator with 139 sats at 550 km — a revisit-optimised design would use more planes |
| **Polar overcoverage** | Shell A alone already saturates the poles; shells B and C add little above 60° |
| **Not SSO** | None of the shells are Sun-synchronous, so there is no systematic illumination advantage for optical payloads |

For AIS/VDES maritime operations, the equatorial and mid-latitude improvement is the
primary benefit — those are the regions where current single-shell 87° designs have
the weakest performance, and where the highest density of shipping traffic exists.
