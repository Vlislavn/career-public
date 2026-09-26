"""Canonical data validation (§12.1).  All checks deterministic."""
from __future__ import annotations
from .load import load_experiences, load_profile, all_facts
from .models import ValidationResult

def validate(staging: bool = False) -> list[ValidationResult]:
    """Run all §12.1 checks on canonical (or staged) data."""
    results: list[ValidationResult] = []

    # 1. Pydantic schema violations (caught at load — if we get here, OK)
    try:
        profile = load_profile()
    except Exception as e:
        results.append(ValidationResult(level="ERROR", message=f"profile: {e}"))
        return results  # can't continue without profile
    try:
        exps = load_experiences(staging=staging)
    except Exception as e:
        results.append(ValidationResult(level="ERROR", message=f"experience: {e}"))
        return results

    # 2. duplicate experience IDs
    seen_exp: set[str] = set()
    for e in exps:
        if e.id in seen_exp:
            results.append(ValidationResult(
                level="ERROR", message=f"duplicate experience id: {e.id}"))
        seen_exp.add(e.id)

    # 3. duplicate fact IDs across experiences (models check within an experience)
    seen_facts: set[str] = set()
    for e in exps:
        for f in e.facts:
            if f.id in seen_facts:
                results.append(ValidationResult(
                    level="ERROR", message=f"duplicate fact id: {f.id}"))
            seen_facts.add(f.id)

    # 4. education ID uniqueness
    edu_ids: set[str] = set()
    for edu in profile.education:
        if edu.id in edu_ids:
            results.append(ValidationResult(
                level="ERROR", message=f"duplicate education id: {edu.id}"))
        edu_ids.add(edu.id)

    # 5. staging collision check
    if staging:
        _validate_staging_collisions(results)
    return results

def _validate_staging_collisions(results: list[ValidationResult]) -> None:
    """Staged fact IDs must not collide with existing canonical IDs."""
    canonical = set(all_facts(staging=False).keys())
    staged = all_facts(staging=True)
    for fid in staged:
        if fid in canonical:
            results.append(ValidationResult(
                level="ERROR",
                message=f"staging collision: fact id '{fid}' already exists in canonical data"))
