# RAAN — Right Ascension of the Ascending Node
## A Physics Tutorial for Constellation Design

---

## 1. What is the Ascending Node?

A satellite in a non-equatorial orbit crosses the equatorial plane twice per revolution:

- **Ascending node** — crossing from south to north (going up)
- **Descending node** — crossing from north to south (going down)

The **ascending node** is the reference crossing. Its position is measured as an angle along the equator, eastward from the **vernal equinox** (the direction the Sun points at the March equinox, fixed in inertial space).

---

## 2. RAAN Definition

**RAAN (Ω)** is the angle between the vernal equinox direction and the ascending node, measured eastward in the equatorial plane:

$$\Omega \in [0°, 360°)$$

It answers: *"at what longitude does this orbital plane cut through the equator, going northbound?"*

```
                 ♈ Vernal Equinox (fixed stars)
                  ↑
         ─────────┼─────────  Equatorial plane
                  │   Ω
                  └──────────→  Ascending node
```

RAAN is measured in the **inertial frame** (fixed to distant stars), not to Earth's surface. A satellite with Ω = 90° crosses the equator northbound when it's 90° east of the vernal equinox — regardless of what time it is or where the Earth has rotated.

---

## 3. RAAN in a Walker Delta Constellation

In a Walker Delta constellation with **P planes**, the planes are spread evenly around the equator:

$$\Delta\Omega = \frac{360°}{P}$$

For the 66/6 constellation used in this simulator:

$$\Delta\Omega = \frac{360°}{6} = 60°$$

| Plane | RAAN |
|-------|------|
| 1     | 0°   |
| 2     | 60°  |
| 3     | 120° |
| 4     | 180° |
| 5     | 240° |
| 6     | 300° |

This uniform spacing maximises coverage uniformity — no region of Earth is ever far from a satellite pass.

---

## 4. RAAN and Orbital Plane Geometry

Every RAAN value defines a **great circle** tilted by the inclination angle from the equator. The full orbital plane is a flat disk cutting through the Earth's centre, like a slice through an orange.

For inclination **i = 87°**:

```
Side view (edge-on to equator):

  North Pole
      ↑
      |  87°
      | ╱
──────╳──────  Equatorial plane
      |╲
      | ╲ 
      ↓
  South Pole
```

The orbital plane is nearly but not exactly vertical — tilted 3° from polar.

Two planes with RAANs exactly **180° apart** (e.g. Ω=0° and Ω=180°) are:
- At **90° inclination**: the **same physical plane** (both contain the polar axis)
- At **87° inclination**: two **distinct planes** that are very nearly parallel near the poles, separated by ~2× the 3° inclination offset

This is why 6 Walker planes at 87° produce **6 closely-paired spokes** rather than 6 distinct spokes when viewed from the pole — the pairs (Ω=0°/180°, Ω=60°/240°, Ω=120°/300°) nearly overlap.

---

## 5. The Spoke Counting Rule

Viewed from directly above the north pole, each orbital plane appears as a line through the centre. Each plane contributes **2 spokes** — one for the ascending leg, one for the descending leg:

$$\text{Total spokes} = 2P$$

But planes with RAANs exactly 180° apart are **co-planar at i=90°**, collapsing to the same line:

$$\text{Visible spokes at } i=90° = \frac{2P}{2} = P$$

At **87°** (not exactly polar), both spokes still exist but are nearly coincident:

$$\text{Visible spokes at } i=87° \approx P \text{ (closely doubled)}$$

**Counter-example**: 5 planes at 87°  
$\Delta\Omega = 72°$ — no pair of planes is separated by exactly 180°, so all 10 spokes are visually distinct.

| Planes | $\Delta\Omega$ | Spoke pairs coincide? | Visible spokes |
|--------|---------------|----------------------|----------------|
| 4      | 90°           | Yes                  | 4              |
| 5      | 72°           | No                   | 10             |
| 6      | 60°           | Yes                  | 6              |
| 7      | ~51.4°        | No                   | 14             |
| 8      | 45°           | Yes                  | 8              |

**Rule**: If P is even, opposite planes overlap → visible spokes = P. If P is odd, no overlap → visible spokes = 2P.

---

## 6. RAAN Drift — The Hidden Dynamic

RAAN is not static in real life. The Earth's equatorial bulge (J2 oblateness term) causes the orbital plane to **precess** — Ω drifts over time:

$$\dot{\Omega} = -\frac{3}{2} \frac{n J_2 R_E^2}{(1-e^2)^2 a^2} \cos i$$

Where:
- $n$ = mean motion (rad/s)
- $J_2 = 1.08263 \times 10^{-3}$ — Earth's oblateness coefficient
- $R_E$ = Earth radius
- $a$ = semi-major axis
- $e$ = eccentricity
- $i$ = inclination

Key consequences:

**At i = 87°**: $\cos(87°) \approx +0.052$ → slow positive drift ≈ +0.05°/day  
**At i = 90°** (true polar): $\cos(90°) = 0$ → **no drift**  
**At i ≈ 98.2°** (SSO): drift = exactly **+0.9856°/day**, matching the Sun's apparent motion → the orbit stays Sun-synchronous

For a Walker constellation, all planes must be at the **same altitude and inclination** so they drift at the same rate and the 60° spacing is preserved indefinitely. Mixed-altitude constellations gradually lose their RAAN spacing.

---

## 7. RAAN vs. Longitude of the Ascending Node

A common point of confusion:

| | RAAN (Ω) | Longitude of ascending node (λ) |
|---|---|---|
| Reference frame | Inertial (fixed stars) | Earth-fixed (rotates with Earth) |
| Changes with time? | Only due to J2 precession | Changes every second as Earth rotates |
| Used for | Orbital mechanics | Ground track prediction |

A satellite with Ω = 0° crosses the equator northbound at the longitude corresponding to 0° in inertial space **at that moment** — which changes by 360° every 24 hours as Earth rotates beneath it.

---

## 8. Practical Implications for the Simulator

### Coverage uniformity

The 60° RAAN spacing of the 66/6 constellation ensures that at any point on Earth's surface above ±87° latitude, a satellite is always within ≈10° of elevation — the gap between planes in the equatorial region is:

$$\text{Equatorial gap} = 60° \times \frac{R_E}{R_E + h} \approx 56° \text{ on the ground at 600 km}$$

At 87° inclination, the coverage is denser at high latitudes (planes converge toward the poles) and sparser near the equator — visible in the geometric heatmap as the green band near ±80°.

### Why the heatmap is green at the poles and red at mid-latitudes

```
Latitude 80°: many planes simultaneously visible → high coverage %
Latitude  0°: planes spread 60° apart, gaps between them → lower coverage %
```

### RAAN and the RF heatmap difference

The RF heatmap produces a similar but stricter pattern: at high elevations (near poles where many planes converge), FSPL is lower and the link budget closes more easily. At low elevations near the equatorial gaps, slant range is longer and the link may fail — widening the red equatorial band compared to the geometric heatmap.

---

## 9. Coverage Overlap and the Plane Saturation Threshold

### Footprint geometry

Each satellite covers an Earth cap of angular radius $\alpha$ (the half-angle from the sub-satellite point to the edge of coverage, measured from Earth's centre):

$$\alpha = \arccos\!\left(\frac{R_e \cos\varepsilon_{\min}}{R_e + h}\right) - \varepsilon_{\min}$$

Where $\varepsilon_{\min}$ is the minimum elevation angle required for a usable link (typically 10° for maritime, 5° for AIS broadcast).

For two planes to provide **independent** (non-overlapping) coverage at the equator, their RAAN spacing must exceed $2\alpha$:

$$\Delta\Omega > 2\alpha \quad \Rightarrow \quad \text{no equatorial overlap}$$

### The diminishing-returns threshold

The optimal number of planes is roughly where each footprint diameter equals the plane spacing:

$$P_{\text{opt}} \approx \frac{180°}{\alpha}$$

| Altitude | $\varepsilon_{\min}=10°$ | $\alpha$ | $P_{\text{opt}}$ | 6-plane spacing | Verdict |
|---|---|---|---|---|---|
| 600 km  | — | ~16° | **~11 planes** | 60° — no overlap | 6 planes *under*-saturated |
| 1200 km | — | ~24° | **~7 planes**  | 60° — ~20% overlap | Near the efficiency knee |
| 2000 km | — | ~33° | **~5 planes**  | 60° — full overlap | 6 planes *over*-saturated |

### Why 6 planes ≈ 3 planes at high altitudes

Once $\alpha > 30°$ (altitude ≳ 1500 km), adjacent footprints overlap so deeply that the incremental coverage added by each new plane is negligible. Specifically:

- At the equator: planes 1, 3, 5 already collectively cover the full belt → planes 2, 4, 6 are redundant
- Near the poles: planes always converge regardless of altitude, so polar coverage is already 100% with even 2–3 planes

The result is that doubling the plane count from 3 to 6 **at LEO >1200 km** produces nearly identical geometric coverage statistics — as visible when comparing heatmaps for those configurations.

### Breaking the symmetry: why more planes still help

Even when geometric footprints overlap, more planes improve:

1. **Revisit time** — more planes mean shorter gaps between consecutive passes at any ground point
2. **Simultaneous visibility** — two or more satellites visible at once enables Doppler rejection, multi-path diversity, or handover-free links
3. **RF margin** — overlapping footprints mean a better-elevation satellite is almost always available, reducing the average slant range and improving the link budget
4. **Fault tolerance** — losing one plane degrades coverage less severely

So the geometric heatmap (coverage %) is a **necessary but not sufficient** metric. The RF heatmap captures point 3, and a revisit-time analysis (not yet implemented) would capture point 1.

### Rule of thumb for Walker Delta design

$$\text{If } h < \frac{R_e}{P \sin(180°/P) / \cos\varepsilon_{\min} - 1} \quad \text{→ planes are under-saturated, add more}$$

Or, more practically:

> **At 600 km, 6 planes adds genuine coverage. At 1800 km, you need only 4–5 planes to saturate. Beyond that, extra planes buy revisit time, not area coverage.**

---

## 10. Summary

| Concept | Symbol | What it controls |
|---------|--------|-----------------|
| RAAN | Ω | Which direction the orbital plane faces in inertial space |
| RAAN spacing | ΔΩ | How evenly planes cover all longitudes |
| J2 precession | $\dot{\Omega}$ | Long-term drift of the plane orientation |
| SSO inclination | i ≈ 98.2° | Drift rate matched to Sun's motion |
| Spoke count | 2P or P | Visual polar appearance depending on inclination parity |

---

## 11. Further Reading

- Vallado, D.A. — *Fundamentals of Astrodynamics and Applications* (Chapter 3)
- Walker, J.G. — *Satellite Constellations*, JBIS 1984
- ITU-R S.580 — Coordination of geostationary satellite networks (RAAN assignments)
- [NASA J2 perturbation reference](https://spaceflight.nasa.gov/realdata/sightings/SSapplications/Post/JavaSSOP/SSOP_Help/tle_def.html)
