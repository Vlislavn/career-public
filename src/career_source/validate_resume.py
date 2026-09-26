"""Resume spec validation (§12.2): provenance, numbers, entities."""
from __future__ import annotations
import re
from pathlib import Path
import yaml
from .load import load_experiences, load_profile, all_facts, fact_to_experience
from .models import ResumeSpec, ValidationResult, number_claims, number_errors
from .normalize import normalize, _reverse_map

def validate_resume(spec_path: str | Path) -> list[ValidationResult]:
    """Run all §12.2 checks on a resume selection spec."""
    results: list[ValidationResult] = []
    path = Path(spec_path)
    if not path.exists():
        return [ValidationResult(level="ERROR", message=f"file not found: {path}")]
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    # 1. schema validation
    try:
        spec = ResumeSpec(**raw)
    except Exception as e:
        return [ValidationResult(level="ERROR", message=f"schema: {e}")]
    fact_map = all_facts()
    f2e = fact_to_experience()
    exps = {e.id: e for e in load_experiences()}
    edu_ids = {e.id for e in load_profile().education}

    # 2. unknown experience_id / education_id
    for we in spec.sections.work:
        if we.experience_id not in exps:
            results.append(ValidationResult(
                level="ERROR",
                message=f"unknown experience_id: {we.experience_id}"))
        elif we.title is not None and we.title != exps[we.experience_id].title:
            results.append(ValidationResult(level="ERROR", message=f"work/{we.experience_id}: title must match canonical title"))
    for edu in spec.sections.education:
        if edu.education_id not in edu_ids:
            results.append(ValidationResult(
                level="ERROR",
                message=f"unknown education_id: {edu.education_id}"))

    # 3. unknown fact_id in publications
    for pub in spec.sections.publications:
        if pub.fact_id not in fact_map:
            results.append(ValidationResult(
                level="ERROR",
                message=f"unknown publication fact_id: {pub.fact_id}"))

    # 4. per-bullet checks
    for we in spec.sections.work:
        exp_id = we.experience_id
        for i, bullet in enumerate(we.bullets):
            _check_bullet(bullet, exp_id, fact_map, f2e, results, f"work/{exp_id}[{i}]")
    for proj in spec.sections.projects:
        for i, bullet in enumerate(proj.bullets):
            _check_bullet(bullet, None, fact_map, f2e, results,
                          f"projects/{proj.name}[{i}]", project_mode=True)

    # 5. advisory: skills section
    _check_skills(spec, fact_map, results)
    return results

def _check_bullet(
    bullet, exp_id, fact_map, f2e, results, label, project_mode=False,
) -> None:
    """Check a single bullet's provenance, numbers, and entities."""
    refs = bullet.source_fact_ids

    # unknown fact_id
    for fid in refs:
        if fid not in fact_map:
            results.append(ValidationResult(
                level="ERROR",
                message=f"{label}: unknown source_fact_id: {fid}"))
            return

    # fact from unrelated experience
    if exp_id and not project_mode:
        for fid in refs:
            if f2e.get(fid) != exp_id:
                results.append(ValidationResult(
                    level="ERROR",
                    message=f"{label}: fact {fid} belongs to '{f2e.get(fid)}', not '{exp_id}'"))
    text = bullet.text
    if not text:
        return  # Mode B — no text to check
    referenced_facts = [fact_map[fid] for fid in refs if fid in fact_map]
    # metric survival: every metric value from source facts must appear in text
    _check_metric_survival(text, referenced_facts, label, results)

    # number provenance (§12.2)
    _check_numbers(text, referenced_facts, label, results)

    # entity presence (§12.2)
    _check_entities(text, referenced_facts, label, results)

def _check_metric_survival(text, facts, label, results) -> None:
    """Every metric value from source facts must appear in polished text."""
    values = {v for v, unit in number_claims(text)}
    for f in facts:
        for m in f.metrics:
            if m.value not in values:
                results.append(ValidationResult(level="ERROR",
                    message=f"{label}: metric '{m.value}{m.unit}' from {f.id} not found in text"))

def _check_numbers(text, facts, label, results) -> None:
    results.extend(ValidationResult(level="ERROR", message=f"{label}: {message}")
                   for message in number_errors(text, [m for f in facts for m in f.metrics]))
def _check_entities(text, facts, label, results) -> None:
    """Tokens resolving to known tools/skills must be in referenced facts."""
    ref: set[str] = set()
    for f in facts:
        ref.update(normalize(s) for s in f.skills + f.tools)
        fl = f.text.lower()
        ref.update(c for a, c in _reverse_map().items()
                   if len(a) >= 3 and re.search(rf"\b{re.escape(a)}\b", fl))
    tl = text.lower()
    flagged: set[str] = set()
    for a, c in _reverse_map().items():
        if len(a) >= 3 and re.search(rf"\b{re.escape(a)}\b", tl) and c not in ref and c not in flagged:
            results.append(ValidationResult(level="ERROR",
                message=f"{label}: entity '{c}' in text but not in referenced facts' skills/tools"))
            flagged.add(c)
    # also check canonical names (catches short forms like "Go" len=2)
    for c in set(_reverse_map().values()):
        cl = c.lower()
        if len(cl) >= 2 and re.search(rf"\b{re.escape(cl)}\b", tl) and c not in ref and c not in flagged:
            results.append(ValidationResult(level="ERROR",
                message=f"{label}: entity '{c}' in text but not in referenced facts' skills/tools"))
            flagged.add(c)

def _check_skills(spec, fact_map, results) -> None:
    """Advisory WARN for skills not in selected facts, with candidate suggestions."""
    refs = spec.sections.fact_ids()
    sel = [fact_map[fid] for fid in refs if fid in fact_map]
    fskills = {normalize(x) for f in sel for x in f.skills + f.tools}
    listed = spec.sections.skills + [s for values in spec.sections.skill_groups.values() for s in values]
    for s in listed:
        if normalize(s) not in fskills:
            cands = [fid for fid, f in fact_map.items()
                     if normalize(s) in {normalize(x) for x in f.skills + f.tools}]
            hint = f" (found in: {', '.join(cands[:5])})" if cands else ""
            results.append(ValidationResult(level="WARN",
                message=f"skills section: '{s}' not found in any selected fact's skills/tools{hint}"))
