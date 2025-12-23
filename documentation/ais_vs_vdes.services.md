# 🛰️ Technical Analysis: AIS vs. VDES Service Eligibility

### 1. The Fundamental Distinction: Broadcast vs. Transactional
The primary reason VDES requires stricter connectivity thresholds than AIS lies in the protocol architecture.

| Feature | Legacy AIS (Class A/B) | VDES (VDE-Sat) |
| :--- | :--- | :--- |
| **Protocol Type** | **"Fire and Forget" (Broadcast)** | **Transactional (Two-Way)** |
| **Success Criteria** | Single packet reception (~30ms) | Complete session maintenance (Handshake $\to$ Transfer $\to$ ACK) |
| **Packet Loss Tolerance**| **High.** If the satellite misses 5 packets but catches the 6th, the location update is successful. | **Zero/Low.** Dropped packets trigger re-transmission requests (ARQ), consuming valuable pass time. |
| **30% Connectivity** | ✅ **Survivable.** (Location updates occur, just less frequently). | ❌ **Critical Failure.** (Sessions time out before data transfer completes). |

---

### 2. The "30% Connectivity" Failure Mode
In a scenario with **30% Connectivity** (approx. 18 minutes visibility / 42 minutes gap), VDES faces specific operational hurdles that AIS does not:

#### **A. Link Setup Overhead**
* **AIS:** Transmits immediately upon visibility.
* **VDES:** Requires a handshake sequence (Announcement $\to$ Request $\to$ Grant $\to$ Data).
* *Impact:* This administrative traffic eats into the already limited 18-minute window, effectively reducing the "useful" data time to ~12-15 minutes.

#### **B. The Modulation Penalty (MCS)**
* **AIS:** Uses robust GMSK modulation. It works even at very low elevations (noisy environments).
* **VDES:** Uses higher-order modulation (e.g., 16-QAM) to achieve high throughput. These modes require a high Signal-to-Noise Ratio (SNR).
* *Impact:* At the edges of coverage (where connectivity is spotty), the satellite may be visible, but the signal is too weak for VDES high-speed modes. The system falls back to lowest speeds or fails to sync.

#### **C. "Broken Pipe" Syndrome**
* **Scenario:** A vessel attempts to download a 2MB Electronic Navigation Chart (ENC).
* **Result:** If the transfer is 80% complete when the satellite sets (entering the 42-minute gap), the session breaks. Depending on the implementation, the vessel may have to restart the transfer from zero when the next satellite appears 42 minutes later.
* *Conclusion:* "Just-in-Time" data becomes impossible.

---

### 3. The "Throughput Trap" & The Digital Cliff
When mapping coverage, the fall-off behavior differs significantly between the two technologies.

> **The VDES Equation:**
> $$\text{Total Data Volume} = \text{Connectivity Time} \times \text{Average Throughput (MCS)}$$

* **AIS Service Fade (Linear):** As you move away from the constellation core, you simply get fewer points on the map. It is a graceful degradation.
* **VDES Service Fade (The Cliff):** As you move away, you lose **Time** (geometry) AND **Speed** (lower MCS due to distance).
    * *Result:* Service capability drops off a "cliff." A zone with 30% AIS utility might have **0% VDES utility**.

---

### 4. Strategic Mapping Recommendations

If you are building a commercial coverage map for VDES:

1.  **Shift the "Red" Line:** Treat anything below **50% Connectivity** as "No Service" for data applications.
2.  **Change the Metric:** Instead of "% Time," map **"Max Transfer Size per Pass."**
    * *Example:* "In this zone, you can transfer 100KB per hour." (This is actionable data for a Captain).
3.  **Hybrid Definition:** Clearly demarcate **Deep Ocean** (Satellite VDES - Low Bandwidth/High Latency) vs. **Coastal** (Terrestrial VDES - High Bandwidth/Real-time).
