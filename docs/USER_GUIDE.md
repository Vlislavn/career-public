# User guide

Use this guide from a fresh checkout. For evidence and approval rules, start at [AGENTS.md](../AGENTS.md); for a full JD application, follow its career-apply skill link.

## Fictional demo

First follow [README installation](../README.md#install) (`uv sync --python 3.12 --locked` installs RenderCV, fonts and Python Typst with the project). No separate system Typst or RenderCV CLI install is needed. Then, in the repository root:

```bash
uv run career validate
uv run career facts
uv run career match examples/jd.txt
```

The example data models Test Person at fictional organizations; its `example.com` email and reserved 555-0100 telephone are non-contactable placeholders. Never treat demo facts as real candidate evidence.

## Real candidate setup

Use a **separate local checkout** with no demo `data/`. Copy the blank skeleton once, then replace the null name (blank values intentionally fail validation):

```bash
cp -R examples/blank-data data
# edit data/profile/basics.yaml: replace null with the person's actual name
# optional: replace {} in education.yaml with entries: [{id: edu_001, institution: ..., degree: ..., start_date: '2020'}]
uv run career validate
```

To add an experience, copy `examples/experience-template.yaml` to `data/experience/<id>.yaml` (create the directory). Use a lowercase ID of letters, digits, and single underscores (for example, `first_role`, **not** `first-role`); set `id` to the filename stem. Fill `organization`, `title`, and **quoted** `start_date` (`'2024'` or `'2024-01'`); `end_date: null` may remain if ongoing. Leave `facts: []`. After human review of this metadata, run `uv run career validate`; only then `uv run career add <id> --text '...' --stage` and `uv run career validate --staging`. Inspect the staged additions against canonical data, obtain explicit approval, promote the reviewed facts, then validate again. **Do not** start a real application until actual supported facts exist. No CLI command creates new experience metadata, and CLI success does not prove user approval. Never seed a real profile by copying demo data. `data/` is ignored but can be force-added; never commit or publish it.

## Propose a fact, then wait for approval

The example below adds a *synthetic* proposed fact, not a real claim:

```bash
uv run career add demo_ops --text 'Documented the fictional intake handoff for the sample team.' --skills 'Process improvement' --stage
uv run career validate --staging
diff -u /dev/null data/.staging/demo_ops.yaml || test "$?" -eq 1
```

`diff` exits 1 for ordinary differences. Staging contains **only proposed facts**, not a full replacement of the canonical file; compare each proposed fact to `data/experience/demo_ops.yaml`. Review the **entire** staged file with the owner; **do not promote merely because validation passed**. `promote` appends all staged facts, not selected IDs. Immediately before promotion re-read the full staged file and confirm it matches the approved set. If only some facts were approved, prepare and revalidate an approved-only proposal and show the revised diff first. Only then run `uv run career promote demo_ops` and `uv run career validate`. Unapproved staging is never resume evidence. Do not auto-commit.

## From a JD to a PDF

The CLI assembles a *skeleton*; an agent or author chooses relevant canonical facts and writes grounded bullets. Run the following with the fictional sample:

```bash
uv run career facts
uv run career match examples/jd.txt
uv run career build --include demo_ops_001,demo_data_001 --output applications/demo/_work/resume.yaml
```

Edit `applications/demo/_work/resume.yaml`: set `name: demo`, `target.company: Fictional Lantern Works`, and `target.role: Operations Analyst`; optionally select `edu_001` under `sections.education`. The empty `bullet.text` fields render the canonical fact text; if rewriting, keep its `source_fact_ids` and every numeric claim's metric. Review the JD against every fact; do not treat `match` as proof of semantic fit. Record unsupported requirements as `GAPS`, partial fit with fact IDs as `TRANSFERABLE`, and direct support with fact IDs as `STRENGTHS`. For a real JD, follow [AGENTS.md](../AGENTS.md) → career-apply for the complete evidence review.

```bash
uv run career validate
uv run career validate-resume applications/demo/_work/resume.yaml
uv run career report applications/demo/_work/resume.yaml examples/jd.txt
uv run career render applications/demo/_work/resume.yaml
```

The renderer prints the produced path (`generated/demo.pdf`). Inspect the PDF visually and check its text and claims before sharing it. `applications/`, `generated/`, and `data/` are ignored locally; inspect the complete staged file list before any public release. A private sync script is maintained separately and is not shipped here. This repository has no private history; its initial commit requires human review. Do not import personal history or documents.
