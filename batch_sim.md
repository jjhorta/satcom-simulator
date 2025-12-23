🛰️ Simulation Rationale: Constellation Architecture Analysis

1. Objective

The goal of the simulate_scenarios.sh batch script is to empirically compare two initial deployment options for a 12-satellite LEO AIS/VDES constellation against:

A future "Phase 2" expansion (24 satellites).

Existing market competitors (Legacy AIS providers and Iridium MSS).

The simulation evaluates Geometric Coverage (Revisit Time) and RF Link Reliability (Signal-to-Noise Ratio) across critical global maritime chokepoints.

2. The Scenarios

🔵 Phase 1: The Trade-Off (12 Satellites)

With only 12 satellites in LEO (600 km), continuous coverage is impossible. The engineering challenge is optimizing Revisit Time (how often a ship gets a signal).

Scenario 1: Option A (Concentrated Planes)

Config: Walker 53° : 12 / 3 / 1 (3 Planes, 4 Satellites each).

Rationale: Placing 4 satellites in a plane creates a "longer train." A ship will see satellites for a longer continuous block of time (e.g., 20 mins), allowing for large file uploads (VDES).

Downside: The gap between the 3 planes is wide. Ships may wait 40+ minutes between passes.

Scenario 2: Option B (Distributed Planes) - RECOMMENDED

Config: Walker 53° : 12 / 4 / 1 (4 Planes, 3 Satellites each).

Rationale: Spreading the same 12 satellites into 4 planes reduces the gap between orbital passes.

Benefit: Ships see a satellite more frequently (shorter wait times), even if the pass duration is slightly shorter. This is superior for AIS/Tracking where frequent position updates are more valuable than bulk data transfer.

🟢 Phase 2: Full Deployment (24 Satellites)

Scenario 5: The Expansion

Config: Walker 53° : 24 / 8 / 1 (8 Planes, 3 Satellites each).

Rationale: This simulates doubling the fleet by inserting new planes between the Phase 1 planes.

Expected Outcome: Revisit time should drop to < 10 minutes at mid-latitudes, offering a "Near-Real-Time" service comparable to larger constellations.

🔴 The Benchmark Competitors

Scenario 3: Legacy AIS (e.g., Spire/exactEarth)

Config: ~60 Satellites, Sun-Synchronous Orbit (SSO ~98°).

Physics: SSO orbits cluster at the poles. They offer 100% coverage of the Arctic but have larger gaps at the Equator compared to inclined orbits.

Comparison: Use this to prove your 53° constellation performs better at the Panama Canal and Malacca Strait (where most shipping is).

Scenario 4: MSS Standard (Iridium NEXT)

Config: 66 Satellites, Polar (86.4°), 780 km.

Physics: The "Gold Standard." L-Band frequencies (Rain robust) + massive density = 100% uptime.

Comparison: This serves as the "Ceiling." If your 12-sat constellation achieves 15-20% connectivity compared to Iridium's 100%, you can validate your "Low Cost / Low Data" business model.

3. Interpreting the Outputs

The batch script generates three types of data for each scenario:

1. 3D Orbit View (view=orbit)

What to look for: The symmetry of the "Birdcage" around Earth.

Check: Verify that Phase 2 (8 planes) looks like a significantly tighter net than Phase 1.

2. Ground Track (view=track)

What to look for: The sine-wave gaps.

Check: Measure the horizontal distance between red lines at the Equator. Wider gaps = Longer wait times for ships.

3. Coverage Analysis (view=sky)

Data: Generates coverage_*.csv.

Metric: connectivity_pct (Percentage of time a link is valid).

Key Insight:

AIS (VHF): Expect high percentages even at low elevations due to low path loss.

VDES (VHF): Similar to AIS but requires slightly higher SNR.

Ku-Band: Will show lower percentages in "Storm" weather due to rain fade logic.

4. Physics Engine Settings

SGP4 Propagator: Deterministic orbital mechanics.

Link Budget: Duplex (Uplink + Downlink). The link is only "UP" if both the ship (low power) can reach the satellite AND the satellite can reach the ship.

Weather: Set to STORM (25mm/hr rain) to simulate worst-case reliability.