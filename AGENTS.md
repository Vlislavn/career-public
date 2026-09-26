# AGENTS.md — career-source agent contract

Vendor-neutral **primary entry point**. Read this before touching `data/`, changing code, or drafting a resume. Do not import personal facts, prefixes, model preferences, or instructions from another repository or a parent `AGENTS.md`. This repository stores and validates one candidate's professional history and renders evidence-grounded resumes. It is **not** an agent, job-search service, or application-submission platform.

## Choose the path

```text
INGEST: source notes → career add --stage → validate --staging
        → show proposed additions → explicit human approval
        → career promote → validate → canonical data/experience/*.yaml

APPLY: JD → canonical evidence → gap check → agent-written resume spec
       → validate-resume → render → PDF + gap/selection report
```

- **Demo:** in an empty checkout, `cp -R examples/data data` gives fictional evidence. Never cite it for a real person.
- **Real candidate:** use a separate local checkout; `cp -R examples/blank-data data`, fill its null profile name, then create reviewed experience metadata from `examples/experience-template.yaml`. Never overwrite an existing `data/`. See [real setup](docs/USER_GUIDE.md#real-candidate-setup). Stop if profile fields are placeholders or no canonical facts exist; do not generate an application.
- `data/`, `applications/`, and `generated/` are local and ignored, **not safe to publish**: Git can force-add ignored files. Do not import a private Git history, old resumes, or real candidate records into this shared starter.

## Source of truth and fact shape

- `data/experience/*.yaml` is the **only** canonical experience truth. `data/profile/*.yaml` holds identity, education and languages; `data/aliases.yaml` normalizes skill names. `data/.staging/` is unapproved proposals; `.esco_cache.json` is a cache. There is no required raw/provenance mirror; source notes are temporary input, not canonical evidence. Never automatically delete a user's source material.
- New experience IDs start with a lowercase letter and contain lowercase letters, digits or single underscores (no trailing underscore). Set `id` equal to its filename stem. New experiences generate fact IDs `<experience_id>_001`, etc.; existing experiences preserve their established prefix. Education IDs use `edu_001`, `edu_002`, etc. **No private prefix table.**
- Facts are plain, verifiable statements, not polished resume bullets. Each quantity in `fact.text` needs a matching `metrics[].value` (with unit and context). Skills are practices (e.g. root-cause analysis); tools are software/hardware (e.g. Python). Never list one item in both. `source_refs` is optional; do not fabricate citations or treat the JD as a source for candidate facts.
- `quality: {confidence, source, verified, notes}` may be stored per fact. `career quality` computes detail/completeness/score and flags scores below 60% for review; this is advisory, not proof. Aliases normalize skills; `career esco` is optional, network-backed and advisory, not a validation requirement.

## Ingest: propose, review, then promote

1. Read the target canonical experience, or create and review its metadata first (`career add` cannot create a new experience). Never infer an employer, date, or title from a JD.
2. Run `uv run career add <experience_id> --text 'factual prose' [--skills '...'] [--tools '...'] [--metrics 'value:unit:context'] --stage`. **Always specify `--stage`**; omitting it writes canonical data directly. The CLI cannot establish user approval.
3. Run `uv run career validate --staging` and `uv run career quality --staging`. Number claims and skill/tool overlap are checked. A >30% word-overlap warning is a **review prompt**, not permission to discard or merge a fact automatically.
4. Show the **entire staging file** against the existing canonical facts, including all proposed IDs, metrics, tools and unresolved ambiguities. Staging contains proposals, not a full replacement file. Wait for explicit approval of the whole proposed set. Do not treat validation, an earlier request, or silence as approval.
5. `career promote` appends **every fact in that experience's staging file**; it cannot select a subset. If only some facts are approved, prepare an approved-only staging proposal, revalidate it and show the revised diff for confirmation. Immediately before promotion, re-read the full staging file and confirm it matches the approved set exactly. Only then run `uv run career promote <experience_id>` and `uv run career validate`. Never auto-promote.
6. Report the outcome, even when no facts were approved:

```text
Added: N facts, N metrics, N technologies, N leadership items
Missing: unresolved quantity/date/source (fact ID if applicable)
```

## Apply: evidence before wording

For a supplied/linked JD or end-to-end tailoring, **read [career-apply/SKILL.md](.agents/skills/career-apply/SKILL.md) and its references**. That skill owns research, gap questioning, selection, honest/optional stretched variants, review and delivery. CLI availability is not authorization: the agent does the reasoning and writing; **do not call local generative commands** (`career polish`, `career extract`, Ollama-backed matching). `career match`/`report` are lexical lower bounds, not proof of qualification.

- Before drafting, map each JD requirement to `direct`, `transferable`, or `gap` with fact IDs. Ask once about **material unsupported experience**; stage any new facts through the approval protocol above. If none is provided or approved, keep the gap. Never convert planned learning into current study or work experience.
- Write Enhanced STAR when supported: business situation → goal/constraint → decision and action → measured result. Lead with outcomes, then tools; do not invent a result where none exists. Keep canonical facts in factual prose and perform resume phrasing only in `bullet.text`.
- **Never invent** an employer, title, date, project, responsibility, technology, metric, certification, publication, skill usage or credential. Every bullet has `source_fact_ids` (a list); every numeric claim traces to metrics in those referenced facts. `summary` and project names are not fully provenance-checked by the CLI: manually verify them. A skills-section warning may list supporting fact IDs outside the selected set; check and resolve it.
- Keep a mandatory gap report:

```text
GAPS: unsupported JD requirements
TRANSFERABLE: bounded adjacent experience ← supporting fact IDs
STRENGTHS: direct support ← supporting fact IDs
```

- The renderer selects a role-based template (`classic`, `engineeringresumes`, `sb2nov`); `design.template` overrides it. `career build` produces a skeleton with blank target company/role: fill these truthfully before validation. Run `uv run career validate`, `uv run career validate-resume <spec.yaml>`, then `uv run career render <spec.yaml>`. Inspect the PDF visually and its text/claims; CLI checks do not prove every sentence or a readable layout.

## Change and release boundaries

- **No auto-commit, auto-promotion, publication, or submission.** Every canonical fact change requires a diff the human saw and explicitly approved. `career delete` and `career clean` mutate canonical/local data: never run them without explicit scope and approval. This local starter has no commits or remote yet: an empty `git clone` contains no project files until a human reviews and makes the initial commit.
- Fail fast at I/O boundaries: no bare `except`, swallowed errors, or silent default-on-error. A bug fix needs a regression test that fails before the fix. Public behavior changes update `README.md`, relevant docs, and `CHANGELOG.md`. Do not add incidental annotations or comments to untouched code. When touching `src/` or `scripts/`, explicitly assess whether branches, functions or duplication can be simplified; simplify in the same change when safe, otherwise record why not in the review.
- For code/data changes: run `uv run career validate` (after safely initializing local demo data if no real data exists) **and** `uv run --extra dev pytest tests/`. For a JD package, use the skill's additional claim, report and PDF gates. Before *any* public commit, audit the complete staged file list/blobs and all reachable history for personal data, IDs, metadata and generated artifacts; `.gitignore` is not a privacy guarantee. The private→public sync script is maintained outside this repository and never commits or pushes.

CLI orientation (not authorization): inspect with `career facts --json`, `career quality`, `career skills` and optional `career esco`; assemble with `career build --include <ids> --output <spec.yaml>`; audit selection with `career report <spec.yaml> <jd.txt>`. Destructive maintenance and canonical promotion still require the human gate above.

Report concisely: show a staged diff before requesting approval; after ingestion use the `Added/Missing` format above. For plans or multi-part findings, lead with a small ASCII flow and cite concrete `file:line` evidence rather than claiming that validation proves unsupported prose. Command syntax may evolve: probe `uv run career --help` rather than copying a stale command list. For a runnable fictional example, see [docs/USER_GUIDE.md](docs/USER_GUIDE.md).
