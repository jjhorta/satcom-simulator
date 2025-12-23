# 📱 MSS & D2D Service Eligibility: The Power Paradigm

### Executive Summary
In the context of Direct-to-Device (D2D) using unmodified smartphones, **Received Power (SNR / Link Margin)** supersedes simple geometric "connectivity" as the primary determinant of service.

While AIS/VDES terminals are purpose-built with optimized antennas, D2D contends with the **"Smartphone Handicap"** (low-gain antennas, body blockage). Therefore, service eligibility acts as a **"Waterfall"**: as SNR increases, you unlock higher tiers of service (SMS $\to$ Voice $\to$ Data).

---

### 1. The Physics: The "Waterfall" Effect

In D2D, we do not just ask "Is the satellite visible?" (Geometry). We ask "Is the link strong enough?" (Physics). The fundamental constraint is the **Shannon-Hartley Theorem**:

$$C = B \cdot \log_2(1 + \text{SNR})$$

As **SNR** drops (due to low elevation angle, foliage, or building entry), the Capacity ($C$) collapses. This creates concentric **Service Cones** rather than a uniform coverage circle.

---

### 2. D2D Service Eligibility Matrix (Power-Based)

Unlike AIS (which is binary: works or doesn't), D2D has distinct **Quality of Service (QoS)** tiers based on Link Margin.

| Service Tier | Service Type | Est. Required SNR ($C/N_0$) | Bandwidth | Critical Constraint |
| :--- | :--- | :--- | :--- | :--- |
| 🟢 **Tier 3** | **Broadband Data**<br>(Web/Video) | **> 10-15 dB** | High<br>(> 1 MHz) | **Link Margin.** Requires Line-of-Sight (LOS) + High Elevation (>40°). *Unlikely to work indoors.* |
| 🟡 **Tier 2** | **Voice**<br>(VoLTE/VoNR) | **3 - 6 dB** | Medium<br>(~30 kHz) | **Jitter & Packet Loss.** Dropping below 3dB causes robotic voice or call drops. |
| 🟠 **Tier 1** | **Text / SMS**<br>(Basic Messaging) | **-10 dB to 0 dB** | Low<br>(< 5 kHz) | **Time / Latency.** Can use extreme coding gain (repetition) to punch through noise, but message takes seconds to send. |
| �� **Tier 0** | **Beaconing**<br>(SOS / Location) | **< -15 dB** | Ultra-Low | **None.** Works even in pocket, partial foliage, or edge of cell (LoRa-like characteristics). |

---

### 3. The Mapping Implication: The "Shrinking Cone"

If your map shows "100% Connectivity," it only means the satellite is *visible*. The **Effective Service Area** shrinks for higher tiers.

* **Horizon (0° - 20° Elevation):** Path is long, atmosphere is thick.
    * *Service:* **Tier 1 (SMS Only)**
* **Mid-Sky (20° - 45° Elevation):** Path is shorter, better gain.
    * *Service:* **Tier 2 (Voice + SMS)**
* **Zenith (> 45° Elevation):** Shortest path, maximum power.
    * *Service:* **Tier 3 (Data + Voice + SMS)**

> **Mapping Rule:** A map of "Broadband Eligibility" might only be **30%** of the size of the "SMS Eligibility" map for the same satellite pass.

---

### 4. Comparison: Legacy VDES vs. Future MSS

| Feature | Legacy VDES / AIS | Future MSS D2D |
| :--- | :--- | :--- |
| **Limiting Factor** | **Time** (Geometry / Gaps) | **Power** (Link Budget / SNR) |
| **User Antenna** | High Gain (Ship Mast) | Negative Gain (Phone in Hand, -3 dBi) |
| **Service Gradient** | **Binary** (Works / Broken) | **Gradient** (Data $\to$ Voice $\to$ SMS) |
| **Building Entry** | Irrelevant (Ships are outside) | **Critical** (High power needed for Indoor service) |


# ⚔️ D2D Architecture Wars: "Brute Force" vs. "Orbital Swarm"

### Executive Summary
To overcome the weak signal of a standard smartphone (-3 dBi gain), satellite operators must close the link budget. There are two opposing engineering philosophies to achieve the required **Signal-to-Noise Ratio (SNR)** for service eligibility.

---

### 1. Approach A: The "Brute Force" Aperture (AST SpaceMobile)
**Philosophy:** *Put the cell tower in space.*
AST focuses on launching fewer, massive satellites with enormous unfolded phased-array antennas to maximize sensitivity ($G/T$) and transmit power (EIRP).

* **The Mechanism:**
    * **Huge Aperture:** Satellites like *BlueWalker 3* and *BlueBird* unfold to sizes exceeding $64m^2$ (and eventually larger).
    * **High Gain:** The massive surface area acts as a giant "ear," allowing it to pick up weak signals from phones even at lower elevation angles or inside buildings.
    * **Service Impact:** Aims to support **Tier 3 (Broadband/Video)** immediately upon launch, even with a sparse constellation, because a single satellite has a massive "Service Cone."

> **Analogy:** AST is like a **Floodlight**. One light is powerful enough to illuminate a whole stadium brightly.

---

### 2. Approach B: The "Swarm" Density (Starlink / SpaceX)
**Philosophy:** *Blanket the sky with infrastructure.*
Starlink leverages its launch advantage to deploy thousands of satellites. While individual D2D payloads are smaller/less powerful than AST's, the sheer number of satellites solves the link budget via geometry.

* **The Mechanism:**
    * **Standardized Bus:** Uses the "V2 Mini" or "V3" bus. The D2D antenna is large (~25 $m^2$) but significantly smaller than AST's arrays.
    * **Geometric Gain:** By having thousands of satellites, the probability of having a satellite at **Zenith (directly overhead)** is near 100%.
    * **Service Impact:**
        * *Phase 1:* **Tier 1 (Text/SMS)**.
        * *Phase 2:* As density increases, the "Voice/Data Cones" overlap, eventually allowing continuous **Tier 2/3** service.

> **Analogy:** Starlink is like **Streetlights**. Individual lights are smaller, but if you place them every 10 meters, the entire street is lit.

---

### 3. Technical Comparison Matrix

| Feature | **AST SpaceMobile** (Brute Force) | **Starlink D2D** (Swarm) |
| :--- | :--- | :--- |
| **Primary Variable** | **Aperture Size ($m^2$)** | **Constellation Density ($N$)** |
| **Link Margin Strategy** | High Gain Antenna closes the link even at cell edges. | Short Slant Range (Overhead) closes the link. |
| **Service Eligibility** | **Broadband First.** Designed for data/video from Day 1. | **Text First.** Progressing to Voice/Data as satellite count grows. |
| **Indoor Coverage** | **Better Potential.** High link margin can penetrate walls (Deep Indoor). | **Challenging.** Likely requires near-window or outdoor visibility initially. |
| **MIMO Capability** | **High.** Large array allows distinct spatial separation for true MIMO. | **Limited.** Relies on single-beam or limited beamforming per user. |
| **Deployment Risk** | **Mechanical.** Unfolding massive structures in space is complex. | **Regulatory/Scale.** Requires thousands of launches to reach full capacity. |

---

### 4. Summary for Service Mapping

When mapping "Service Eligibility" for these two providers:

* **AST Map:** You map large, high-power circles. A user entering the circle immediately jumps to **Tier 3 (Data)**.
* **Starlink Map:** You map a "Probability Density Function."
    * *Low Density:* User has **Tier 1 (Text)**.
    * *High Density:* User eventually gets **Tier 2 (Voice)**.
    * *Zenith Pass:* Brief bursts of **Tier 3 (Data)**.