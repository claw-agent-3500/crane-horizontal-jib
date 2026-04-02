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
