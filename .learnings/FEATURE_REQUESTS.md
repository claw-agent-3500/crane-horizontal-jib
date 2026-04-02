# Feature Requests

Missing capabilities or recurring workflow frictions that should become features, scripts, or skills.

**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | promoted

## When to log here

Use this file when the user asks for something the current workflow or tooling cannot yet do well.

Examples:
- a missing export format
- a repeated manual step that should be automated
- a capability gap that keeps surfacing across sessions

## Entry template

```markdown
## [FEAT-YYYYMMDD-XXX] capability-name

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Requested Capability
What the user wanted to do

### Summary
One-line summary of the request

### User Context
Why the capability matters

### Complexity Estimate
simple | medium | complex

### Suggested Implementation
Concrete starting point for building it

### Metadata
- Frequency: first_time | recurring
- Related Features: existing-feature-name

---
```

## [FEAT-20260402-001] deflection-calculation

**Logged**: 2026-04-02T11:27:07Z
**Priority**: high
**Status**: pending
**Area**: backend

### Requested Capability
deflection calculation

### Summary
Compute jib tip deflection and deflection curve along X axis

### User Context
Structural engineers need deflection to verify jib meets serviceability limits (typically L/250 to L/400).

### Complexity Estimate
medium

### Suggested Implementation
Integrate M(x)/EI twice numerically (trapezoidal) to get slope θ(x) and deflection δ(x). Report max deflection and tip deflection. Add deflection plot to HTML report.

### Metadata
- Frequency: recurring

---

## [FEAT-20260402-002] material-properties-and-stress-checks

**Logged**: 2026-04-02T11:27:51Z
**Priority**: medium
**Status**: pending
**Area**: backend

### Requested Capability
material properties and stress checks

### Summary
Add material yield strength to sections and compute utilization ratios

### User Context
Engineers need to know if stress is within allowable limits, not just the raw MPa value.

### Complexity Estimate
simple

### Suggested Implementation
Add optional 'yield_strength' field to sections (default: 345 MPa for Q345 steel). Compute σ/σ_yield ratio per section. Flag sections exceeding 1.0 in the report.

### Metadata
- Frequency: first_time

---
