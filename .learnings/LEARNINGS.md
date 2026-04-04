# Learnings Log

Corrections, knowledge gaps, best practices, and durable project conventions.

**Categories**: correction | knowledge_gap | best_practice | insight
**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## When to log here

Use this file when a lesson should change future behaviour.

Examples:
- the user corrected a wrong assumption
- a project convention was discovered
- a workaround or prevention rule emerged from debugging
- a better workflow or tool usage pattern was identified

## Entry template

```markdown
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
One-line summary of the learning

### Details
What happened, what was wrong or surprising, and what is now known to be true

### Suggested Action
Specific prevention rule, fix, or workflow change

### Metadata
- Source: conversation | error | user_feedback | docs | simplify-and-harden
- Related Files: path/to/file.ext
- Tags: tag1, tag2
- See Also: LRN-20260313-001
- Pattern-Key: stable.pattern.key
- Recurrence-Count: 1
- First-Seen: 2026-03-13
- Last-Seen: 2026-03-13

---
```

## Promotion fields

When the learning becomes durable project memory:

```markdown
**Status**: promoted
**Promoted**: CLAUDE.md
```

When it becomes a reusable skill:

```markdown
**Status**: promoted_to_skill
**Skill-Path**: skills/skill-name
```

## [LRN-20260402-001] best_practice

**Logged**: 2026-04-02T11:26:36Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Trolley sweep removed in v0.2.0 — was a valuable feature for worst-case analysis

### Details
When rebuilding crane_calc.py with new constraints (5PL+5UDL, XYZ coords), the trolley position sweep feature was dropped. This was useful for finding the worst-case trolley position and max root moment across all positions. Should be restored as an opt-in analysis mode.

### Suggested Action
Restore trolley sweep as an optional analysis feature. Keep the 1-load-case constraint for the primary output, but allow sweep as a secondary analysis mode.

### Metadata
- Source: conversation
- Related Files: crane_calc.py
- Tags: regression, feature-loss

---

## [LRN-20260402-002] insight

**Logged**: 2026-04-02T11:29:02Z
**Priority**: medium
**Status**: pending
**Area**: backend

### Summary
When rebuilding with new constraints, validate which existing features survive

### Details
v0.2.0 rebuilt crane_calc.py from scratch to support new constraints. The trolley sweep feature was accidentally dropped. Before rebuilding, audit existing features and explicitly decide: keep, modify, or remove. Don't assume new code preserves old capabilities.

### Suggested Action
Before any rebuild, list existing features and mark each as keep/modify/remove. Cross-check after rebuild.

### Metadata
- Source: conversation
- Tags: rebuild, regression-prevention

---

## [LRN-20260402-003] best_practice

**Logged**: 2026-04-02T11:54:57Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Trolley sweep restored with trolley_mag parameter fix

### Details
Restored trolley sweep as optional analysis mode. Fixed root cause (ERR-20260402-001) by passing trolley_mag explicitly. Now produces worst-case moment, shear, and deflection across trolley positions.

### Suggested Action
Keep sweep as opt-in secondary analysis. Primary output stays 1 load case.

### Metadata
- Source: conversation
- Tags: trolley-sweep, restored
- See Also: ERR-20260402-001, LRN-20260402-001

---

## [LRN-20260402-004] best_practice

**Logged**: 2026-04-02T11:54:57Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Deflection via double integration of M/(EI)

### Details
Added deflection calculation using cumulative trapezoidal integration. θ(x) = ∫M/(EI)dx, δ(x) = ∫θ(x)dx with θ(0)=0, δ(0)=0. Added L/250 serviceability check and deflection plot to report.

### Suggested Action
Always include deflection in structural reports. Check against L/250 and L/400 limits.

### Metadata
- Source: conversation
- Tags: deflection, serviceability
- See Also: FEAT-20260402-001

---

## [LRN-20260402-005] best_practice

**Logged**: 2026-04-02T13:03:57Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Modular architecture for expandable calculations

### Details
Restructured monolithic crane_calc.py into modular package: models.py (data), calculations/ (beam, deflection, stress, truss), plotting/ (7 plot modules), report.py (HTML), loader.py (YAML), validation.py, crane_calc.py (CLI). New calculations just add a file in calculations/ and a corresponding plot in plotting/.

### Suggested Action
Follow the pipeline pattern: each calc module takes (model, x, ...) and returns a dict. Each plot module takes a result and returns base64 PNG. Wire them in run_analysis() and report.py.

### Metadata
- Source: conversation
- Tags: architecture, modular, refactor

---

## [LRN-20260402-006] insight

**Logged**: 2026-04-02T16:19:33Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Used self-improvement loop to improve the tool itself

### Details
Following LRN-20260402-002 (audit features before rebuild), applied self-improvement feedback to evolve crane-jib-calc: added deflection (from FEAT), trolley sweep (restored from LRN), modular architecture (LRN), load cases with coefficients (from user requirements), and wind loads with wind_area/wind_pressure. Each iteration logged, pushed to repo, creating a feedback loop where the tool improves itself.

### Suggested Action
For future projects: start self-improvement loop early, log every feature decision, apply learnings to next iteration. The loop compounds.

### Metadata
- Source: conversation
- Tags: self_improvement, feedback_loop, iterative_development
- See Also: LRN-20260402-002, FEAT-20260402-001, LRN-20260402-003, LRN-20260402-004

---

## [LRN-20260404-001] insight

**Logged**: 2026-04-04T13:31:00Z
**Priority**: medium
**Status**: pending
**Area**: docs

### Summary
Report HTML is comprehensive but lacks PDF export

### Details
Design engineers often need PDF for formal submissions. Current HTML-only output requires printing to PDF via browser.

### Suggested Action
Add PDF export using reportlab or matplotlib backend. Keep HTML as primary, add --pdf flag.

### Metadata
- Source: conversation
- Tags: pdf, export, reporting

---

## [LRN-20260404-002] correction

**Logged**: 2026-04-04T14:30:00Z
**Priority**: critical
**Status**: pending
**Area**: backend

### Summary
Confusing sign convention in chord forces - positive M gives positive (compression) on upper but lower should be tension

### Details
Current: upper = M/(h*uc), lower = -M/(h*lc). For positive M (hogging at root), upper is in compression (correct), lower is in tension (correct). But signs in output table were confusing - need clearer labels.

### Suggested Action
[TODO: add suggested action]

### Metadata
- Source: conversation
- Tags: sign-convention, chord-forces, correction

---

## [LRN-20260404-003] best_practice

**Logged**: 2026-04-04T14:30:11Z
**Priority**: medium
**Status**: pending
**Area**: backend

### Summary
Wind loads should be marked distinct from gravity loads in report

### Details
Wind is horizontal, gravity is vertical. Should visually distinguish wind contribution in SFD/BMD or add separate wind diagram.

### Suggested Action
[TODO: add suggested action]

### Metadata
- Source: conversation
- Tags: wind, visualization

---
