"""Model validation."""

from models import CraneModel, MAX_POINT_LOADS, MAX_UDLS


def validate_model(model: CraneModel) -> list[str]:
    """Validate model constraints and return list of errors."""
    errors = []

    if len(model.point_loads) > MAX_POINT_LOADS:
        errors.append(f"Too many point loads: {len(model.point_loads)} (max {MAX_POINT_LOADS})")
    if len(model.udls) > MAX_UDLS:
        errors.append(f"Too many UDLs: {len(model.udls)} (max {MAX_UDLS})")

    sorted_secs = sorted(model.sections, key=lambda s: s.start)
    if sorted_secs[0].start != 0:
        errors.append(f"First section starts at {sorted_secs[0].start}, must be 0")
    if sorted_secs[-1].end != model.jib_length:
        errors.append(f"Last section ends at {sorted_secs[-1].end}, must be {model.jib_length}")

    for i in range(len(sorted_secs) - 1):
        gap = sorted_secs[i + 1].start - sorted_secs[i].end
        if abs(gap) > 1e-6:
            errors.append(f"Gap between sections at X={sorted_secs[i].end:.1f} to {sorted_secs[i+1].start:.1f}")

    for pl in model.point_loads:
        if pl.position < 0 or pl.position > model.jib_length:
            errors.append(f"Point load '{pl.name}' at X={pl.position} outside jib [0, {model.jib_length}]")

    for udl in model.udls:
        if udl.start < 0 or udl.end > model.jib_length:
            errors.append(f"UDL '{udl.name}' [{udl.start}, {udl.end}] outside jib [0, {model.jib_length}]")
        if udl.start >= udl.end:
            errors.append(f"UDL '{udl.name}' has start >= end")

    if model.youngs_modulus <= 0:
        errors.append(f"Young's modulus must be positive, got {model.youngs_modulus}")

    for sec in model.sections:
        if sec.truss:
            tr = sec.truss
            if tr.upper_chords not in (1, 2):
                errors.append(f"Section '{sec.name}': upper_chords must be 1 or 2, got {tr.upper_chords}")
            if tr.lower_chords not in (1, 2):
                errors.append(f"Section '{sec.name}': lower_chords must be 1 or 2, got {tr.lower_chords}")

    return errors
