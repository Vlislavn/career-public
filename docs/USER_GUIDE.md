# Setup and CLI reference

Technical companion to [README](../README.md#start-in-the-agent-chat). The coding agent executes these steps under [AGENTS.md](../AGENTS.md); canonical changes require explicit approval. Source materials may remain outside the repository.

## Install

Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/), package-index access and setup permission. From the repository root:

```bash
uv sync --python 3.12 --locked
uv run --locked career --help
```

Python 3.12–3.13 is supported. RenderCV, fonts and Python Typst are included; no separate system renderer is needed. `pdftotext` is optional. Ollama generation is not this workflow; ESCO is optional/advisory.

## Real candidate setup

Use a separate private copy. Never overwrite existing `data/` or seed real records with demo facts. With setup permission, only if `data/` is absent:

```bash
test ! -e data && cp -R examples/blank-data data
```

Propose profile edits in `data/profile/basics.yaml` and education/languages; obtain approval before saving. The null name intentionally fails validation. Education IDs: `edu_001`, etc.

Prepare `examples/experience-template.yaml` for review. Use a lowercase ID such as `first_role`, matching filename and `id`. Fill employer, title and quoted dates (`'2024-01'`); null end-date means ongoing. Keep `facts: []`. After metadata approval, save `data/experience/<id>.yaml` and validate. `career add` cannot create experiences. Do not draft real resumes until real facts exist.

## Fictional CLI example

In a fresh copy without `data/`:

```bash
test ! -e data && cp -R examples/data data
uv run --locked career validate
uv run --locked career facts
```

Stop if initialization fails; demo records are not candidate evidence. Stage an addition:

```bash
uv run --locked career add demo_ops --text 'Documented the fictional intake handoff for the sample team.' --skills 'Process improvement' --stage
uv run --locked career validate --staging
uv run --locked career quality --staging
```

Show **all** of `data/.staging/demo_ops.yaml` against `data/experience/demo_ops.yaml`; request explicit approval. Scores are advisory. Promotion appends every staged fact, not selected IDs or corrections. For partial approval, revise/revalidate/reconfirm first. Existing-record corrections need approved canonical diffs.

After exact-set approval, reread staging before promotion:

```bash
uv run --locked career promote demo_ops
uv run --locked career validate
```

## Later: fictional vacancy to PDF

```bash
uv run --locked career build --include demo_ops_001,demo_data_001 --output applications/demo/_work/resume.yaml
```

In the skeleton, set `name: demo`, `target.company: Fictional Lantern Works`, `target.role: Operations Analyst`; optionally select education `edu_001`. Empty bullet text uses canonical facts.

Follow [career-apply](../.agents/skills/career-apply/SKILL.md): review requirements/claims and save `gaps.md` with `GAPS`, `TRANSFERABLE`, `STRENGTHS` and supporting IDs. Then:

```bash
uv run --locked career validate
uv run --locked career validate-resume applications/demo/_work/resume.yaml
uv run --locked career report applications/demo/_work/resume.yaml examples/jd.txt
uv run --locked career render applications/demo/_work/resume.yaml
test -s generated/demo.pdf
```

Review PDF layout, text and claims; successful checks do not establish factual support. Copy the reviewed PDF to `applications/demo/`. No automatic submission.

## Contributor checks

Use isolated fictional data, never overwrite personal records:

```bash
uv run --locked career validate
uv run --locked --extra dev pytest tests/
```
