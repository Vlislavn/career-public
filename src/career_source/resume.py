"""Resume selection schema + deterministic build assembler (§10, §11)."""
from __future__ import annotations
from pathlib import Path
import yaml
from .load import load_experiences, load_profile, all_facts
from .models import ResumeSpec, ResumeBullet, ResumeWorkEntry, ResumeSections

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated"
_SOFT_SKILLS = set("conference presentation|cross-functional collaboration|cross-functional leadership|delegation|knowledge sharing|mentoring|project leadership|research initiative|stakeholder communication|teaching|technical communication|technical leadership".split("|"))
_CLINICAL_QUALITY = "biomarker|capa|clinical|fda|guideline|medical oncology|ngs|process improvement|quality|root-cause".split("|")
_RESEARCH_EVALUATION = "benchmark cluster-bootstrap evaluation experiment failure-mode ground-truth hypothesis literature negative-result oracle pass@k performance reliability research scientific tri-state".split()
def _master_skill_groups(exps) -> dict[str, list[str]]:
    # ponytail: keyword grouping; replace with an explicit taxonomy if a skill is misclassified.
    groups = {k: [] for k in ("Hard - Clinical & quality", "Hard - AI, data & engineering", "Hard - Research & evaluation", "Soft - Leadership & collaboration")}
    for skill in sorted({s for e in exps for f in e.facts for s in f.skills}):
        low = skill.lower()
        label = ("Soft - Leadership & collaboration" if low in _SOFT_SKILLS else
                 "Hard - Clinical & quality" if any(x in low for x in _CLINICAL_QUALITY) else
                 "Hard - Research & evaluation" if any(x in low for x in _RESEARCH_EVALUATION) else
                 "Hard - AI, data & engineering")
        groups[label].append(skill)
    groups["Tools & technologies"] = sorted({t for e in exps for f in e.facts for t in f.tools})
    return {label: items for label, items in groups.items() if items}
def build_include(fact_ids: list[str], output: str | Path) -> Path:
    """Mode B: assemble selected facts verbatim into a resume spec (§10.2)."""
    facts = all_facts()
    missing = set(fact_ids) - facts.keys()
    if missing: raise ValueError(f"unknown fact IDs: {sorted(missing)}")
    if not fact_ids: raise ValueError("Select at least one fact")
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    exps = {e.id: e for e in load_experiences()}

    # group facts by experience
    by_exp: dict[str, list[str]] = {}
    for fid in fact_ids:
        for eid, exp in exps.items():
            if any(f.id == fid for f in exp.facts):
                by_exp.setdefault(eid, []).append(fid)
                break
    work: list[ResumeWorkEntry] = []
    for eid, fids in by_exp.items():
        bullets = [ResumeBullet(source_fact_ids=[fid]) for fid in fids]
        work.append(ResumeWorkEntry(experience_id=eid, bullets=bullets))
    spec = ResumeSpec(name="selection", target={"company": "", "role": ""}, sections=ResumeSections(work=work))
    with open(out, "w") as f:
        yaml.safe_dump(spec.model_dump(), f, sort_keys=False, allow_unicode=True)
    return out
def build_all(output: str | Path) -> Path:
    """Master view: every fact of every experience."""
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    exps = sorted(load_experiences(), key=lambda e: e.start_date if e.start_date != "present" else "9999", reverse=True)
    independent = next((e for e in exps if e.id == "independent"), None)
    projects = [f for f in independent.facts if f.kind not in {"publication", "certification"}] if independent else []
    publications = [f.id for e in exps for f in e.facts if f.kind == "publication"]
    work = []
    for e in exps:
        facts = [f for f in e.facts if f.kind != "publication" and (e.id != "independent" or f.kind == "certification")]
        if facts: work.append(ResumeWorkEntry(experience_id=e.id, bullets=[ResumeBullet(source_fact_ids=[f.id]) for f in facts]))
    profile = load_profile(); b = profile.basics
    role = b.target_roles[0] if b.target_roles else None
    areas = [m for m in b.magnets if not role or m.lower() not in role.lower()]
    summary = f"{role} working across {', '.join(areas[:3])}." if role else None
    spec = ResumeSpec(name="master", target={"company": "", "role": ""}, summary=summary,
        sections=ResumeSections(work=work,
            projects=[{"name": "Independent Projects", "bullets": [{"text": f.text, "source_fact_ids": [f.id]} for f in projects]}] if projects else [],
            publications=[{"fact_id": fid} for fid in publications], skill_groups=_master_skill_groups(exps),
            education=[{"education_id": e.id} for e in profile.education]))
    with open(out, "w") as f:
        yaml.safe_dump(spec.model_dump(), f, sort_keys=False, allow_unicode=True)
    return out

_STOP_WORDS = set(
    "the a an and or for to of in on at by with from as is are be will you your "
    "we our us they their it its this that these those not no yes if then else "
    "when where who whom which what why how all any each every some none more most "
    "less few many much very can could should would may might must shall do does did "
    "has have had been being was were am i me my mine he she his her hers him they "
    "them out about into over under again further once here there both each few such "
    "no nor only own same so than too very can will just don should now per via etc "
    "off up down across after before during between within without along among towards "
    "through throughout towards upon amongst whilst whereas regardless notwithstanding"
    .split())
def _extract_jd_keywords(jd_text: str) -> set[str]:
    """Extract content keywords from JD text."""
    import re
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]{1,30}", jd_text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) >= 2}
def tailor_jd(jd_path: str, output: str | Path, *, max_per_exp: int = 2,
              max_experiences: int = 5) -> dict:
    """JD → verbatim resume spec via TF-IDF keyword matching. Recency-weighted allocation."""
    from collections import Counter
    jd_text = Path(jd_path).read_text(encoding="utf-8")
    jd_words = list(_extract_jd_keywords(jd_text))
    freq = Counter(jd_words)
    idf = {w: 1.0 / freq[w] for w in freq}  # rare words → higher weight
    facts = all_facts()
    exps = {e.id: e for e in load_experiences()}
    scored: list[tuple[str, float]] = []
    for fid, f in facts.items():
        fw = set(f.text.lower().split())
        for s in f.skills: fw.update(s.lower().split())
        for t in f.tools: fw.update(t.lower().split())
        score = sum(idf.get(w, 0) for w in (set(freq) & fw))
        if f.metrics: score += 2.0  # quality bonus: facts with metrics
        if score > 0: scored.append((fid, round(score, 2)))
    scored.sort(key=lambda x: x[1], reverse=True)
    # recency allocation: recent experience gets more bullets
    sorted_exps = sorted(exps.values(),
        key=lambda e: e.start_date if e.start_date != "present" else "9999", reverse=True)
    by_exp: dict[str, list[str]] = {}
    used: set[str] = set()
    for idx, exp in enumerate(sorted_exps):
        limit = max(1, max_per_exp + 1 - idx) if idx < 2 else max(1, max_per_exp - 1)
        for fid, sc in scored:
            if fid in used: continue
            if any(f.id == fid for f in exp.facts):
                by_exp.setdefault(exp.id, []).append(fid)
                used.add(fid)
                if len(by_exp[exp.id]) >= limit: break
        if len(by_exp) >= max_experiences: break
    work = [ResumeWorkEntry(experience_id=eid,
                            bullets=[ResumeBullet(source_fact_ids=[fid]) for fid in fids])
            for eid, fids in by_exp.items()]
    work.sort(key=lambda w: exps[w.experience_id].start_date
              if exps[w.experience_id].start_date != "present" else "9999", reverse=True)
    spec = ResumeSpec(name="tailored", target={"company": "", "role": ""},
                      sections=ResumeSections(work=work))
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        yaml.safe_dump(spec.model_dump(), f, sort_keys=False, allow_unicode=True)
    return {"output": str(out), "n_keywords": len(freq),
            "n_facts": sum(len(v) for v in by_exp.values()),
            "selected": {eid: fids for eid, fids in by_exp.items()},
            "scores": dict(scored[:15])}
def load_resume_spec(path: str | Path) -> ResumeSpec:
    """Load a resume selection spec from YAML."""
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return ResumeSpec(**raw)
_POLISH_SYS = (
    "Write ONE resume bullet from a fact using Enhanced STAR: [Result with metric first] by [Action with tools/skills] for [Situation/Task]. "
    "Lead with the business outcome and its NUMBER. If no metrics, lead with the key capability delivered. "
    "Mention tools/skills from the fact in the action clause. "
    "Start with a strong verb (Built, Designed, Led, Shipped, Automated, Created, Engineered). "
    "NEVER use: Coordinated, Maintained, Streamlined, Enabled, Leverage, Utilized, comprehensive, robust, seamless. "
    "Reframe to emphasize what the JD cares about — JD is your PRIMARY context. "
    "MUST REWRITE the fact, never copy verbatim. NEVER invent numbers. "
    "ALL numbers as DIGITS (4 not four). No em dashes. Output only the bullet text.")
def _ollama_chat(model: str, system: str, user: str, timeout: int = 90) -> str:
    """Single-shot ollama /api/chat call."""
    import json, re, urllib.request
    msg = json.dumps({"model": model, "think": False, "stream": False,
        "options": {"temperature": 0.6, "num_predict": 300},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    raw = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/chat", data=msg,
        headers={"Content-Type": "application/json"}), timeout=timeout).read())
    text = raw["message"]["content"].strip().strip("\"'")
    text = text.replace("\u2014", ". ").replace("\u2013", "-").replace("\u2212", "-")
    text = re.sub(r"\b(\d+)\.0\b", r"\1", text)
    return re.sub(r"\s+", " ", text).strip().strip(".")
def polish_jd(spec_path: str | Path, jd_path: str, model: str = "granite4.1:30b",
              output: str | Path | None = None) -> str:
    """LLM write STAR bullets from facts via ollama, with summary + gap report."""
    from .validate_resume import validate_resume
    jd = Path(jd_path).read_text(encoding="utf-8")[:800]
    facts = all_facts()
    spec = load_resume_spec(spec_path)
    out = Path(output) if output else Path(str(spec_path).replace(".yaml", "_polished.yaml"))
    def _save():
        with open(out, "w") as fh:
            yaml.safe_dump(spec.model_dump(), fh, sort_keys=False, allow_unicode=True)
    for we in spec.sections.work:
        for b in we.bullets:
            if b.text: continue
            fid = b.source_fact_ids[0]
            if fid not in facts: continue
            f = facts[fid]
            sk = ", ".join(f.skills + f.tools) if (f.skills or f.tools) else ""
            mt = "; ".join(f"{m.value}{m.unit} ({m.context})" for m in f.metrics) if f.metrics else ""
            user = (f"JD excerpt:\n{jd}\n\nFact:\n{f.text}\n\n"
                    f"Skills/tools: {sk}\nMetrics: {mt}\n\nBullet:")
            try:
                text = _ollama_chat(model, _POLISH_SYS, user)
                # metric survival: all metric values must appear
                ok = all(str(int(m.value)) in text if m.value == int(m.value)
                         else str(m.value) in text for m in f.metrics)
                # anti-fabrication: strip numbers not in fact metrics
                valid_nums = {str(int(m.value)) if m.value == int(m.value) else str(m.value) for m in f.metrics}
                import re as _re
                _W2D = {"one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10"}
                for w, d in _W2D.items():
                    text = _re.sub(rf"\b{w}\b", d, text, flags=_re.I)
                for tok in _re.findall(r"\b\d+(?:\.\d+)?\b", text):
                    if not _re.match(r"^(19|20)\d{2}$", tok) and tok not in valid_nums:
                        text = _re.sub(rf"\b{tok}\b", "", text)
                text = _re.sub(r"(?<!\d)%|(?<!\d)\+", "", text)
                text = _re.sub(r"\s{2,}", " ", text).strip()
                b.text = text if ok and len(text) > 10 and "\u2014" not in text else f.text
            except Exception:
                b.text = f.text
    _save()
    errs = [r for r in validate_resume(out) if r.level == "ERROR"]
    if errs:
        for we in spec.sections.work:
            for i, b in enumerate(we.bullets):
                lbl = f"work/{we.experience_id}[{i}]"
                if any(lbl in e.message for e in errs) and b.source_fact_ids:
                    fid = b.source_fact_ids[0]
                    if fid in facts:
                        b.text = facts[fid].text
        _save()
    # summary (Problem 5) + skills section (Problem 4)
    try:
        bl = [b.text for we in spec.sections.work for b in we.bullets if b.text]
        su = (f"JD:\n{jd}\n\nKey achievements:\n" + "\n".join(f"- {b}" for b in bl[:5])
              + "\n\nWrite a 2-sentence summary positioning for the JD. No numbers. Output only summary.")
        spec.summary = _ollama_chat(model, "Write a tight professional summary.", su)
    except Exception: pass
    sel_sk = sorted({s for we in spec.sections.work for b in we.bullets
                     if b.source_fact_ids and b.source_fact_ids[0] in facts
                     for s in facts[b.source_fact_ids[0]].skills + facts[b.source_fact_ids[0]].tools})
    if sel_sk: spec.sections.skills = sel_sk
    _save()
    try: _gen_gap_report(spec, jd, facts, out)
    except Exception: pass
    return str(out)

_GAP_NOISE = set("advanced analysis assurance build clinical collaborate collaborative communication competitive computer design develop development diagnostics discovery degree background related familiar hybrid model models model ensure ensuring including experience following joined requirements seeking role team teams working years benefits package offer salary opportunity strong excellent shape field office engineer engineers engineering english german germany mainz munich science sciences scientists biontech bioinformatics biologists biomedical computational processes responsible reproducibility testing validation validating executable execute experiments frameworks guidance informatics lifecycle oracles perform pipelines profile pytest quality regulatory salary scale shape skills suites systems trace grader graders" .split())
def _gen_gap_report(spec, jd: str, facts, spec_path) -> None:
    """Write GAPS/TRANSFERABLE/STRENGTHS report alongside spec."""
    import re
    jw = _extract_jd_keywords(jd)
    sel_fids = {b.source_fact_ids[0] for we in spec.sections.work for b in we.bullets if b.source_fact_ids}
    sel_sk = {s.lower() for fid in sel_fids if fid in facts for s in facts[fid].skills + facts[fid].tools}
    all_sk = {s.lower() for f in facts.values() for s in f.skills + f.tools}
    # gaps: JD keywords not in any skill, filtered
    gaps = {w for w in jw - all_sk - _GAP_NOISE if len(w) > 5 and not w.isdigit() and w.isalpha()}
    trans = {w for w in (jw & all_sk) - sel_sk if len(w) > 3}
    strong = {w for w in jw & sel_sk if len(w) > 3}
    r = Path(str(spec_path).replace(".yaml", "_gaps.txt"))
    lines = ["GAPS (no supporting fact):"] + [f"  - {g}" for g in sorted(gaps)[:10]]
    lines += ["", "TRANSFERABLE (have skill, not selected):"] + [f"  - {t}" for t in sorted(trans)[:10]]
    lines += ["", "STRENGTHS (strong support):"] + [f"  - {s}" for s in sorted(strong)[:10]]
    r.write_text("\n".join(lines), encoding="utf-8")
def assembly_report(spec_path: str | Path, jd_path: str) -> dict:
    """JD matching report: selected, excluded, coverage, needs rephrasing."""
    from collections import Counter
    from .load import fact_quality
    jd_words = list(_extract_jd_keywords(Path(jd_path).read_text(encoding="utf-8")))
    freq = Counter(jd_words)
    facts = all_facts()
    spec = load_resume_spec(spec_path)
    sel_ids = spec.sections.fact_ids()
    scored = []
    for fid, f in facts.items():
        fw = set(f.text.lower().split()) | {w for s in f.skills + f.tools for w in s.lower().split()}
        rel = sum(1.0 / freq[w] for w in (set(freq) & fw) if freq[w] > 0)
        if f.metrics: rel += 2.0
        q = fact_quality(f)
        scored.append({"id": fid, "relevance": round(rel, 2), "quality_score": q["score"],
                       "detail": q["detail"], "has_metrics": q["has_metrics"], "kind": f.kind,
                       "text": f.text[:80].replace("\n", " "), "selected": fid in sel_ids,
                       "skills": f.skills, "tools": f.tools})
    scored.sort(key=lambda x: x["relevance"], reverse=True)
    selected = [s for s in scored if s["selected"]]
    sel_skills = {w.lower() for s in selected for w in s["skills"] + s["tools"]}
    jd_kw = set(freq)
    covered = {w for w in jd_kw if any(w in sk for sk in sel_skills)}
    weak = {"coordinated", "maintained", "responsible", "streamlined", "enabled", "assisted"}
    needs = [s for s in selected if s["quality_score"] < 0.6 or any(w in s["text"].lower() for w in weak)]
    return {"selected": selected, "excluded": [s for s in scored if not s["selected"]][:5],
            "gaps": sorted(jd_kw - covered)[:10], "coverage_pct": round(len(covered) / max(1, len(jd_kw)) * 100),
            "needs_rephrasing": needs}

_EXTRACT_SYS = ('Extract SEPARATE facts as JSON array. One fact per distinct achievement/project. Each: {"text":"prose WITHOUT numbers",'
    '"kind":"technical|leadership|project|achievement|research|responsibility",'
    '"skills":["..."],"tools":["..."],"metrics":[{"value":"N","unit":"...","context":"..."}]}. '
    'Numbers in metrics NEVER in text. Output ONLY JSON array.')
def extract_facts(text: str, model: str = "granite4.1:30b") -> list[dict]:
    """Extract structured facts from raw text via ollama (single-shot)."""
    import json, re
    resp = _ollama_chat(model, _EXTRACT_SYS, text)
    s, e = resp.find("["), resp.rfind("]") + 1
    if s < 0 or e <= 0: return []
    raw = re.sub(r',\s*([}\]])', r'\1', resp[s:e])
    try: return json.loads(raw)
    except json.JSONDecodeError:
        out = []
        for m in re.findall(r'\{[^{}]+\}', raw):
            try: out.append(json.loads(m))
            except Exception: pass
        return out
