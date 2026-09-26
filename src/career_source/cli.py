"""Typer CLI (§9)."""
from __future__ import annotations
import json
from pathlib import Path
import typer
import yaml
from .load import export_context as _export_context, export_profile as _export_profile, match_jd as _match_jd, add_fact as _add_fact, skill_inventory as _skill_inventory, fact_quality as _fact_quality, delete_fact as _delete_fact, clean_data as _clean_data, promote_staging as _promote_staging, all_facts as _all_facts
from .validate import validate as _validate_fn
from .validate_resume import validate_resume as _validate_resume_fn
from .resume import build_all as _build_all, build_include as _build_include, tailor_jd as _tailor_jd, polish_jd as _polish_jd, assembly_report as _assembly_report, extract_facts as _extract_facts
from .render import render as _render_fn
from .models import ValidationResult

app = typer.Typer(no_args_is_help=True, add_completion=False)
def _emit(obj, json_out: bool) -> None:
    """Emit as JSON (--json) or YAML (default)."""
    if json_out:
        typer.echo(json.dumps(obj, indent=2, ensure_ascii=False))
    else:
        typer.echo(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True))
SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"
GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated"
def _print_results(results: list[ValidationResult]) -> None:
    errors = [r for r in results if r.level == "ERROR"]
    warns = [r for r in results if r.level == "WARN"]
    for r in results:
        prefix = "ERROR" if r.level == "ERROR" else "WARN "
        typer.echo(f"  {prefix}: {r.message}")
    if errors:
        typer.echo(f"\n{len(errors)} error(s), {len(warns)} warning(s)")
        raise typer.Exit(1)
    typer.echo(f"\nOK — {len(warns)} warning(s)")
@app.command()
def validate(
    staging: bool = typer.Option(False, "--staging", help="validate data/.staging/"),
):
    """Validate canonical career data (§12.1)."""
    typer.echo("Validating " + ("staging..." if staging else "canonical..."))
    results = _validate_fn(staging=staging)
    _print_results(results)
@app.command(name="validate-resume")
def validate_resume_cmd(
    file: str = typer.Argument(..., help="resume spec YAML path"),
):
    """Validate a generated resume spec (§12.2)."""
    typer.echo(f"Validating resume spec: {file}")
    results = _validate_resume_fn(file)
    _print_results(results)
@app.command()
def facts(
    skill: str = typer.Option(None, "--skill", help="filter by skill (normalized)"),
    experience: str = typer.Option(None, "--experience", help="filter by experience ID"),
    json_out: bool = typer.Option(False, "--json", help="JSON output with computed quality"),
):
    """List facts, optionally filtered. --json includes computed quality scores."""
    ctx = _export_context(skill=skill, experience=experience)
    fact_list = ctx["facts"]
    if json_out:
        for f in fact_list:
            fid = f["id"]
            f["computed_quality"] = _fact_quality(_all_facts()[fid]) if fid in _all_facts() else {}
        typer.echo(json.dumps(fact_list, indent=2, ensure_ascii=False))
    else:
        for f in fact_list:
            typer.echo(f"  {f['id']}  [{f['kind']}]  {f['text'][:80]}")
@app.command()
def skills(json_out: bool = typer.Option(False, "--json")):
    """List all skills and tools with fact counts."""
    inv = _skill_inventory()
    if json_out:
        typer.echo(json.dumps(inv, indent=2, ensure_ascii=False)); return
    typer.echo("SKILLS:")
    for s, fids in sorted(inv["skills"].items()):
        typer.echo(f"  {s:35s} ← {len(fids)} facts: {', '.join(fids[:3])}")
    typer.echo("\nTOOLS:")
    for t, fids in sorted(inv["tools"].items()):
        typer.echo(f"  {t:35s} ← {len(fids)} facts: {', '.join(fids[:3])}")
@app.command()
def context(
    skill: str = typer.Option(None, "--skill"),
    experience: str = typer.Option(None, "--experience"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Export career context bundle (§15)."""
    ctx = _export_context(skill=skill, experience=experience)
    _emit(ctx, json_out)
@app.command(name="export-profile")
def export_profile(
    json_out: bool = typer.Option(False, "--json"),
    merged_skills: bool = typer.Option(False, "--merged-skills", help="profile with merged skills and tools"),
):
    """Export structured candidate profile for matching consumers."""
    prof = _export_profile(merged_skills=merged_skills)
    _emit(prof, json_out)
@app.command()
def build(
    include: list[str] = typer.Option(None, "--include", help="fact IDs to include"),
    all_facts: bool = typer.Option(False, "--all", help="master view (all facts)"),
    output: str = typer.Option(..., "--output", "-o", help="output YAML path"),
):
    """Mode B: deterministically assemble a resume spec (§10.2, §10.3)."""
    if not include and not all_facts:
        typer.echo("Error: need --include <id> or --all", err=True)
        raise typer.Exit(1)
    # support comma-separated IDs: --include demo_001,demo_002
    if include and isinstance(include, list) and len(include) == 1 and "," in include[0]:
        include = [x.strip() for x in include[0].split(",") if x.strip()]
    if all_facts:
        path = _build_all(output)
    else:
        path = _build_include(include, output)
    typer.echo(f"Built: {path}")
@app.command()
def render(spec: str = typer.Argument(..., help="resume spec YAML path")):
    """Render a resume spec to PDF via RenderCV (§11)."""
    typer.echo(f"Rendering {spec}...")
    try:
        typer.echo(f"PDF: {_render_fn(spec)}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
@app.command()
def match(
    jd: str = typer.Argument(..., help="JD text file path"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Analyze a JD against canonical data (deterministic, no LLM)."""
    r = _match_jd(jd)
    if json_out:
        typer.echo(json.dumps(r, indent=2, ensure_ascii=False)); return
    typer.echo(f"\nSkills found: {r['n_found']}  |  Education: {r['education']['match']}  |  Seniority: {r['seniority']['match']}")
    for item in r["found_details"]:
        typer.echo(f"  {item['skill']:30s} ← {', '.join(item['facts'])}")
    typer.echo(f"\nRecommended facts:")
    for rec in r["recommended_facts"][:10]:
        typer.echo(f"  {rec['id']:12s} covers: {', '.join(rec['skills'])}")
    typer.echo(f"\nNote: {r['note']}")
@app.command()
def schemas():
    """Export JSON Schemas into schemas/ (§9)."""
    SCHEMAS_DIR.mkdir(exist_ok=True)
    from .models import Experience, ResumeSpec, Profile
    for name, model in [
        ("experience", Experience),
        ("resume", ResumeSpec),
        ("context", Profile),
    ]:
        schema = model.model_json_schema()
        path = SCHEMAS_DIR / f"{name}.schema.json"
        with open(path, "w") as f:
            json.dump(schema, f, indent=2)
        typer.echo(f"  {path}")
@app.command()
def tailor(
    jd: str = typer.Argument(..., help="JD text file path"),
    output: str = typer.Option(None, "--output", "-o", help="output YAML path"),
    max_per_exp: int = typer.Option(2, "--max", help="max facts per experience"),
    render_pdf: bool = typer.Option(True, "--render/--no-render", help="render PDF"),
):
    """JD → tailored resume: deterministic verbatim transfer (no LLM slop).
    Extracts JD keywords, scores facts by keyword overlap, selects top facts
    per experience, and assembles a spec where bullets use fact.text verbatim
    (no rewriting). Validates provenance, optionally renders PDF.
    """
    jd_path = Path(jd)
    if not jd_path.exists():
        typer.echo(f"File not found: {jd}", err=True); raise typer.Exit(1)
    out = output or str(GENERATED_DIR / f"{jd_path.stem}_tailored.yaml")
    r = _tailor_jd(jd, out, max_per_exp=max_per_exp)
    typer.echo(f"Tailored: {r['n_facts']} facts from {len(r['selected'])} experiences")
    typer.echo(f"Spec: {r['output']}")
    for eid, fids in r["selected"].items():
        typer.echo(f"  {eid}: {', '.join(fids)}")
    results = _validate_resume_fn(r["output"])
    _print_results(results)
    if render_pdf and not any(x.level == "ERROR" for x in results):
        typer.echo(f"Rendering...")
        try:
            pdf = _render_fn(r["output"])
            typer.echo(f"PDF: {pdf}")
        except Exception as e:
            typer.echo(f"Render error: {e}", err=True)
            raise typer.Exit(1)
@app.command()
def polish(
    spec: str = typer.Argument(..., help="tailored resume spec YAML"),
    jd: str = typer.Option(..., "--jd", help="JD text file"),
    model: str = typer.Option("granite4.1:30b", "--model"),
    render_pdf: bool = typer.Option(True, "--render/--no-render"),
):
    """LLM polish of verbatim facts (single generation, no agent loop)."""
    typer.echo(f"Polishing {spec} with {model}...")
    out = _polish_jd(spec, jd, model=model)
    typer.echo(f"Output: {out}")
    results = _validate_resume_fn(out)
    _print_results(results)
    if render_pdf and not any(x.level == "ERROR" for x in results):
        try:
            typer.echo(f"PDF: {_render_fn(out)}")
        except Exception as e:
            typer.echo(f"Render error: {e}", err=True)
            raise typer.Exit(1)
@app.command()
def add(
    experience: str = typer.Argument(..., help="experience ID"),
    text: str = typer.Option(..., "--text", "-t", help="fact text (plain prose)"),
    kind: str = typer.Option("technical", "--kind", "-k"),
    skills: str = typer.Option("", "--skills", "-s", help="comma-separated"),
    tools: str = typer.Option("", "--tools", help="comma-separated"),
    metrics: str = typer.Option("", "--metrics", help="value:unit:context, comma-separated"),
    stage: bool = typer.Option(False, "--stage", help="write to .staging/ (§14 ingestion)"),
):
    """Validate and add a fact; --stage keeps it proposed until reviewed."""
    ml = []
    if metrics:
        for m in metrics.split(","):
            parts = m.strip().split(":", 2)
            if len(parts) < 2 or not parts[0] or not parts[1]:
                raise typer.BadParameter("metrics must be value:unit[:context]")
            ml.append({"value": parts[0], "unit": parts[1],
                       "context": parts[2] if len(parts) > 2 else ""})
    fid = _add_fact(experience, text, kind=kind,
        skills=[s.strip() for s in skills.split(",") if s.strip()] or None,
        tools=[t.strip() for t in tools.split(",") if t.strip()] or None,
        metrics=ml or None, stage=stage)
    typer.echo(f"Added {fid} to {experience}")
    _print_results(_validate_fn(staging=stage))
@app.command()
def esco(
    refresh: bool = typer.Option(False, "--refresh", help="ignore cache"),
    occupations: bool = typer.Option(False, "--occupations", help="check occupations not skills"),
):
    """Check all skills/tools against ESCO taxonomy (advisory, keyless)."""
    from .normalize import esco_lookup
    from .load import DATA_DIR, load_experiences
    if refresh:
        (DATA_DIR / ".esco_cache.json").unlink(missing_ok=True)
    kind = "occupation" if occupations else "skill"
    src = {e.title: [e.id] for e in load_experiences()} if occupations else _skill_inventory()["skills"]
    typer.echo(f"\n{'OCCUPATIONS' if occupations else 'SKILLS'}:")
    n = 0
    for term in sorted(src):
        r = esco_lookup(term, kind=kind)
        if r:
            n += 1; typer.echo(f"  ✅ {term:35s} → {r['label']}")
        else:
            typer.echo(f"  ❌ {term:35s} (not in ESCO)")
    typer.echo(f"\n{n}/{len(src)} matched in ESCO")
@app.command()
def quality(
    json_out: bool = typer.Option(False, "--json"),
    worst: int = typer.Option(0, "--worst", help="show N worst facts"),
    staging: bool = typer.Option(False, "--staging", help="check staging facts"),
):
    """Show fact quality scores (detail, metrics, completeness, verification)."""
    rows = sorted(((fid, _fact_quality(f)) for fid, f in _all_facts(staging=staging).items()), key=lambda x: x[1]["score"])
    if worst: rows = rows[:worst]
    if json_out: typer.echo(json.dumps(dict(rows), indent=2)); return
    typer.echo(f"\nQUALITY REPORT ({len(rows)} facts)")
    typer.echo("═" * 80)
    for fid, q in rows:
        typer.echo(f"  {fid:12s} {q['score']:>4.0%}  {q['detail']:8s}  "
                   f"M={'Y' if q['has_metrics'] else 'N'} S={'Y' if q['has_skills'] else 'N'} "
                   f"T={'Y' if q['has_tools'] else 'N'}  {q['source']:12s} {'✓' if q['verified'] else ''}")
    low = [r for r in rows if r[1]["score"] < 0.6]
    if low:
        typer.echo("═" * 80)
        typer.echo(f"NEEDS IMPROVEMENT ({len(low)} facts below 60%):")
        for fid, q in low:
            gaps = ", ".join(q["issues"])
            typer.echo(f"  {fid:12s} {q['score']:>4.0%}  {q['detail']}, {gaps}{(' → ' + q['notes']) if q['notes'] else ''}")
@app.command()
def delete(fact_id: str):
    """Delete a fact by ID from canonical data."""
    if not _delete_fact(fact_id):
        typer.echo(f"ERROR: fact {fact_id} not found", err=True); raise typer.Exit(1)
    typer.echo(f"Deleted {fact_id}"); _print_results(_validate_fn())
@app.command()
def clean():
    """Remove orphaned files, stale staging, dead source_refs."""
    actions = _clean_data()
    if not actions: typer.echo("Nothing to clean"); return
    for a in actions: typer.echo(f"  removed: {a}")
    typer.echo(f"\n{len(actions)} cleanup action(s)")
@app.command()
def promote(experience_id: str):
    """Move staged facts to canonical (merge into existing experience)."""
    n = _promote_staging(experience_id)
    if not n: typer.echo(f"No staging file for {experience_id}", err=True); raise typer.Exit(1)
    typer.echo(f"Promoted {n} fact(s) from staging to {experience_id}"); _print_results(_validate_fn())
@app.command()
def report(spec: str, jd: str):
    """Assembly report: selected, excluded, coverage %, needs rephrasing."""
    r = _assembly_report(spec, jd)
    typer.echo(f"\nASSEMBLY REPORT  |  JD coverage: {r['coverage_pct']}%  |  Gaps: {', '.join(r['gaps']) or 'none'}")
    typer.echo("═" * 70)
    typer.echo(f"\nSELECTED ({len(r['selected'])} — brought to top):")
    for s in r["selected"]:
        typer.echo(f"  {s['id']:12s} rel={s['relevance']:>5.1f} q={s['quality_score']:>4.0%} {s['detail']:8s} [{s['kind']}] {s['text'][:55]}")
    typer.echo(f"\nEXCLUDED (top {len(r['excluded'])} — thrown out):")
    for s in r["excluded"]:
        typer.echo(f"  {s['id']:12s} rel={s['relevance']:>5.1f} q={s['quality_score']:>4.0%} {s['detail']:8s} [{s['kind']}] {s['text'][:55]}")
    if r["needs_rephrasing"]:
        typer.echo(f"\nNEEDS REPHRASING ({len(r['needs_rephrasing'])}):")
        for s in r["needs_rephrasing"]:
            typer.echo(f"  {s['id']:12s} q={s['quality_score']:>4.0%} {s['detail']}{' (no metrics)' if not s['has_metrics'] else ''}")
@app.command()
def extract(experience: str, text: str = typer.Option(..., "--text", "-t"), model: str = typer.Option("granite4.1:30b", "--model")):
    """Extract structured facts from raw text via ollama, write to staging."""
    facts = _extract_facts(text, model)
    if not facts:
        typer.echo("No facts extracted.", err=True); raise typer.Exit(1)
    for f in facts:
        _add_fact(experience, text=f["text"], kind=f.get("kind", "technical"),
                  skills=f.get("skills"), tools=f.get("tools"), metrics=f.get("metrics"), stage=True)
    typer.echo(f"Extracted {len(facts)} facts to staging. Run: career validate --staging && career quality --staging")
@app.command()
def master():
    """Master resume (all facts, deterministic) → data/master_latest.pdf."""
    _build_all("data/master_latest.yaml"); import shutil; shutil.copy(_render_fn('data/master_latest.yaml'), "data/master_latest.pdf"); typer.echo("→ data/master_latest.pdf")

if __name__ == "__main__":
    app()
