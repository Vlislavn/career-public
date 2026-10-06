# User guide

## Continue in the agent chat

Start with [the README](../README.md#start-in-the-agent-chat). Use an external coding agent that can open your **private local copy** of this project and run its terminal commands. Ask it to read [AGENTS.md](../AGENTS.md). Ordinary chat without repository and terminal access cannot execute this workflow.

No job description is needed to build your career record. Send relevant notes or files in batches: an old resume, project notes, or your own account can help propose facts, but are **not approved truth** or direct evidence for a final resume.

```text
Materials → clarify one experience → review complete proposal → approve
                                                          → reusable facts
Later: job description + approved facts → tailored resume + gaps + PDF
```

The agent should clarify one experience at a time: its context, what you personally did versus the team, tools actually used, outcomes, and the evidence behind numbers. Unknown details stay unknown. Improving clarity must not invent responsibilities or results; a quality score is advisory, not proof.

Before anything becomes canonical, the agent shows an understandable review of **all new and changed information**, alongside existing facts: proposed identity/experience metadata, fact IDs, wording, metrics, skills, tools, and unresolved questions. The exact raw proposals must accompany the review (full YAML files for additions; before/after canonical diffs for corrections). Approve only what is accurate. Metadata and canonical changes require explicit approval **before writing** them. Staging may hold unapproved new-fact proposals; it is not canonical truth.

If you approve only part of a proposal, the agent must show a revised approved-only set for confirmation. Existing fact corrections require an approved before/after canonical diff, not a duplicate staged fact or promotion. The agent automatically reports what was added or changed and what remains unclear, even if nothing was approved. You can always ask:

> Show all proposed facts, changes, and unresolved questions. Do not save them as approved records yet.

The interview and refinement happen in the external agent conversation, not in a built-in CLI interview or generic file-upload importer. After your permission, the agent handles setup and commands. If repository access or tooling is missing, it should explain the smallest manual step needed (for example, opening the private project in a coding agent or installing `uv`), rather than claiming it saved facts.

### Keep source material private

Use a separate private local copy, never the shared public tree for real candidate records. Redact employer and third-party confidential information before sharing. Attachments may be processed by your external agent provider; check its privacy settings and your permission to disclose the material.

Source files can stay outside the repository or, after initializing the blank profile, optionally under ignored `data/inbox/` in the private workspace. Do not create `data/inbox/` before initialization; setup must never overwrite an existing `data/`. No raw archive is required; never automatically delete originals. Ignored files are **not confidential by default** and can be force-added to Git. Do not publish personal records, source inputs, applications, generated PDFs, or private Git history. Review files and reachable history before any public release. There is no automatic commit, publication, or application submission.

## Technical reference — for the agent or hands-on author

Run commands from the repository root. [AGENTS.md](../AGENTS.md) owns evidence and approval rules. For later JD tailoring, use the existing [career-apply skill](../.agents/skills/career-apply/SKILL.md) and its [workflow](../.agents/skills/career-apply/references/workflow.md), [evidence policy](../.agents/skills/career-apply/references/evidence-policy.md), and [quality gates](../.agents/skills/career-apply/references/quality-gates.md).

## Install

With the user's permission, install [uv](https://docs.astral.sh/uv/getting-started/installation/) if unavailable, then run the commands below. Initial setup needs access to the Python package index. The project supports Python 3.12–3.13; this command selects 3.12 even if the system Python is newer.

```bash
uv sync --python 3.12 --locked
uv run --locked career --help
```

The locked dependencies include `rendercv[full]`, fonts, and Python Typst. No separate system Typst or RenderCV CLI installation is needed. `pdftotext` is optional for PDF text inspection, not required to render. Do not run local generative commands (`career extract`, `career polish`, or Ollama-backed matching) for agent intake or application writing.

## Real candidate setup

Use a **separate private local copy**, without demo data. Never overwrite an existing `data/`: inspect it and continue from its records instead. Only when `data/` does not exist, and after setup permission:

```bash
test ! -e data && cp -R examples/blank-data data
```

The blank skeleton has a null profile name and intentionally fails validation until completed. Propose truthful edits to `data/profile/basics.yaml` and any education/languages; show their exact diff and obtain approval before saving canonical profile changes. Education IDs use `edu_001`, `edu_002`, etc.

For each experience, prepare metadata from `examples/experience-template.yaml` for review **outside canonical data first**. Show the proposed path `data/experience/<id>.yaml` and complete contents. The ID starts with a lowercase letter and uses lowercase letters, digits, and single underscores, with no trailing underscore; set `id` equal to the filename stem (for example, `first_role`). Fill truthful `organization`, `title`, and quoted dates such as `'2024'` or `'2024-01'`; `end_date: null` means ongoing. Leave `facts: []`.

Only after explicit metadata approval, create `data/experience/` if needed and save the approved file. Then:

```bash
uv run --locked career validate
```

`career add` requires existing experience metadata; it cannot create it. Propose new facts through staging and approval as below. Canonical experience truth lives only in `data/experience/*.yaml`; profile truth lives in `data/profile/*.yaml`. Stop before a real application if the profile is a placeholder or no supported canonical facts exist. Never seed a real profile with fictional demo data.

## Fictional demo: initialize, propose, review

Use a fresh checkout with **no existing `data/`** after installation:

```bash
test ! -e data && cp -R examples/data data
uv run --locked career validate
uv run --locked career facts
```

If the copy guard fails, stop; do not overwrite or mix records. The sample describes Test Person at fictional organizations with non-contactable placeholders. These are demonstration facts, never evidence about a real person.

Propose one additional **synthetic** fact:

```bash
uv run --locked career add demo_ops --text 'Documented the fictional intake handoff for the sample team.' --skills 'Process improvement' --stage
uv run --locked career validate --staging
uv run --locked career quality --staging
cat data/experience/demo_ops.yaml
cat data/.staging/demo_ops.yaml
```

Always pass `--stage`: omitting it writes directly to canonical data. The agent must show the entire staging file against existing canonical facts, including every proposed ID, metric, skill, and tool, plus ambiguities. Staging contains additions, not a replacement experience file. Each quantity in factual text needs a matching metric value, unit, and context. Skills are practices; tools are software/hardware; do not list an item in both. Optional source references must not be fabricated.

Validation, quality scores, overlap warnings, and silence do not establish approval. Ask for explicit approval of the **whole proposed set**. Promotion appends **all facts** in that experience's staging file; it does not edit existing facts or select a subset. For partial approval, prepare an approved-only proposal, revalidate it, and show the revised complete set for confirmation. For corrections, show the canonical before/after diff and obtain approval before applying it directly; preserve established fact IDs.

### Only after explicit approval

Immediately before promotion, re-read the complete staging file and confirm it exactly matches the approved set. This is a separate step, not part of the proposal commands:

```bash
cat data/.staging/demo_ops.yaml
# Proceed only when every staged fact matches the explicitly approved set.
uv run --locked career promote demo_ops
uv run --locked career validate
```

Report the outcome automatically, including pending corrections or approvals:

```text
Added: N facts, N metrics, N technologies, N leadership items
Missing: unresolved quantity/date/source (fact ID if applicable)
```

## Later: fictional JD to PDF

Intake does not require a JD. When tailoring later, the agent maps every requirement to direct support, bounded transferable experience, or a gap using canonical fact IDs. Ask about material unsupported experience before drafting; any new facts still need the intake approval gate. Neither the JD nor an old resume supplies approved candidate truth.

With the initialized fictional demo:

```bash
uv run --locked career facts
uv run --locked career match examples/jd.txt
uv run --locked career build --include demo_ops_001,demo_data_001 --output applications/demo/_work/resume.yaml
```

Edit the skeleton at `applications/demo/_work/resume.yaml`: set `name: demo`, `target.company: Fictional Lantern Works`, and `target.role: Operations Analyst`. Optionally select `edu_001` under `sections.education`. Empty `bullet.text` fields use canonical fact text; rewritten bullets must retain `source_fact_ids` and trace every number to metrics in those facts. Manually verify the summary and project names too.

Save a mandatory evidence/gap note, for example `applications/demo/_work/gaps.md`, with:

```text
GAPS: unsupported JD requirements
TRANSFERABLE: bounded adjacent experience ← supporting fact IDs
STRENGTHS: direct support ← supporting fact IDs
```

Review every JD requirement and selected claim; `match` and `report` measure lexical coverage, not qualification or factual support. Then:

```bash
uv run --locked career validate
uv run --locked career validate-resume applications/demo/_work/resume.yaml
uv run --locked career report applications/demo/_work/resume.yaml examples/jd.txt
uv run --locked career render applications/demo/_work/resume.yaml
test -s generated/demo.pdf
```

The renderer prints `generated/demo.pdf` when the spec name is `demo`. Inspect it visually for clipping, reading order, missing sections, and layout; check the text and every claim against the canonical facts. If available, `pdftotext generated/demo.pdf -` helps inspect extracted text. Resolve warnings and rerun checks after corrections before sharing. A successful render is not proof of a supported or readable resume. Real applications require the full career-apply workflow linked above.

## Appendix: optional tooling and contributor checks

- `uv run --locked career esco --help`: optional network-backed skill normalization, advisory only; not required for validation.
- Ollama-backed commands exist but are optional and are **not** the external agent's intake/apply workflow. Do not invoke local generation to replace evidence review or approvals.
- For contributor code/data changes, validate local data and run the locked development tests:

```bash
uv run --locked career validate
uv run --locked --extra dev pytest tests/
```

Use fictional data in an isolated checkout for contributor checks, never overwrite real records. These checks do not establish human approval or authorize a commit.
