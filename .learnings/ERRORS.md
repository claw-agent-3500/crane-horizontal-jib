# Errors Log

Non-obvious command failures, tool/API issues, exceptions, and recurring operational problems.

**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | promoted

## When to log here

Use this file when the failure is worth remembering, not for every routine error.

Good candidates:
- required real debugging or investigation
- likely to recur
- revealed an environment or tooling gotcha
- should influence future troubleshooting steps

## Entry template

```markdown
## [ERR-YYYYMMDD-XXX] error-name

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
One-line description of what failed

### Error
```
Raw error message or representative output
```

### Context
What command, tool, API, or workflow was involved

### Suggested Fix
What to try next time or how to prevent recurrence

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file.ext
- See Also: ERR-20260313-001

---
```

## [ERR-20260402-001] trolley-sweep-zero-magnitude

**Logged**: 2026-04-02T11:28:04Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Trolley sweep computed with 0 kN due to empty trolley_loads in base model

### Error
```
Worst trolley position: 3.0 m (should have been near tip at 58m)
```

### Context
In sweep_trolley(), a base_model was created with empty trolley_loads, then compute_sfd_bmd() fell back to model.trolley_loads for magnitude — resulting in 0 kN.

### Suggested Fix
Always pass trolley_mag explicitly when sweeping. Don't rely on model state for load magnitude when overriding position.

### Metadata
- Reproducible: yes
- Related Files: crane_calc.py

---
