# 📡 Coverage Capacity & Service Eligibility Framework

### Executive Summary
This framework classifies the **140 coverage points** based on Duty Cycle (Connectivity %) to determine viable commercial use cases.

---

### 1. Service Classification Matrix

| Tier / Map Legend | Connectivity | Service Class | Eligible Use Cases | Operational Limitations |
| :--- | :--- | :--- | :--- | :--- |
| 🟢 **Tier 5** | **> 95%** | **Mission Critical** | • Anti-Piracy / Security<br>• SAR (Search & Rescue)<br>• Just-in-Time Logistics | **None.** Near real-time visibility (<5 min latency). |
| 🟢 **Tier 4** | **70% – 95%** | **Premium** | • High-Value Cargo Tracking<br>• Regulatory Compliance<br>• Route Optimization | **Minor Gaps.** Occasional 10-15 min delays, but rarely misses a major event. |
| 🟡 **Tier 3** | **50% – 70%** | **Standard** | • Fleet Management<br>• ETA Updates (Hourly)<br>• General Shipping | **Moderate Gaps.** Will miss quick maneuvers, but captures general transit progress. |
| 🟠 **Tier 2** | **30% – 50%** | **Basic / Economy** | • Daily Reporting<br>• Asset Recovery (Post-theft)<br>• Non-Critical Monitoring | **Significant Blind Spots.** Gaps >40 mins allowed. **Not for security.** |
| 🔴 **Tier 1** | **10% – 30%** | **Low-Duty IoT** | • Smart Buoys / Fishing Nets<br>• Scientific Sensors<br>• "Keep-Alive" Heartbeats | **Data Logging Only.** Real-time access is impossible. Data arrives in bursts. |
| ⚫ **Tier 0** | **< 10%** | **No Service** | • None reliably. | **Dead Zone.** Functionally useless for commercial operations. |

---

### 2. Geographic Interpretation Guide

When analyzing the map clusters, use these diagnostic rules:

* **The "Gold" Zone (>95%)**
    * *Geography:* Typically Mid-Latitudes ($20^{\circ} - 50^{\circ}$).
    * *Commercial Strategy:* Sell as **"Security Grade"** coverage.
* **The "Standard" Zone (50% - 70%)**
    * *Geography:* Equatorial regions (plane spacing) or High Latitudes (inclination edge).
    * *Commercial Strategy:* Valid for logistics, but **enforce Latency SLAs**.
* **The "Danger" Zone (<30%)**
    * *Geography:* The "Polar Hole" ($>60^{\circ}$ Lat) or deep ocean (no Ground Stations).
    * *Commercial Strategy:* **Do not sell** unless for simple daily logging.

---

### 3. Classification Logic (Python Snippet)

Use this logic to tag your dataset automatically:

```python
def classify_coverage(percent):
    if percent >= 95:
        return "Tier 5: Mission Critical"
    elif percent >= 70:
        return "Tier 4: Premium Commercial"
    elif percent >= 50:
        return "Tier 3: Standard"
    elif percent >= 30:
        return "Tier 2: Basic Economy"
    elif percent >= 10:
        return "Tier 1: Low-Duty IoT"
    else:
        return "Tier 0: No Service"
