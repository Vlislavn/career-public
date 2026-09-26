"""Loaders for canonical career data (§3, §17)."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml
from .models import Experience, Profile, Basics, EducationEntry, Fact
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}
def load_profile() -> Profile:
    """Load basics + education from data/profile/."""
    pdir = DATA_DIR / "profile"
    basics = Basics(**_load_yaml(pdir / "basics.yaml"))
    edu_raw = _load_yaml(pdir / "education.yaml")
    education = [EducationEntry(**e) for e in (edu_raw.get("entries") or edu_raw)]
    return Profile(basics=basics, education=education)
def load_experiences(staging: bool = False) -> list[Experience]:
    """Load all experience files from data/experience/ (or .staging/)."""
    directory = DATA_DIR / ".staging" if staging else DATA_DIR / "experience"
    if not directory.exists():
        return []
    exps: list[Experience] = []
    for p in sorted(directory.glob("*.yaml")):
        raw = _load_yaml(p)
        exps.append(Experience(**raw))
    return exps
def load_facts(staging: bool = False) -> dict[str, list[Fact]]:
    """Return {experience_id: [facts]} for all experiences."""
    return {e.id: e.facts for e in load_experiences(staging=staging)}
def all_facts(staging: bool = False) -> dict[str, Fact]:
    """Return {fact_id: Fact} across all experiences."""
    out: dict[str, Fact] = {}
    for e in load_experiences(staging=staging):
        for f in e.facts:
            out[f.id] = f
    return out
def fact_to_experience(staging: bool = False) -> dict[str, str]:
    """Return {fact_id: experience_id} mapping."""
    out: dict[str, str] = {}
    for e in load_experiences(staging=staging):
        for f in e.facts:
            out[f.id] = e.id
    return out
def export_context(
    skill: Optional[str] = None,
    experience: Optional[str] = None,
    staging: bool = False,
) -> dict:
    """Export a compact machine bundle (§15) with schema_version."""
    from .normalize import normalize
    profile = load_profile()
    exps = load_experiences(staging=staging)
    exp_data: list[dict] = []
    fact_data: list[dict] = []
    for e in exps:
        if experience and e.id != experience:
            continue
        facts_out: list[dict] = []
        for f in e.facts:
            if skill:
                fskills = {normalize(s) for s in f.skills}
                ftools = {normalize(t) for t in f.tools}
                if normalize(skill) not in fskills | ftools:
                    continue
            fd = f.model_dump()
            fd["experience_id"] = e.id  # tag for consumers
            facts_out.append(fd)
        if not skill or facts_out or not experience:
            exp_data.append(e.model_dump(exclude={"facts"}))
            fact_data.extend(facts_out)
    return {
        "schema_version": 1,
        "profile": profile.model_dump(),
        "experiences": exp_data,
        "facts": fact_data,
    }
# ISCED-grounded education ordinal (eligibility mapping)
_EDU_TERMS: list[tuple[str, int]] = [
    (r"\b(ph\.?d|doctora|doctoral|promotion|doktor|dphil)\b", 3),
    (r"\b(master|m\.?sc|m\.?a\.?|m\.?eng|magister|diplom|staatsexamen|mba|residency)\b", 2),
    (r"\b(bachelor|b\.?sc|b\.?a\.?|b\.?eng|bakkalaureat)\b", 1),
]
_EDU_ORDINAL = {"none": 0, "bachelor": 1, "master": 2, "phd": 3}
def _edu_ordinal(degree: str) -> int:
    """Map a degree string to an ISCED ordinal (0=none, 1=bachelor, 2=master, 3=phd)."""
    import re
    s = (degree or "").strip().lower()
    if s in _EDU_ORDINAL:
        return _EDU_ORDINAL[s]
    # "not completed" / "incomplete" → use the PREVIOUS level
    incomplete = any(w in s for w in ("not completed", "incomplete", "unfinished", "abandoned"))
    for pat, ordv in _EDU_TERMS:
        if re.search(pat, s):
            return max(0, ordv - 1) if incomplete else ordv
    return 0
def _derive_experience_summary(exps: list) -> str:
    """Prose experience summary from canonical facts (for bge-m3 embedding)."""
    parts = []
    for e in sorted(exps, key=lambda x: x.start_date, reverse=True):
        end = "present" if not e.end_date or e.end_date == "present" else e.end_date
        facts = " ".join(f.text.strip() for f in e.facts if f.text)[:500]
        parts.append(f"{e.title} at {e.organization} ({e.start_date}–{end}). {facts}")
    return "\n".join(parts)
def _derive_summary(profile, exps, seniority: str, years, edu_level: str) -> str:
    """2-3 sentence overview from profile data (deterministic, no LLM)."""
    roles = "/".join(profile.basics.target_roles[:2]) or "professional"
    domains = ", ".join(sorted({d for e in exps for d in e.domains})[:3]) or "various domains"
    return (f"{seniority.title()} professional with {years or 'several'} years "
            f"in {domains}. Education: {edu_level}. Targeting {roles} roles. "
            f"Based in {profile.basics.location}.")
def export_profile(staging: bool = False, merged_skills: bool = False) -> dict:
    """Structured candidate profile for matching consumers (no LLM).
    If merged_skills=True, matches downstream consumer schema (skills+tools merged)."""
    import re
    from .normalize import normalize
    profile = load_profile()
    exps = load_experiences(staging=staging)
    skills: set[str] = set()
    tools: set[str] = set()
    domains: set[str] = set()
    for e in exps:
        domains.update(e.domains)
        for f in e.facts:
            skills.update(normalize(s) for s in f.skills)
            tools.update(normalize(t) for t in f.tools)
    title = (max(exps, key=lambda e: e.start_date, default=None).title or "").lower()
    sn = lambda words, val: val if any(w in title for w in words) else None
    seniority = sn(("lead", "principal", "staff", "head", "director"), "lead") \
        or sn(("senior", "sr", "expert"), "senior") \
        or sn(("junior", "entry", "associate"), "junior") or "mid"
    from datetime import datetime
    starts = [int(e.start_date[:4]) for e in exps if e.start_date]
    ends = [datetime.now().year if (not e.end_date or e.end_date == "present")
            else int(e.end_date[:4]) for e in exps]
    years = max(ends) - min(starts) if starts and ends else None
    highest = max(profile.education, key=lambda e: _edu_ordinal(e.degree), default=None)
    edu_level = {0: "none", 1: "bachelor", 2: "master", 3: "phd"}.get(_edu_ordinal(highest.degree) if highest else 0, "none")
    exp_text, sum_text = _derive_experience_summary(exps), _derive_summary(profile, exps, seniority, years, edu_level)
    locs = [profile.basics.location] if profile.basics.location else []
    base = {"experience": exp_text, "summary": sum_text, "domains": sorted(domains),
            "seniority": seniority, "years_experience": years,
            "education": highest.degree if highest else "", "education_level": edu_level,
            "languages": profile.basics.languages, "target_roles": profile.basics.target_roles,
            "locations": locs, "magnets": profile.basics.magnets, "repellents": profile.basics.repellents}
    if merged_skills:
        return {**base, "skills": sorted(skills | tools)}
    return {"schema_version": 1, "name": profile.basics.name, "email": profile.basics.email,
            "phone": profile.basics.phone, "location": profile.basics.location,
            "orcid": profile.basics.orcid, "skills": sorted(skills), "tools": sorted(tools),
            "interests": profile.basics.interests, **base}
def match_jd(jd_path: str, staging: bool = False) -> dict:
    """Deterministic JD skill/education/language/seniority analysis (no LLM)."""
    import re
    from .normalize import normalize, load_aliases
    jd_text = Path(jd_path).read_text(encoding="utf-8")
    jd_lower = jd_text.lower()
    profile = load_profile()
    exps = load_experiences(staging=staging)
    aliases = load_aliases()
    skill_facts: dict[str, list[str]] = {}
    for e in exps:
        for f in e.facts:
            for s in f.skills + f.tools:
                skill_facts.setdefault(normalize(s), []).append(f.id)
    found: list[dict] = []
    for canon, alts in aliases.items():
        forms = [canon] + list(alts)
        if any(re.search(r"\b" + re.escape(f) + r"\b", jd_text, re.I) for f in forms) \
                and canon in skill_facts:
            found.append({"skill": canon, "facts": sorted(set(skill_facts[canon]))})
    edu_req = ("phd" if re.search(r"\bph\.?d|doctorate|promov\w+\b", jd_lower)
               else "master" if re.search(r"\bmaster|m\.?sc|mba|magister|diplom\b", jd_lower)
               else "bachelor" if re.search(r"\bbachelor|b\.?sc\b", jd_lower) else None)
    cand_edu = export_profile(staging=staging).get("education_level", "none")
    cefr = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}
    lang_gaps: list[dict] = []
    for ln, lc in [("german", "de"), ("english", "en"), ("russian", "ru")]:
        m = re.search(rf"\b{ln}\b.*?\b([abc][12])\b", jd_lower)
        if m:
            has = profile.basics.languages.get(lc, "none").lower()
            if cefr.get(has, 0) < cefr.get(m.group(1), 0):
                lang_gaps.append({"language": ln, "required": m.group(1).upper(), "has": has.upper()})
    jd_sen = ("lead" if re.search(r"\b(lead|principal|head of|director)\b", jd_lower)
              else "senior" if re.search(r"\b(senior|sr\.?)\b", jd_lower)
              else "junior" if re.search(r"\b(junior|entry.level|associate)\b", jd_lower) else None)
    cand_sen = export_profile(staging=staging).get("seniority", "mid")
    fsc: dict[str, set[str]] = {}
    for item in found:
        for fid in item["facts"]:
            fsc.setdefault(fid, set()).add(item["skill"])
    recommended = sorted(fsc, key=lambda f: len(fsc[f]), reverse=True)
    return {
        "jd_skills_found": [f["skill"] for f in found], "n_found": len(found),
        "found_details": found,
        "education": {"required": edu_req, "has": cand_edu,
                      "match": edu_req is None or _edu_ordinal(cand_edu) >= _edu_ordinal(edu_req)},
        "language_gaps": lang_gaps,
        "seniority": {"required": jd_sen, "has": cand_sen,
                      "match": jd_sen is None or jd_sen == cand_sen},
        "recommended_facts": [{"id": fid, "skills": sorted(fsc[fid])} for fid in recommended],
        "note": "Lower bound: only detects skills in aliases.yaml. "
                "Semantic fit requires evidence review by the external agent.",
    }
def add_fact(experience_id: str, text: str, kind: str = "technical",
              skills: list[str] | None = None, tools: list[str] | None = None,
              metrics: list[dict] | None = None, *, stage: bool = False) -> str:
    """Validate the complete proposal before atomically saving it."""
    from .normalize import normalize
    import re, sys
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", experience_id):
        raise ValueError("invalid experience ID")
    exp_path = DATA_DIR / "experience" / f"{experience_id}.yaml"
    target = DATA_DIR / ".staging" / exp_path.name if stage else exp_path
    if not target.exists() and not exp_path.exists():
        raise ValueError("Create an experience with valid metadata before adding facts")
    raw = _load_yaml(target if target.exists() else exp_path)
    if raw["id"] != experience_id: raise ValueError("experience ID does not match filename")
    if stage and not target.exists(): raw["facts"] = []
    text = text.strip()
    facts = {**all_facts(), **(all_facts(staging=True) if stage else {})}
    wnew = set(re.findall(r'[a-z]+', text.lower()))
    for fid, f in facts.items():
        wold = set(re.findall(r'[a-z]+', f.text.lower()))
        if wnew and wold:
            ov = len(wnew & wold) / len(wnew | wold)
            if ov > 0.3:
                print(f"WARN: {ov:.0%} word overlap with {fid}: {f.text[:60]}...", file=sys.stderr)
    existing = _load_yaml(exp_path).get("facts", []) if exp_path.exists() else raw.get("facts", [])
    p = existing[0]["id"].rsplit("_", 1)[0] if existing else experience_id
    nums = [int(f.id.rsplit("_", 1)[-1]) for f in facts.values()
            if f.id.startswith(p + "_") and f.id.rsplit("_", 1)[-1].isdigit()]
    fid = f"{p}_{max(nums + [0]) + 1:03d}"
    fact = {"id": fid, "kind": kind, "text": text,
            "skills": [normalize(s) for s in (skills or [])], "tools": [normalize(t) for t in (tools or [])],
            "metrics": metrics or [], "source_refs": []}
    raw.setdefault("facts", []).append(fact)
    _save_experience(target, raw)
    loc = "staging" if stage else "canonical"
    print(f"Added {fid} to {experience_id} ({loc})", file=sys.stderr)
    return fid

def _save_experience(path, raw):
    import tempfile
    Experience(**raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            yaml.safe_dump(raw, handle, sort_keys=False, allow_unicode=True)
            handle.flush()
            import os
            os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
def skill_inventory() -> dict[str, list[str]]:
    """Return {skill: [fact_ids]} and {tool: [fact_ids]} for all canonical facts."""
    from .normalize import normalize
    skills: dict[str, list[str]] = {}
    tools: dict[str, list[str]] = {}
    for fid, f in all_facts().items():
        for s in f.skills:
            skills.setdefault(normalize(s), []).append(fid)
        for t in f.tools:
            tools.setdefault(normalize(t), []).append(fid)
    return {"skills": skills, "tools": tools}

# ── SOTA quality tracking (hybrid: stored metadata + computed metrics) ──
# Pattern: Catalog-Intelligence-Pipeline (2026-08) + DAMA dimensions +
# Great Expectations (computed assertions, not stored scores).
# Stored: confidence, source, verified, notes, last_updated (user/agent set)
# Computed: detail, completeness, score (derived, always current)
def fact_quality(f: Fact) -> dict:
    """Compute quality dimensions (SOTA: computed, not stored). Hybrid model:
    stored metadata (confidence, source, verified) + computed metrics (detail, score)."""
    q = f.quality or {}
    w = len((f.text or "").split())
    has_m, has_s, has_t = bool(f.metrics), bool(f.skills), bool(f.tools)
    source, verified = q.get("source", "unknown"), q.get("verified", False); evidence = f.kind in {"publication", "certification"} or has_m or has_t
    issues = (["thin text"] if w < 12 else []) + (["no skills"] if not has_s else []) + (["no metric/tool evidence"] if not evidence else []) + (["source unknown"] if source == "unknown" else []) + (["unverified"] if not verified else [])
    return {"detail": "sparse" if w < 8 else "adequate" if w < 16 else "rich", "words": w,
            "has_metrics": has_m, "has_skills": has_s, "has_tools": has_t,
            "completeness": round(sum([has_s, evidence, source != "unknown", verified]) / 4, 2),
            "score": round(sum([w >= 12, has_s, evidence, source != "unknown", verified]) / 5, 2),
            "confidence": q.get("confidence", 0.5), "source": source, "verified": verified,
            "notes": q.get("notes", ""), "issues": issues}
def delete_fact(fact_id: str) -> bool:
    """Remove a fact by ID from canonical data. Returns True if deleted."""
    for p in sorted((DATA_DIR / "experience").glob("*.yaml")):
        data = _load_yaml(p)
        before = len(data.get("facts", []))
        data["facts"] = [f for f in data.get("facts", []) if f.get("id") != fact_id]
        if len(data["facts"]) < before:
            with open(p, "w") as f: yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
            return True
    return False
def clean_data() -> list[str]:
    """Remove orphaned files, stale staging, dead source_refs."""
    removed = []
    for p in sorted((DATA_DIR / "experience").glob("*.yaml")):
        data = _load_yaml(p)
        for f in data.get("facts", []):
            if f.get("source_refs"): f["source_refs"] = []
        with open(p, "w") as fh: yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)
        removed.append(f"cleared source_refs: {p.name}")
    for p in sorted((DATA_DIR / ".staging").glob("*.yaml")) if (DATA_DIR / ".staging").exists() else []:
        p.unlink(); removed.append(f"staging: {p.name}")
    return removed
def promote_staging(experience_id: str) -> int:
    """Atomically append valid, nonconflicting staged facts; preserve rejected proposals."""
    import re
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", experience_id): raise ValueError("invalid experience ID")
    sp = DATA_DIR / ".staging" / f"{experience_id}.yaml"
    if not sp.exists(): return 0
    staged = _load_yaml(sp)
    proposal = Experience(**staged)
    if proposal.id != experience_id: raise ValueError("experience ID does not match filename")
    collisions = set(all_facts()) & {f.id for f in proposal.facts}
    if collisions: raise ValueError(f"staging collision: {sorted(collisions)}")
    if not proposal.facts: raise ValueError("No staged facts to promote")
    ep = DATA_DIR / "experience" / f"{experience_id}.yaml"
    canon = _load_yaml(ep) if ep.exists() else staged
    if ep.exists():
        if Experience(**canon).model_dump(exclude={"facts"}) != proposal.model_dump(exclude={"facts"}):
            raise ValueError("Staged experience metadata differs from canonical")
        canon.setdefault("facts", []).extend(staged["facts"])
    _save_experience(ep, canon)
    sp.unlink()
    return len(staged.get("facts", []))
