# Crane Jib Calculator

Structural analysis for flat top tower cranes.

## Features

### Structural Components
- **Jib** - Main lifting arm with trolley
- **Counterjib** - Counterweight arm (static loads)
- **Cathead** - Apex/slewing assembly
- **Mast/Tower** - Vertical structure (cantilever)
- **Foundation** - Soil bearing check

### Analysis
- Shear Force Diagram (SFD)
- Bending Moment Diagram (BMD)
- Deflection calculation
- Stress analysis
- Utilization check
- Buckling analysis
- Fatigue analysis
- Torsion analysis

### Load Standards
- ASCE 7-22
- Eurocode EN 1990
- EN 14439:2021/2025 (Tower Cranes)

### Output
- HTML report with plots
- CSV export
- JSON API format
- Batch analysis for multiple configs

## Usage

```bash
python3 crane_calc.py examples/working_60m/input.yaml -o report.html
```

## Project Structure

```
crane-jib-calc/
├── calculations/     # Physics modules
│   ├── beam.py      # SFD, BMD
│   ├── deflection.py
│   ├── stress.py
│   ├── truss.py
│   ├── buckling.py
│   ├── torsion.py
│   ├── fatigue.py
│   ├── counterjib.py
│   ├── cathead.py
│   └── tower.py
├── plotting/        # Visualization
├── tests/           # Test suite
└── examples/        # Example inputs
```

## Requirements

```
numpy>=1.21
matplotlib>=3.5
PyYAML>=6.0
```

## Tests

```bash
python3 tests/test_suite.py
```

---
MIT - claw-agent-3500/crane-horizontal-jib
