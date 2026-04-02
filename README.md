# Tower Crane Jib Calculator 🏗️

Flat-top tower crane jib analysis tool — models the jib as a cantilever beam with varying cross-sections.

## Features

- **Shear Force Diagram (SFD)** — shear distribution along the jib
- **Bending Moment Diagram (BMD)** — moment distribution along the jib
- **Stress Distribution** — bending stress (σ) and shear stress (τ)
- **Trolley Position Sweep** — finds worst-case trolley position
- **HTML Report** — dark-themed report with embedded matplotlib diagrams
- **YAML Input** — define crane geometry, sections, and loads

## Quick Start

```bash
# Run with example crane
python3 crane_calc.py example_crane.yaml

# Custom output path
python3 crane_calc.py my_crane.yaml -o my_report.html

# Don't auto-open browser
python3 crane_calc.py example_crane.yaml --no-browser
```

## Input Format (YAML)

```yaml
crane:
  name: "My Crane"
  jib_length: 60.0

sections:
  - name: "Root Section"
    start: 0.0
    end: 12.0
    weight_per_length: 2.8    # kN/m
    area: 0.085               # m²
    moment_of_inertia: 0.042  # m⁴
    height: 2.6               # m

point_loads:
  - name: "Tip Load"
    position: 60.0
    magnitude: 15.0           # kN

trolley_loads:
  - name: "Trolley + Payload"
    position: 20.0
    trolley_weight: 8.0       # kN
    payload_weight: 120.0     # kN

trolley_sweep:
  enabled: true
  min_position: 3.0
  max_position: 58.0
  step: 1.0
```

## Dependencies

- Python 3.10+
- `matplotlib`
- `pyyaml`
- `numpy`

```bash
pip install matplotlib pyyaml numpy
```

## Model Assumptions

- **Cantilever**: root (fixed) at x=0, free tip at x=L
- **Euler-Bernoulli** beam theory
- Sections are prismatic within each segment
- Effective cross-section properties (A, I, height) per section
- Simplified shear stress (average: τ = V/A)
- Sign convention: positive shear = downward loads to the right; positive moment = hogging

## Output

HTML report with:
- Summary (reactions, max shear/moment/stress)
- Jib configuration schematic
- Section and load tables
- SFD, BMD, and stress diagrams
- Trolley sweep results (if enabled)

## Roadmap

- [ ] Truss member force extraction
- [ ] Deflection calculation
- [ ] Multiple load cases (erection, storm)
- [ ] Stress ratio / utilization checks against material limits
- [ ] PDF export
- [ ] Web UI
