# Crane Jib Calculator - Software Architecture

## Overview

Flat top tower crane jib structural analysis with SFD, BMD, deflection, stress, and truss member forces.

## Project Structure

```
crane-jib-calc/
├── crane_calc.py          # Main entry point (CLI)
├── loader.py              # YAML input parser
├── models.py              # Data classes
├── validation.py          # Input validation
├── report.py              # HTML report generator
│
├── calculations/          # Physics modules
│   ├── beam.py           # Shear & moment
│   ├── deflection.py     # Displacement & rotation
│   ├── stress.py         # Bending & shear stress
│   ├── truss.py          # Truss member forces
│   ├── buckling.py       # Global buckling (Euler)
│   ├── torsion.py        # Torsional analysis
│   └── fatigue.py        # Fatigue (S-N curve)
│
├── plotting/             # Visualization modules
│   ├── sfd.py           # Shear Force Diagram
│   ├── bmd.py           # Bending Moment Diagram
│   ├── deflection_plot.py
│   ├── stress_plot.py
│   ├── chord_plot.py
│   ├── diagonal_plot.py
│   ├── wind_plot.py
│   ├── utilization_plot.py
│   ├── sweep.py         # Trolley sweep envelope
│   ├── schematic.py     # Jib schematic
│   └── plot_3d.py       # 3D visualization
│
├── load_case_io.py       # Save/load load cases
├── load_case_summary.py  # Per-case summary table
├── wind_analysis.py     # Wind load computation
├── seismic_analysis.py  # Seismic loads (ASCE 7)
├── unit_conversion.py   # SI ↔ Imperial
├── load_combinations.py # ASCE/Eurocode combos
│
├── examples/            # Example inputs
│   └── working_60m/
│       └── input.yaml
│
├── tests/               # Test suite
│   └── test_suite.py    # 17 tests
│
└── PENDING_FEATURES.md  # Feature backlog
```

## Features

### Core Analysis
| Feature | Module | Description |
|---------|--------|-------------|
| Shear Force | `beam.py` | V(x) along jib |
| Bending Moment | `beam.py` | M(x) along jib |
| Deflection | `deflection.py` | δ(x), θ(x) using Euler-Bernoulli |
| Bending Stress | `stress.py` | σ = M*y/I |
| Shear Stress | `stress.py` | τ = VQ/It |
| Truss Forces | `truss.py` | Upper/lower chord, diagonals |

### Advanced Analysis
| Feature | Module | Description |
|---------|--------|-------------|
| Global Buckling | `buckling.py` | Euler formula, K=0.7 |
| Torsion | `torsion.py` | Eccentric loads |
| Fatigue | `fatigue.py` | S-N curve, Miner's rule |
| Seismic | `seismic_analysis.py` | ASCE 7-22 spectral method |
| Load Combinations | `load_combinations.py` | ASCE 7-22, Eurocode EN 1990 |

### Visualization
| Plot | File | Description |
|------|------|-------------|
| SFD | `sfd.py` | Shear force diagram |
| BMD | `bmd.py` | Bending moment diagram |
| Deflection | `deflection_plot.py` | Displacement curve |
| Stress | `stress_plot.py` | Stress distribution |
| Chord Forces | `chord_plot.py` | Upper/lower chord |
| Diagonal Forces | `diagonal_plot.py` | Compression/tension |
| Wind | `wind_plot.py` | Wind pressure diagram |
| Utilization | `utilization_plot.py` | σ/f_y ratio |
| Trolley Sweep | `sweep.py` | Envelope of all positions |
| 3D Schematic | `plot_3d.py` | 3D truss visualization |

### Input/Output
| Feature | File | Description |
|---------|------|-------------|
| YAML Input | `loader.py` | Parse crane model from YAML |
| HTML Report | `report.py` | Full analysis report |
| CSV Export | - | Sections, loads, results, forces |
| Load Case I/O | `load_case_io.py` | Save/load load case sets |
| Unit Conversion | `unit_conversion.py` | SI ↔ Imperial |

## Data Models (models.py)

```python
CraneModel
├── name: str
├── jib_length: float
├── jib_height_position: float
├── sections: list[Section]
├── point_loads: list[PointLoad]  # max 5
├── udls: list[UDL]               # max 5
├── trolley: Trolley
├── load_cases: list[LoadCase]
└── report_config: ReportConfig

Section
├── name: str
├── start, end: float (m)
├── weight_per_length: float (kN/m)
├── area: float (m²)
├── moment_of_inertia: float (m⁴)
├── height: float (m)
├── yield_strength: float (MPa)  # default 345
└── truss: TrussConfig

LoadCase
├── name: str
├── coefficients: dict  # {load_name: factor}
├── wind_pressure: float (Pa)
└── description: str
```

## CLI Usage

```bash
python3 crane_calc.py input.yaml -o report.html

# Options:
#   --save-lc FILE      Save load cases to YAML
#   --load-lc FILE     Load additional load cases
#   --units SI|Imperial
#   --no-browser       Don't open browser
```

## Input Format (YAML)

```yaml
crane:
  name: "TC7030-12"
  jib_length: 60.0
  jib_height_position: 0.0
  youngs_modulus: 200000.0  # MPa

sections:
  - name: Root
    start: 0.0
    end: 10.0
    weight_per_length: 2.5
    area: 0.05
    moment_of_inertia: 0.015
    height: 1.8
    yield_strength: 345.0

point_loads:
  - name: payload
    position: 45.0
    magnitude: 120.0

udls:
  - name: deck
    start: 0.0
    end: 60.0
    magnitude: 0.5

trolley:
  magnitude: 80.0
  min_position: 5.0
  max_position: 55.0

load_cases:
  - name: Working
    coefficients:
      self_weight: 1.0
      payload: 1.0
    wind_pressure: 250.0  # Pa
```

## Test Suite

```bash
python3 tests/test_suite.py
```

**17 Tests:**
1. Basic Analysis
2. HTML Report Generation
3. CSV Export
4. Save/Load Load Cases
5. Minimal Input
6. Serviceability Limits
7. Input Validation
8. Truss Cross-Section Types
9. Wind Analysis
10. Per-Section Forces
11. Report Configuration
12. Global Buckling
13. Torsion Analysis
14. Fatigue Analysis
15. Load Combinations
16. Seismic Analysis
17. 3D Visualization

## Constraints

- Max 5 point loads + 5 UDLs
- XYZ: X=longitudinal, Y=vertical (+up), Z=width
- Loads act in -Y (downward)
- snake_case throughout
- yield_strength default: 345 MPa (Q345 steel)
- serviceability_limit: 'L/250', 'L/400', or custom

## Example Output (60m jib)

- Max root moment: **10,981 kN·m**
- Max shear: **263 kN**
- Max stress: **340 MPa**
- Max utilization: **98.5%**
- Tip deflection: 2,041 mm (exceeds L/250)

## Version History

- v0.3.0 - Deflection + trolley sweep
- v0.4.0 - Modular architecture
- v0.5.0 - Load cases with coefficients
- v0.6.0 - Wind loads
- v0.7.0 - CG coordinates
- v0.8.0 - Per-section forces at start
- v0.9.0 - Material utilization
- v0.10.0 - CSV export
- v0.11.0 - Per-load-case summary
- v0.12.0 - Save/load load cases + wind diagram
- v0.13.0 - Unit conversion + global buckling

## License

Internal project - claw-agent-3500/crane-horizontal-jib