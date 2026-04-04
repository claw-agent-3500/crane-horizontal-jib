# Pending Features - Crane Jib Calculator

## Overview
This document tracks all pending feature requests for the crane-jib-calc project. Features are organized by priority.

---

## Completed Features (Implemented in v0.3.0 - v0.12.0)

| Version | Feature |
|---------|---------|
| v0.3.0 | Deflection calculation |
| v0.3.0 | Trolley envelope |
| v0.4.0 | Modular architecture |
| v0.4.0 | Truss member forces |
| v0.5.0 | Load cases with coefficients |
| v0.6.0 | Wind loads |
| v0.7.0 | CG coordinates |
| v0.8.0 | Per-section forces at start |
| v0.9.0 | Material utilization |
| v0.9.0 | Configurable serviceability limits |
| v0.10.0 | CSV export |
| v0.11.0 | Per-load-case summary table |
| v0.12.0 | Save/load load case sets |
| v0.12.0 | Wind diagram |

---

## Pending Features

### High Priority

| ID | Capability | Description |
|----|------------|-------------|
| FEAT-20260404-009 | Global buckling check | Compute global buckling for the jib |
| FEAT-20260404-012 | Torsion analysis | Torsion from eccentric loads (using CG Z offset) |

### Medium Priority

| ID | Capability | Description |
|----|------------|-------------|
| FEAT-20260404-016 | Load combinations | Automated load combinations per ASCE/Eurocode |
| FEAT-20260404-018 | Section utilization plot | Plot utilization ratio along jib length |
| FEAT-20260404-010 | Fatigue analysis | Fatigue analysis for cyclic loading |
| FEAT-20260404-011 | Seismic loads | Seismic load cases per code |

### Low Priority

| ID | Capability | Description |
|----|------------|-------------|
| FEAT-20260404-014 | 3D visualization | 3D visualization of jib with forces |
| FEAT-20260404-005 | Unit conversion | SI/Imperial toggle |
| FEAT-20260404-015 | Member optimization | Suggest optimal section sizes based on utilization |
| FEAT-20260404-007 | Multiple jib comparison | Compare results across multiple jib configurations |
| FEAT-20260404-017 | Reaction forces export | Export reaction forces for structural analysis |

---

## Feature Details

### Global Buckling Check (FEAT-20260404-009)
- **Priority**: High
- **Summary**: Compute global buckling for jib using Euler's formula
- **Suggested Implementation**: Use effective length factor K=2.0 for cantilever. Compute Pcr = π²EI/(KL)² and compare with actual loads.

### Torsion Analysis (FEAT-20260404-012)
- **Priority**: High  
- **Summary**: Torsion from eccentric loads (using CG Z offset)
- **Suggested Implementation**: Already have CG coordinates. Compute torsional moment = sum(P × e_z) where e_z is offset from shear center.

### Load Combinations (FEAT-20260404-016)
- **Priority**: Medium
- **Summary**: Automated load combinations per ASCE/Eurocode
- **Suggested Implementation**: Pre-define common combinations (1.4D, 1.2D+1.6L, etc.) and apply them automatically.

### Section Utilization Plot (FEAT-20260404-018)
- **Priority**: Medium
- **Summary**: Plot utilization ratio (σ/f_y) along jib length
- **Suggested Implementation**: Similar to stress plot, but show utilization ratio with limit lines at 0.7, 0.9, 1.0.

### Fatigue Analysis (FEAT-20260404-010)
- **Priority**: Medium
- **Summary**: Fatigue analysis for cyclic loading based on stress range
- **Suggested Implementation**: Use S-N curves. Compute Δσ and check against allowable cycles.

### Seismic Loads (FEAT-20260404-011)
- **Priority**: Medium
- **Summary**: Seismic load cases per code (ASCE 7, Eurocode 8)
- **Suggested Implementation**: Add seismic load case type with base shear calculation.

### 3D Visualization (FEAT-20260404-014)
- **Priority**: Low
- **Summary**: 3D visualization of jib with color-coded forces
- **Suggested Implementation**: Use matplotlib 3D or Plotly for interactive 3D view.

### Unit Conversion (FEAT-20260404-005)
- **Priority**: Low
- **Summary**: Unit conversion (SI/Imperial toggle)
- **Suggested Implementation**: Add `--units SI|Imperial` flag. Convert all outputs.

### Member Optimization (FEAT-20260404-015)
- **Priority**: Low
- **Summary**: Suggest optimal section sizes based on utilization
- **Suggested Implementation**: Iteratively adjust section properties to meet utilization targets.

### Multiple Jib Comparison (FEAT-20260404-007)
- **Priority**: Low
- **Summary**: Compare results across multiple jib configurations
- **Suggested Implementation**: Accept multiple YAML files, compute each, produce comparison table.

### Reaction Forces Export (FEAT-20260404-017)
- **Priority**: Low
- **Summary**: Export reaction forces for structural analysis
- **Suggested Implementation**: Add to CSV export or create separate reactions.json.

---

## Usage Notes

To implement any pending feature:
1. Select a feature from the list
2. Create a new calculation module in `calculations/`
3. Add corresponding plot in `plotting/`
4. Add to report generation
5. Update version and commit

---

## License
MIT
