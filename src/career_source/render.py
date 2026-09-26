"""RenderCV adapter: resume-selection-schema → RenderCV YAML → PDF (§11)."""
from __future__ import annotations
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml
from . import load as _load
from .resume import load_resume_spec
DEFAULT_TEMPLATE = "engineeringresumes"
GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated"
_TEMPLATE_RULES: list[tuple[list[str], str]] = [
    (["product", "project", "program", "business", "consult", "strategy",
      "lead", "manager", "director", "head"], "classic"),
    (["engineer", "developer", "architect", "devops", "sre", "data scientist",
      "ml", "research", "scientist"], "engineeringresumes"),
    (["design", "ux", "ui"], "sb2nov"),
]
def _pick_template(role: str) -> str:
    """Select a RenderCV theme based on role keywords."""
    r = (role or "").lower()
    for keywords, theme in _TEMPLATE_RULES:
        if any(k in r for k in keywords):
            return theme
    return DEFAULT_TEMPLATE
def _fix_date(d: str | None) -> str | int | None:
    """Preserve year-only precision for RenderCV."""
    return int(d) if d and len(d) == 4 and d.isdigit() else d

def _highlights(bullets, facts):
    return [text for b in bullets for text in ([b.text] if b.text else [facts[fid].text for fid in b.source_fact_ids])]

def _to_rendercv(spec) -> dict:
    """Convert our resume selection schema → RenderCV YAML dict."""
    profile = _load.load_profile(); basics = profile.basics
    exps = {e.id: e for e in _load.load_experiences()}
    facts = {f.id: f for e in exps.values() for f in e.facts}
    social = [{"network": n, "username": u} for n, u in basics.socials.items()]
    social += [{"network": "ORCID", "username": basics.orcid}] if basics.orcid else []
    sections: dict[str, list] = {}
    if spec.summary: sections["summary"] = [spec.summary]
    # work experience (reverse chronological)
    experience: list[dict] = []
    for we in sorted(spec.sections.work, key=lambda w: exps[w.experience_id].start_date, reverse=True):
        exp = exps[we.experience_id]
        entry: dict = {
            "company": exp.organization,
            "position": exp.title,
            "start_date": _fix_date(exp.start_date),
            "highlights": _highlights(we.bullets, facts),
        }
        if exp.end_date:
            entry["end_date"] = _fix_date(exp.end_date)
        experience.append(entry)
    if experience: sections["experience"] = experience
    # education
    edu_list: list[dict] = []
    education = {e.id: e for e in profile.education}
    for e in spec.sections.education:
        pe = education[e.education_id]
        entry = {"institution": pe.institution,
                 "area": ", ".join(x for x in (pe.degree, pe.focus) if x),
                 "degree": "", "start_date": _fix_date(pe.start_date)}
        if pe.end_date: entry["end_date"] = _fix_date(pe.end_date)
        edu_list.append(entry)
    if edu_list: sections["education"] = edu_list
    # projects
    if spec.sections.projects:
        proj_entries: list[dict] = []
        for p in spec.sections.projects:
            entry: dict = {"name": f"[{p.name}]({p.url})" if p.url else p.name, "highlights": _highlights(p.bullets, facts)}
            if p.url:
                entry["url"] = p.url
            proj_entries.append(entry)
        sections["projects"] = proj_entries
    # structured groups are self-contained in the spec; flat skills remain backward compatible
    if spec.sections.skill_groups:
        sections["skills"] = [{"label": label, "details": ", ".join(items)}
                              for label, items in spec.sections.skill_groups.items()]
    elif spec.sections.skills:
        sections["skills"] = [", ".join(spec.sections.skills)]

    # publications
    if spec.sections.publications:
        sections["publications" if spec.name == "master" else "Selected Publications"] = [facts[p.fact_id].text for p in spec.sections.publications]
    if basics.languages:
        names = {"en": "English", "de": "German", "ru": "Russian"}
        sections["languages"] = [{"label": names.get(code, code), "details": level} for code, level in basics.languages.items()]
    headline = spec.target.role or (basics.interests[0] if basics.interests else None)
    _order = ["summary", "skills", "experience", "education", "projects", "Selected Publications", "publications", "languages"]
    sections = {k: sections[k] for k in _order if k in sections}
    return {
        "cv": {
            "name": basics.name,
            **({"headline": headline} if headline else {}),
            **({"photo": str(_load.DATA_DIR / "profile" / basics.photo)} if basics.photo else {}),
            "email": basics.email,
            "phone": basics.phone,
            "location": basics.location,
            **({"social_networks": social} if social else {}),
            "sections": sections,
        },
        "design": {
            "theme": (spec.design.template if spec.design and spec.design.template
                      else _pick_template(spec.target.role)),
            "page": {"size": "a4"},
            "sections": {"show_time_spans_in": []},
            "header": {"photo_width": "2.7cm", "photo_position": "right"},
            **({"entries": {"allow_page_break": True}} if spec.name == "master" else {}),
        },
    }

def render(spec_path: str | Path) -> Path:
    """Validate, render in isolation, and publish only a nonempty current PDF."""
    from .validate import validate
    from .validate_resume import validate_resume
    errors = [r.message for r in validate() + validate_resume(spec_path) if r.level == "ERROR"]
    if errors: raise ValueError("; ".join(errors))
    spec = load_resume_spec(spec_path)
    if Path(spec.name).name != spec.name or spec.name in {"", ".", ".."}:
        raise ValueError("resume name must be a filename stem")
    rc_yaml = _to_rendercv(spec)
    GENERATED_DIR.mkdir(exist_ok=True)
    target = GENERATED_DIR / f"{spec.name}.pdf"
    with tempfile.TemporaryDirectory(prefix="render-", dir=GENERATED_DIR) as directory:
        run_dir = Path(directory)
        tmp_path = run_dir / "resume.yaml"
        with tmp_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(rc_yaml, handle, sort_keys=False, allow_unicode=True)
        rcv = shutil.which("rendercv") or str(Path(sys.executable).parent / "rendercv")
        result = subprocess.run(
            [rcv, "render", str(tmp_path),
             "--output-folder", str(run_dir),
             "--dont-generate-markdown", "--dont-generate-html",
             "--dont-generate-png"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"rendercv failed (exit {result.returncode}): {result.stderr or result.stdout}")
        candidates = list(run_dir.rglob("*.pdf"))
        if len(candidates) != 1 or candidates[0].stat().st_size == 0:
            raise RuntimeError("rendercv did not produce exactly one nonempty PDF")
        candidates[0].replace(target)
    return target
