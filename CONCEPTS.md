# Tower Crane Structural Analysis - Key Concepts

## Overview

This document explains the structural analysis methodology for flat-top tower cranes. It covers load paths, analysis methods, and key formulas used in the calculations.

---

## 1. Load Path

```
┌─────────────────────────────────────────────────────────────┐
│                     LOAD PATH DIAGRAM                       │
└─────────────────────────────────────────────────────────────┘

     Payload (lifting)
           ↓
    ┌──────────────────────┐
    │        JIB            │ ← SFD, BMD, Stress, Deflection
    │  (Main arm, 60m)     │
    └──────────────────────┘
           ↓ M, V, Fz
    ┌──────────────────────┐
    │      CATHEAD         │ ← Apex, slewing connection
    │   (6-8m truss)       │   Self-weight, wind area, CG
    └──────────────────────┘
           ↓
    ┌──────────────────────┐
    │  SLEWING BEARING     │ ← Transfers vertical + moment
    │   (connects upper   │   to lower (stationary) structure
    │    to lower)        │
    └──────────────────────┘
           ↓
    ┌──────────────────────┐
    │      TOWER/MAST     │ ← Cantilever from foundation
    │   (45-55m vertical) │   SFD, BMD, Stress, Deflection
    │   (cantilever)      │   + Fatigue from slewing
    └──────────────────────┘
           ↓
    ┌──────────────────────┐
    │    FOUNDATION       │ ← Soil bearing check
    │    (pad/raft)       │   Sliding, overturning
    └──────────────────────┘
           ↓
         Ground
```

---

## 2. Key Formulas

### 2.1 Jib Analysis (Cantilever Beam)

**Shear Force:**
```
V(x) = Σ(vertical loads above x)
```

**Bending Moment:**
```
M(x) = Σ(F × distance from x)
```

**Bending Stress:**
```
σ = M × y / I
where:
  M = moment (kN·m)
  y = distance from neutral axis (m)
  I = moment of inertia (m⁴)
```

**Deflection (Euler-Bernoulli):**
```
δ(x) = ∫(M/EI) dx
     = M × x² / (2EI)  (for point load at tip)
```

### 2.2 Counterjib Analysis

Similar to jib, but loads are **static** (counterweights, ballast):
- No moving trolley
- Fixed point loads at defined positions
- Self-weight as UDL

### 2.3 Load Combination

**Important: Sign Convention**

When combining jib and counterjib moments at the cathead:
```
My_net = My_jib - My_counterjib

Example:
  Jib moment:      +10,981 kN·m
  Counterjib:       -5,596 kN·m  (OPPOSITE sign!)
  ─────────────────────────────
  Net at cathead:   5,385 kN·m  (NOT sum!)
```

The counterjib creates an opposite (restoring) moment that reduces the net overturning moment.

### 2.4 Tower/Mast Analysis (Cantilever)

**Cumulative Loads at Height h:**
```
Fz(h) = Σ(weights of all parts above h)
My(h) = Σ(moments from all parts above h)
  Note: Each part has its own sign (+/-)
Fx(h) = Σ(horizontal forces from above)
```

**Stress in Mast Section:**
```
σ_axial = Fz / A           (from vertical load)
σ_bending = M × y / I     (from moment)
σ_total = σ_axial + σ_bending
```

**Deflection (Cantilever with Point Moment):**
```
δ = M × x² / (2EI)
where:
  M = cumulative moment at top
  x = distance from base
  E = Young's modulus (200,000 MPa)
  I = moment of inertia (m⁴)
```

### 2.5 Fatigue Analysis (S-N Curve)

**Stress Range:**
```
Δσ = σ_max - σ_min
```

**Allowable Cycles (Miner's Rule):**
```
log(N) = (log(Δσ) × m - log(a)) / m

where for detail category D (welded steel):
  m = 5 (slope)
  a = 10^17 (intercept)
```

**Damage Ratio:**
```
D = n / N
where:
  n = actual cycles per year
  N = allowable cycles from S-N curve

Safe if D < 1.0
```

### 2.6 Slewing Fatigue

When crane rotates, moment direction changes relative to mast:
- At 0°: jib side sees max moment
- At 180°: counterjib side sees max moment
- This creates stress cycling in all 4 faces

```
Stress range from slewing = σ_max - (-σ_max) = 2 × σ_max
```

---

## 3. Service Conditions

| Condition | Slewing Cycles | Wind Cycles | Moment Factor |
|-----------|----------------|-------------|----------------|
| In Service | 10,000 | 5,000 | 1.0× |
| Working | 20,000 | 10,000 | 1.2× |
| Storm | 1,000 | 500 | 1.5× |
| Survival | 0 | 50 | 2.0× |

---

## 4. Standards Reference

- **ASCE 7-22**: General structural loading
- **Eurocode EN 1990**: Load combinations
- **EN 14439:2025**: Tower crane specific

### EN 14439 Load Factors (H-cases):
- H1: 1.0G + 1.0Q (normal)
- H2: 1.0G + 1.0Q + 0.6W (with wind)
- H4: 1.25Q (test load)

---

## 5. Input Data Structure

### Crane Model
```yaml
crane:
  name: "TC7030-12"
  jib_length: 60.0  # m
  
sections:
  - name: Root
    start: 0.0
    end: 10.0
    area: 0.05  # m²
    moment_of_inertia: 0.015  # m⁴
    yield_strength: 345.0  # MPa
    
point_loads:
  - name: payload
    position: 45.0  # m
    magnitude: 120.0  # kN
```

### Batch Configuration (Multiple Jibs)
```yaml
jibs:
  - name: "TC7030-12 (60m)"
    jib_length: 60.0
    sections: [...]
    point_loads: [...]
```

---

## 6. Output Summary

| Component | Key Output |
|-----------|-------------|
| Jib | SFD, BMD, Stress, Deflection |
| Counterjib | SFD, BMD, Stress, Deflection (static loads) |
| Cathead | Self-weight, wind, structural stress |
| Tower | SFD, BMD, Stress, Deflection, Fatigue |
| Foundation | Soil stress, sliding check |

---

## 7. Quick Reference - Analysis Flow

```
1. INPUT
   └─> YAML file with sections, loads, config

2. MODEL CREATION
   ├─> Jib model (with trolley)
   ├─> Counterjib model (static weights)
   ├─> Cathead model (apex truss)
   └─> Tower model (15-18 sections)

3. ANALYSIS (for each)
   ├─> Compute shear V(x)
   ├─> Compute moment M(x)
   ├─> Compute stress σ(x)
   ├─> Compute deflection δ(x)
   └─> Check utilization

4. LOAD PATH (cumulative)
   ├─> Cathead: Fz, My from jib + counterjib
   ├─> Tower: Fz, My from all above
   └─> Foundation: Total from above

5. OUTPUT
   ├─> HTML Report
   ├─> CSV Export
   └─> JSON API
```

---

## 8. Common Mistakes to Avoid

1. **Sign error**: Counterjib moment subtracts (opposite sign), not adds
2. **Unit conversion**: MPa = N/mm², kN·m × 10⁶ = N·mm
3. **Deflection units**: mm vs m (watch out for 1000×)
4. **Section properties**: I in m⁴ → mm⁴ multiply by 10¹²

---

*For questions or modifications, refer to SOFTWARE_STRUCTURE.md and the source code in `calculations/` and `plotting/` directories.*

*MIT License - claw-agent-3500/crane-horizontal-jib*