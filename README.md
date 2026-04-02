# Crane Jib Calculator

Flat-top tower crane jib analysis tool — computes shear force, bending moment, deflection, stress, and truss member forces along the jib.

## What It Does

**Analysis:**
- Shear Force Diagram (SFD) — V(x) along the jib
- Bending Moment Diagram (BMD) — M(x) along the jib
- Deflection curve — δ(x) with L/250 serviceability check
- Stress distribution — bending stress σ and shear stress τ
- Truss member forces — upper/lower chords and diagonals (comp/tens/neutral)
- Per-section forces at section start (for design pivot points)

**Features:**
- Multiple load cases with coefficient multipliers (`coef_` prefix)
- Wind loads via `wind_area` on elements and `wind_pressure` on load cases
- Trolley envelope across travel range [min_position, max_position]
- Modular architecture — easy to add new calculation modules

## Coordinate System

```
X = longitudinal along jib (root at X=0, tip at X=jib_length)
Y = vertical (positive up, gravity in −Y direction)
Z = width (perpendicular to bending plane)
```

## Input Format (YAML)

### Minimal Example

```yaml
crane:
  name: "My Crane"
  jib_length: 60.0
  youngs_modulus: 200000000.0  # kN/m² (200 GPa)

sections:
  - name: "Root"
    start: 0.0
    end: 12.0
    weight_per_length: 2.8   # kN/m
    area: 0.085              # m²
    moment_of_inertia: 0.042 # m⁴
    height: 2.6              # m

point_loads:
  - name: "Tip Load"
    position: 60.0
    magnitude: 15.0

trolley:
  magnitude: 128.0
  min_position: 3.0
  max_position: 58.0

load_cases:
  - name: "Working"
    coef_self_weight: 1.0
    coef_tip_load: 1.0
    coef_trolley: 1.0
    wind_pressure: 250  # Pa
```

### Full Example with Truss

```yaml
crane:
  name: "TC7030-12 Example"
  jib_length: 60.0
  jib_height_position: 45.0  # Y coord of jib reference
  youngs_modulus: 200000000.0

sections:
  - name: "Root Section"
    start: 0.0
    end: 12.0
    weight_per_length: 2.8
    area: 0.085
    moment_of_inertia: 0.042
    height: 2.6
    wind_area: 8.5      # m² for wind
    cg_x: 6.0           # center of gravity
    cg_y: 45.0
    cg_z: 0.0
    truss:
      upper_chords: 2   # 1 or 2
      lower_chords: 2   # 1 or 2
      compression_diagonal: { angle: 45, present: true }
      tension_diagonal: { angle: 45, present: true }

point_loads:
  - name: "Tip Sheave + Hoist"
    position: 60.0
    magnitude: 15.0
    wind_area: 1.5

trolley:
  magnitude: 128.0
  min_position: 3.0
  max_position: 58.0
  step: 1.0
  wind_area: 3.0

load_cases:
  - name: "In Service (Working)"
    wind_pressure: 250   # Pa
    coef_self_weight: 1.0
    coef_tip_sheave_hoist: 1.0
    coef_trolley: 1.0

  - name: "Out of Service (Storm)"
    wind_pressure: 1100  # Pa
    coef_self_weight: 1.0
    coef_tip_sheave_hoist: 1.0
    coef_trolley: 0.0

  - name: "Erection"
    wind_pressure: 0
    coef_self_weight: 1.2
```

## Usage

```bash
# Run analysis
python3 crane_calc.py input.yaml -o report.html

# Skip browser open
python3 crane_calc.py input.yaml -o report.html --no-browser
```

## Output

HTML report with:
- Summary stats (max V, M, σ, tip deflection)
- Jib configuration schematic
- Applied loads table
- SFD, BMD, deflection, stress diagrams
- Chord and diagonal force diagrams
- Forces at section start table (for design pivot points)

## Project Structure

```
crane-jib-calc/
├── crane_calc.py      # CLI entry point
├── models.py          # Data classes
├── loader.py          # YAML parser
├── validation.py      # Input validation
├── report.py          # HTML generator
├── calculations/      # Analysis modules
│   ├── beam.py       # V(x), M(x)
│   ├── deflection.py # θ(x), δ(x)
│   ├── stress.py     # σ, τ
│   └── truss.py      # chord & diagonal forces
├── plotting/          # Plot modules
│   ├── sfd.py, bmd.py, deflection_plot.py, ...
├── examples/          # Example inputs/outputs
└── .learnings/        # Self-improvement log
```

## Load Case Coefficients

Each load gets multiplied by its coefficient:
- `coef_self_weight` — section self-weight
- `coef_<load_name>` — point load (spaces → underscores)
- `coef_<udl_name>` — distributed load
- `coef_trolley` — trolley load

Missing coefficients default to 1.0.

## Wind

Wind force = `pressure * area / 1000` → kN

- **In service**: typically 250 Pa
- **Out of service (storm)**: typically 1100 Pa

## Truss Cross-Sections

| upper_chords | lower_chords | Shape |
|--------------|---------------|-------|
| 1 | 2 | ▽ Triangle (apex up) |
| 2 | 1 | △ Inverted triangle |
| 2 | 2 | ▭ Rectangular (box) |

## Self-Improvement Loop

This project uses the `actual-self-improvement` skill to learn from each iteration:

```bash
# Log a learning
python3 ../skills/actual-self-improvement/scripts/learnings.py log-learning \
  --root . --category insight --priority high --summary "..."

# Log an error
python3 ../skills/actual-self-improvement/scripts/learnings.py log-error \
  --root . --name bug-name --summary "..."

# Log a feature request
python3 ../skills/actual-self-improvement/scripts/learnings.py log-feature \
  --root . --capability name --summary "..."
```

See `.learnings/` directory for history.

## Requirements

- Python 3.10+
- numpy
- matplotlib
- pyyaml

```bash
pip install numpy matplotlib pyyaml
```

## License

MIT
