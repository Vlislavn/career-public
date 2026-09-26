import importlib
import subprocess
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from career_source.cli import app
from career_source.models import Fact, ResumeSpec
from career_source.resume import assembly_report, build_include, load_resume_spec
from career_source.validate import validate
from career_source.validate_resume import validate_resume

load = importlib.import_module("career_source.load")
render = importlib.import_module("career_source.render")


@pytest.fixture(autouse=True)
def isolated(tmp_career, monkeypatch):
    from career_source.normalize import load_aliases, _reverse_map
    monkeypatch.setattr(load, "DATA_DIR", tmp_career / "data")
    monkeypatch.setattr(render, "GENERATED_DIR", tmp_career / "generated")
    load_aliases.cache_clear()
    _reverse_map.cache_clear()
    yield
    load_aliases.cache_clear()
    _reverse_map.cache_clear()


def write_yaml(path, value):
    path.write_text(yaml.safe_dump(value), encoding="utf-8")
    return path


def stage(tmp_career, fact):
    data = yaml.safe_load((tmp_career / "data/experience/helix.yaml").read_text())
    return write_yaml(tmp_career / "data/.staging/helix.yaml", {**data, "facts": [fact]})


@pytest.mark.parametrize("fact", [
    {"id": "hx_001", "kind": "technical", "text": "Corrected proposal."},
    {"id": "vs_001", "kind": "technical", "text": "Cross-experience collision."},
    {"id": "hx_003", "kind": "invalid", "text": "Invalid proposal."},
])
def test_promotion_rejects_without_losing_proposal(tmp_career, fact):
    proposal = stage(tmp_career, fact)
    canon = tmp_career / "data/experience/helix.yaml"
    before = (canon.read_bytes(), proposal.read_bytes())
    result = CliRunner().invoke(app, ["promote", "helix"])
    assert result.exit_code != 0
    assert (canon.read_bytes(), proposal.read_bytes()) == before


@pytest.mark.parametrize("exp_id", ["my-job", "my__job", "my_"])
def test_invalid_experience_id_fails_before_first_fact(tmp_career, exp_id):
    path = write_yaml(tmp_career / f"data/experience/{exp_id}.yaml", {
        "id": exp_id, "organization": "Fictional Company", "title": "Analyst",
        "start_date": "2022-01", "facts": [],
    })
    before = path.read_bytes()
    assert any(r.level == "ERROR" for r in validate())
    with pytest.raises(ValueError, match="invalid experience ID"):
        load.add_fact(exp_id, "Documented a fictional intake handoff.", stage=True)
    assert path.read_bytes() == before


def test_first_fact_ids_for_similar_new_experiences_do_not_collide(tmp_career):
    for exp_id in ("delta_a", "delta_b"):
        write_yaml(tmp_career / f"data/experience/{exp_id}.yaml", {
            "id": exp_id, "organization": "Fictional Company", "title": "Analyst",
            "start_date": "2022-01", "facts": [],
        })
    first = load.add_fact("delta_a", "Documented an intake handoff for the sample team.")
    second = load.add_fact("delta_b", "Reviewed a distinct process for a separate team.")
    assert (first, second) == ("delta_a_001", "delta_b_001")
    assert {first, second} <= load.all_facts().keys()


def test_failed_atomic_promotion_preserves_both_files(tmp_career, monkeypatch):
    proposal = stage(tmp_career, {"id": "hx_003", "kind": "technical", "text": "Valid proposal."})
    canon = tmp_career / "data/experience/helix.yaml"
    before = canon.read_bytes()
    def fail_replace(*args, **kwargs):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError):
        load.promote_staging("helix")
    assert canon.read_bytes() == before and proposal.exists()


def test_valid_promotion_counts_only_new_facts(tmp_career):
    proposal = stage(tmp_career, {"id": "hx_003", "kind": "technical", "text": "Valid proposal."})
    assert load.promote_staging("helix") == 1
    assert not proposal.exists()
    assert {"hx_001", "hx_002", "hx_003"} <= load.all_facts().keys()


@pytest.mark.parametrize("extra", [["--kind", "invalid"], ["--metrics", "not-a-metric"],
                                  ["--skills", "Python", "--tools", "Python"]])
@pytest.mark.parametrize("staging", [False, True])
def test_bad_add_leaves_storage_unchanged(tmp_career, extra, staging):
    paths = sorted((tmp_career / "data").rglob("*.yaml"))
    before = {p: p.read_bytes() for p in paths}
    result = CliRunner().invoke(app, ["add", "helix", "--text", "Reviewed incidents."] +
                                (["--stage"] if staging else []) + extra)
    assert result.exit_code != 0
    assert {p: p.read_bytes() for p in (tmp_career / "data").rglob("*.yaml")} == before


@pytest.mark.parametrize("staging", [False, True])
def test_validate_rejects_unprovenanced_fact_numbers(tmp_career, staging):
    fact = {"id": "hx_003", "kind": "technical", "text": "Improved throughput by 77 percent."}
    path = stage(tmp_career, fact)
    if not staging:
        canon = tmp_career / "data/experience/helix.yaml"
        data = yaml.safe_load(canon.read_text())
        data["facts"].append(fact)
        write_yaml(canon, data)
    assert any(r.level == "ERROR" for r in validate(staging=staging))


@pytest.mark.parametrize("text", ["Added 9.9% while saving 40%.", "Saved -40%.",
                                  "Saved 40 hours.", "Saved 40% and 4000 records.",
                                  "Saved 40% and 2025 records.", "Used version 9.9% and saved 40%."])
def test_number_fabrications_fail(tmp_career, helix_resume, text):
    helix_resume["sections"]["work"][0]["bullets"][0]["text"] = text
    path = write_yaml(tmp_career / "spec.yaml", helix_resume)
    assert any(r.level == "ERROR" for r in validate_resume(path))


@pytest.mark.parametrize("text", ["Used version 3.12 in 2024.", "Used v3.12.", "Certificate No. 7842169, 14 Mar 2023.",
    "Published in Fictional Journal. 2023;17(4):31–39. doi:10.9999/fictional.000123."])
def test_nonmetric_identifiers_remain_supported(text):
    assert Fact(id="hx_003", kind="technical", text=text).text == text


def test_decimal_and_signed_metrics_are_supported(tmp_career, helix_resume):
    path = tmp_career / "data/experience/helix.yaml"
    exp = yaml.safe_load(path.read_text())
    exp["facts"][0]["metrics"] = [{"value": -9.9, "unit": "%"}]
    write_yaml(path, exp)
    helix_resume["sections"]["work"][0]["bullets"][0]["text"] = "Observed a -9.9% change."
    assert not [r for r in validate_resume(write_yaml(tmp_career / "spec.yaml", helix_resume)) if r.level == "ERROR"]


def test_unknown_selection_does_not_write(tmp_career):
    output = tmp_career / "spec.yaml"
    with pytest.raises(ValueError):
        build_include(["missing_999"], output)
    assert not output.exists()


def project_spec():
    return ResumeSpec(name="test", target={"company": "Test", "role": "Engineer"}, sections={
        "projects": [{"name": "QA Project", "bullets": [{"source_fact_ids": ["hx_001"]}]}],
        "publications": [{"fact_id": "hx_002"}]})


def test_report_counts_projects_and_publications(tmp_career):
    path = write_yaml(tmp_career / "spec.yaml", project_spec().model_dump())
    jd = tmp_career / "jd.txt"
    jd.write_text("Python RCA")
    report = assembly_report(path, str(jd))
    assert {s["id"] for s in report["selected"]} == {"hx_001", "hx_002"}
    assert report["coverage_pct"] == 100


def test_render_includes_project_verbatim_and_languages():
    sections = render._to_rendercv(project_spec())["cv"]["sections"]
    assert sections["projects"][0]["highlights"] == [load.all_facts()["hx_001"].text]
    assert "C1" in str(sections["languages"]) and "A2" in str(sections["languages"])


@pytest.mark.parametrize("theme", ["classic", "engineeringresumes", "sb2nov"])
@pytest.mark.parametrize("start,end", [("2024-11", "2026"), ("2017-02", "2019-07"), ("2023-05", None)])
def test_render_preserves_dates_without_inferred_tenure(tmp_career, helix_resume, theme, start, end):
    path = tmp_career / "data/experience/helix.yaml"
    exp = yaml.safe_load(path.read_text())
    exp.update(start_date=start, end_date=end)
    write_yaml(path, exp)
    helix_resume["design"] = {"template": theme}
    output = render._to_rendercv(ResumeSpec(**helix_resume))
    entry = output["cv"]["sections"]["experience"][0]
    assert entry["start_date"] == start
    assert entry.get("end_date") == (int(end) if end and len(end) == 4 else end)
    assert output["design"].get("sections", {}).get("show_time_spans_in") == []


def test_fabricated_title_is_rejected(tmp_career, helix_resume):
    helix_resume["sections"]["work"][0]["title"] = "Chief Executive Officer"
    path = write_yaml(tmp_career / "spec.yaml", helix_resume)
    assert any(r.level == "ERROR" for r in validate_resume(path))


def test_render_rejects_invalid_spec_before_subprocess(tmp_career, fabricated_resume, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("renderer must not run for invalid claims")
    monkeypatch.setattr(render.subprocess, "run", unexpected)
    with pytest.raises(ValueError):
        render.render(write_yaml(tmp_career / "bad.yaml", fabricated_resume))


@pytest.mark.parametrize("command", ["tailor", "polish"])
def test_cli_wrappers_fail_when_render_fails(tmp_career, helix_resume, monkeypatch, command):
    cli = importlib.import_module("career_source.cli")
    spec = write_yaml(tmp_career / "spec.yaml", helix_resume)
    jd = tmp_career / "jd.txt"
    jd.write_text("QA Engineer Python")
    def fail_render(*args, **kwargs):
        raise RuntimeError("no PDF")
    monkeypatch.setattr(cli, "_render_fn", fail_render)
    monkeypatch.setattr(cli, "_polish_jd", lambda *args, **kwargs: str(spec))
    args = ["tailor", str(jd), "--output", str(spec)] if command == "tailor" else ["polish", str(spec), "--jd", str(jd)]
    assert CliRunner().invoke(app, args).exit_code != 0


@pytest.mark.parametrize("mode", ["missing", "empty", "failed"])
def test_render_failure_preserves_existing_pdf(tmp_career, helix_resume, monkeypatch, mode):
    render.GENERATED_DIR.mkdir()
    previous = render.GENERATED_DIR / "helix_qa.pdf"
    previous.write_bytes(b"previous output")
    def fake_run(cmd, **kwargs):
        if mode == "empty":
            (Path(cmd[cmd.index("--output-folder") + 1]) / "empty.pdf").touch()
        return subprocess.CompletedProcess(cmd, 1 if mode == "failed" else 0, "", "failed")
    monkeypatch.setattr(render.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        render.render(write_yaml(tmp_career / "spec.yaml", helix_resume))
    assert previous.read_bytes() == b"previous output"


def test_render_success_uses_current_run_only(tmp_career, helix_resume, monkeypatch):
    render.GENERATED_DIR.mkdir()
    unrelated = render.GENERATED_DIR / "Test_Person_CV.pdf"
    unrelated.write_bytes(b"stale output")
    def fake_run(cmd, **kwargs):
        out = Path(cmd[cmd.index("--output-folder") + 1])
        assert out != render.GENERATED_DIR
        (out / "Test_Person_CV.pdf").write_bytes(b"fresh output")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(render.subprocess, "run", fake_run)
    pdf = render.render(write_yaml(tmp_career / "spec.yaml", helix_resume))
    assert pdf.read_bytes() == b"fresh output"
    assert unrelated.read_bytes() == b"stale output"


def test_stage_to_real_pdf(tmp_career):
    import shutil
    if not shutil.which("pdftotext"):
        pytest.skip("PDF parse-back requires pdftotext")
    basics_path = tmp_career / "data/profile/basics.yaml"
    basics = yaml.safe_load(basics_path.read_text())
    basics.update(photo="", phone="+1-202-555-0123")
    write_yaml(basics_path, basics)
    runner = CliRunner()
    add = runner.invoke(app, ["add", "helix", "--stage", "--text", "Reduced QA effort by 12%.",
                             "--metrics", "12:%:QA effort", "--skills", "RCA", "--tools", "Python"])
    assert add.exit_code == 0, add.output
    assert runner.invoke(app, ["validate", "--staging"]).exit_code == 0
    assert runner.invoke(app, ["promote", "helix"]).exit_code == 0
    output = build_include(["hx_003"], tmp_career / "spec.yaml")
    spec = load_resume_spec(output)
    spec.name = "flow-smoke"
    spec.sections.projects = project_spec().sections.projects
    spec.sections.publications = project_spec().sections.publications
    write_yaml(output, spec.model_dump())
    assert not [r for r in validate_resume(output) if r.level == "ERROR"]
    pdf = render.render(output)
    parsed = subprocess.run(["pdftotext", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    assert all(value in parsed for value in ["Test Person", "Helix Diagnostics", "12%", "QA Project", "C1", "A2"])
    assert load.all_facts()["hx_001"].text in " ".join(parsed.split())
    print(f"Verified PDF: {pdf}")
