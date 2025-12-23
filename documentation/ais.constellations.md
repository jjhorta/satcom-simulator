### 1. Active AIS Constellations Specification Matrix

| Constellation / Operator | Est. Active Satellites | Primary Inclination ($i$) | Orbital Geometry (Planes) | Type / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Spire Global (Lemur-2)** | ~100+ | **Mixed:**<br>• Sun-Synchronous (~97°)<br>• ISS (~51.6°)<br>• Equatorial (Rare) | **Ad-Hoc:** No fixed planes. Satellites are drifted into random phasing from ride-share injections. | **Dedicated AIS & Weather.** Largest fleet. High revisit rate due to mixed inclinations. Includes legacy exactEarth assets. |
| **Iridium NEXT (Aireon)** | 66 (Active) | **86.4°** (Polar) | **Walker Star:**<br>6 Planes<br>11 Sats per plane | **Hosted Payload.** The "Gold Standard" for latency. Real-time (RT) data via Inter-Satellite Links (ISL). |
| **Orbcomm (OG2)** | ~17 | **~52°** (Mid-Latitude) | **Drifting Planes:**<br>45°–52° Inclination<br>Spread via nodal precession. | **M2M/IoT + AIS.** Excellent mid-latitude coverage but strictly limited polar visibility (The "Polar Hole" applies here). |
| **HawkEye 360** | ~30 (Clusters) | **Hybrid:**<br>• Clusters 1–5, 7, 10: **~97°** (SSO)<br>• Clusters 6, 8, 9: **~40–46°** | **Formation Flying:**<br>Triplets (3 sats) flying in formation for RF trilateration. | **RF Intelligence (SIGINT).** Primary mission is RF geolocation; AIS is secondary for correlation. |
| **Unseenlabs** | ~15 | **~98°** (SSO) | **Sun-Synchronous:**<br>Optimized for global revisit. | **RF/SIGINT.** Mono-satellite geolocation technology. Focus on "Dark Vessel" detection. |

---

### 2. Detailed Technical Breakdown

#### **A. Spire Global (Lemur-2)**
* **Architecture:** 3U CubeSats.
* **Deployment Strategy:** Spire utilizes an "agile" constellation approach. They launch constantly on diverse rockets (SpaceX, Rocket Lab, Soyuz, PSLV).
* **Planes:** There are no defined planes. They rely on **Differential Drag**. By deploying into a specific orbit and changing the drag profile of the satellite (tilting solar panels), they force the satellites to drift apart along the orbit, spreading them out over time to minimize gaps.
* **Coverage:** Global (due to SSO usage) with intensified revisit at mid-latitudes (due to ISS/Mid-inclination injections).

#### **B. Iridium NEXT (Aireon / exactView RT)**
* **Architecture:** Hosted Payload (Aireon) on Iridium NEXT bus.
* **Geometry:** The only true **Walker Star** constellation in this list.
* **Inclination:** 86.4°.
* **Performance:** Because Iridium satellites talk to each other (ISL), AIS data picked up in the middle of the Pacific is cross-linked to a gateway immediately.
* **Latency:** <1 second (Theoretical), <15 seconds (Real-world). This is the fastest commercially available AIS.

#### **C. Orbcomm (OG2)**
* **Architecture:** Dedicated M2M satellites with AIS capability.
* **Geometry:** Designed largely around the **45°–52°** inclination bands.
* **Limitation:** This constellation cannot see the North Pole. It is optimized for shipping lanes between ±60° Latitude.

#### **D. HawkEye 360 (RF Geolocation)**
* **Architecture:** "Clusters" of 3 microsatellites flying in close formation.
* **Purpose:** They detect the *RF energy* of a marine radar or radio.
* **Why Inclination Matters:** They recently started launching into **Mid-Inclination (40°–45°)** orbits (Clusters 6, 8, 9) specifically to increase revisit rates over high-traffic conflict zones (e.g., Ukraine, Taiwan, Middle East) which are in mid-latitudes, sacrificing polar coverage for these specific clusters.