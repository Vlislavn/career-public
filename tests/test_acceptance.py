"""Acceptance tests (§22)."""
import json
import yaml
from pathlib import Path

import pytest
import sys
import career_source.load as loadmod
from career_source import (
    load_profile, load_facts, validate, validate_resume, export_context,
)
from career_source.load import export_profile, fact_quality
from career_source.render import _pick_template, _to_rendercv
from career_source.resume import build_all, load_resume_spec
from career_source.models import Fact, ResumeSpec


def _get_module(name):
    return sys.modules[name]


def _patch_data(monkeypatch, tmp_career):
    """Point all modules at the test data dir."""
    d = tmp_career / "data"
    monkeypatch.setattr(loadmod, "DATA_DIR", d)
    # validate.py and validate_resume.py read DATA_DIR via _load.DATA_DIR at runtime
    # clear lru_cache so loaders re-read
    from career_source.normalize import load_aliases, _reverse_map
    load_aliases.cache_clear()
    _reverse_map.cache_clear()


class TestCanonicalData:
    """§22 acceptance tests 1, 7, 9, 10."""

    def test_validate_clean(self, tmp_career, monkeypatch):
        """career validate passes on well-formed data."""
        _patch_data(monkeypatch, tmp_career)
        results = validate()
        errors = [r for r in results if r.level == "ERROR"]
        assert not errors, f"unexpected errors: {[r.message for r in errors]}"

    def test_no_llm_in_repo(self):
        """§22.9: no openai/anthropic/api_key/langchain in src/."""
        src = Path(__file__).resolve().parent.parent / "src"
        forbidden = ["openai", "anthropic", "api_key", "langchain"]
        for py in src.rglob("*.py"):
            text = py.read_text().lower()
            for word in forbidden:
                assert word not in text, f"'{word}' found in {py}"

    def test_skill_tool_overlap_detected(self, tmp_career, monkeypatch):
        """Validator must catch a skill that appears in both skills and tools."""
        _patch_data(monkeypatch, tmp_career)
        # Add a fact where Python is in BOTH skills and tools
        import yaml as _yaml
        exp_path = tmp_career / "data" / "experience" / "helix.yaml"
        exp = _yaml.safe_load(exp_path.read_text())
        exp["facts"][0]["skills"].append("Python")  # Python is already in tools
        exp_path.write_text(_yaml.safe_dump(exp))
        results = validate()
        errors = [r for r in results if r.level == "ERROR"]
        assert any("overlap" in r.message for r in errors), \
            f"expected skill/tool overlap error, got: {[r.message for r in errors]}"

    def test_loc_budget(self):
        """§22.10: src/ ≤ 1600 LOC, ≤ 8 modules."""
        src = Path(__file__).resolve().parent.parent / "src" / "career_source"
        total = sum(
            len(f.read_text().splitlines())
            for f in src.glob("*.py")
            if f.name != "__init__.py"
        )
        modules = len(list(src.glob("*.py"))) - 1  # minus __init__
        assert total <= 1600, f"src/ is {total} LOC (limit 1600)"
        assert modules <= 8, f"{modules} modules (limit 8)"

    def test_publication_quality_does_not_require_metrics_or_tools(self):
        fact = Fact(id="pub_001", kind="publication", text="Published a detailed peer-reviewed clinical research paper documenting oncology methods and patient outcomes clearly.", skills=["medical oncology"])
        quality = fact_quality(fact)
        assert quality["score"] == .6
        assert quality["issues"] == ["source unknown", "unverified"]


class TestResumeValidation:
    """§22 acceptance tests 2, 4, 6."""

    def test_valid_resume_passes(self, tmp_career, monkeypatch, helix_resume):
        """§22.2: every bullet has valid provenance."""
        _patch_data(monkeypatch, tmp_career)
        spec_path = tmp_career / "resume.yaml"
        spec_path.write_text(yaml.safe_dump(helix_resume))
        results = validate_resume(spec_path)
        errors = [r for r in results if r.level == "ERROR"]
        assert not errors, f"unexpected errors: {[r.message for r in errors]}"

    def test_fabricated_metric_fails(self, tmp_career, monkeypatch, fabricated_resume):
        """§22.6: a resume with an invented metric ('99%') fails validation."""
        _patch_data(monkeypatch, tmp_career)
        spec_path = tmp_career / "fab.yaml"
        spec_path.write_text(yaml.safe_dump(fabricated_resume))
        results = validate_resume(spec_path)
        errors = [r for r in results if r.level == "ERROR"]
        assert any("99" in r.message for r in errors), \
            f"expected number-provenance error for '99', got: {[r.message for r in errors]}"

    def test_unsupported_requirement_stays_gap(self, tmp_career, monkeypatch):
        """§22.4: a JD demanding 'Go' gets no Go bullet (no Go facts exist)."""
        _patch_data(monkeypatch, tmp_career)
        spec = {
            "schema_version": 1,
            "name": "go_test",
            "target": {"company": "X", "role": "Go Developer"},
            "sections": {
                "work": [{
                    "experience_id": "helix",
                    "bullets": [{
                        "text": "Built services with Go.",
                        "source_fact_ids": ["hx_001"],
                    }],
                }],
            },
        }
        spec_path = tmp_career / "go.yaml"
        spec_path.write_text(yaml.safe_dump(spec))
        results = validate_resume(spec_path)
        errors = [r for r in results if r.level == "ERROR"]
        assert any("Go" in r.message for r in errors), \
            f"expected entity-presence error for 'Go', got: {[r.message for r in errors]}"


class TestContextExport:
    """§22 acceptance test 1 (same master data serves different JDs)."""

    def test_context_has_schema_version(self, tmp_career, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        ctx = export_context()
        assert ctx["schema_version"] == 1
        assert "profile" in ctx
        assert "experiences" in ctx
        assert "facts" in ctx

    def test_context_skill_filter(self, tmp_career, monkeypatch):
        """Filtering by skill narrows facts."""
        _patch_data(monkeypatch, tmp_career)
        ctx_all = export_context()
        ctx_py = export_context(skill="Python")
        assert len(ctx_py["facts"]) <= len(ctx_all["facts"])
        assert len(ctx_py["facts"]) > 0


class TestExportProfile:
    """Structured candidate profile export (merged-skills consumer-compatible)."""

    def test_profile_has_required_fields(self, tmp_career, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        prof = export_profile()
        for key in ("name", "skills", "tools", "domains", "seniority",
                    "years_experience", "education", "education_level",
                    "target_roles", "languages", "magnets", "repellents",
                    "locations", "experience", "summary"):
            assert key in prof, f"missing field: {key}"
        assert prof["name"] == "Test Person"
        assert isinstance(prof["skills"], list)
        assert len(prof["skills"]) > 0
        # skills and tools must be separate (no overlap)
        assert not (set(prof["skills"]) & set(prof["tools"])), \
            "skills/tools overlap detected"

    def test_profile_seniority_from_latest_role(self, tmp_career, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        prof = export_profile()
        # vectorstack title is "ML Engineer" → no senior/lead keyword → mid
        assert prof["seniority"] == "mid"

    def test_merged_skills_schema_complete(self, tmp_career, monkeypatch):
        """Merged-skills export has exactly the fields downstream consumer expects."""
        _patch_data(monkeypatch, tmp_career)
        prof = export_profile(merged_skills=True)
        required = {"skills", "experience", "domains", "seniority",
                    "years_experience", "education", "education_level",
                    "languages", "target_roles", "locations",
                    "magnets", "repellents", "summary"}
        missing = required - set(prof.keys())
        assert not missing, f"Merged-skills schema missing: {missing}"
        # skills+tools merged in Merged-skills mode
        assert "tools" not in prof
        assert isinstance(prof["skills"], list)
        assert isinstance(prof["languages"], dict)
        assert isinstance(prof["experience"], str)
        assert len(prof["experience"]) > 0


class TestTemplateSelection:
    """Role-based RenderCV theme auto-selection."""

    def test_product_role_gets_classic(self):
        assert _pick_template("Product Lead") == "classic"

    def test_engineer_role_gets_engineeringresumes(self):
        assert _pick_template("Senior Software Engineer") == "engineeringresumes"

    def test_design_role_gets_sb2nov(self):
        assert _pick_template("UX Designer") == "sb2nov"

    def test_unknown_role_falls_back(self):
        assert _pick_template("Astronaut") == "engineeringresumes"

    def test_tailored_resume_defaults_to_a4(self, tmp_career, monkeypatch, helix_resume):
        _patch_data(monkeypatch, tmp_career)
        assert _to_rendercv(ResumeSpec(**helix_resume))["design"]["page"]["size"] == "a4"

    def test_profile_photo_and_socials_are_global(self, tmp_career, helix_resume, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        output = _to_rendercv(ResumeSpec(**helix_resume))
        assert output["cv"]["photo"] == str(tmp_career / "data/profile/photo.png")
        assert {x["network"]: x["username"] for x in output["cv"]["social_networks"]} == {
            "LinkedIn": "test-person", "GitHub": "test-person"}
        assert output["design"]["header"] == {"photo_width": "2.7cm", "photo_position": "right"}

    def test_year_only_dates_keep_year_precision(self, tmp_career, helix_resume, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        education = _to_rendercv(ResumeSpec(**helix_resume))["cv"]["sections"]["education"][0]
        assert education["start_date"] == 2018
        assert education["end_date"] == 2022

    def test_tailored_publications_are_selected(self, tmp_career, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        spec = ResumeSpec(schema_version=1, name="tailored", target={"company": "X", "role": "Y"},
                          sections={"publications": [{"fact_id": "hx_002"}]})
        assert "Selected Publications" in _to_rendercv(spec)["cv"]["sections"]

    def test_project_name_links_to_url(self, tmp_career, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        spec = ResumeSpec(schema_version=1, name="tailored", target={"company": "X", "role": "Y"},
                          sections={"projects": [{"name": "Project", "url": "https://example.com",
                                                  "bullets": [{"text": "Built it.", "source_fact_ids": ["hx_001"]}]}]})
        assert _to_rendercv(spec)["cv"]["sections"]["projects"][0]["name"] == "[Project](https://example.com)"

    def test_master_is_complete_and_breakable(self, tmp_career, monkeypatch):
        _patch_data(monkeypatch, tmp_career)
        path = build_all(tmp_career / "master.yaml")
        spec = load_resume_spec(path)
        selected = {fid for w in spec.sections.work for b in w.bullets for fid in b.source_fact_ids}
        selected |= {fid for p in spec.sections.projects for b in p.bullets for fid in b.source_fact_ids}
        selected |= {p.fact_id for p in spec.sections.publications}
        assert selected == set(loadmod.all_facts())
        assert all(p.fact_id not in {fid for w in spec.sections.work for b in w.bullets for fid in b.source_fact_ids} for p in spec.sections.publications)
        output = _to_rendercv(spec)
        assert output["design"]["page"]["size"] == "a4"
        assert output["design"]["entries"]["allow_page_break"] is True
        assert [x["label"] for x in output["cv"]["sections"]["skills"]] == [
            "Hard - Clinical & quality", "Hard - AI, data & engineering",
            "Hard - Research & evaluation", "Soft - Leadership & collaboration", "Tools & technologies"]
        assert output["cv"]["sections"]["education"][0]["degree"] == ""
        assert "publications" in output["cv"]["sections"]
