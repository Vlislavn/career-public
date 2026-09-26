---
name: career-apply
description: Create an evidence-grounded application from a supplied job description using local canonical career facts and the existing career CLI. Use for resume tailoring, ATS alignment, gap analysis, or an honest and optional stretched variant. No fabricated candidate claims, automatic promotion, submission, or commit.
---

# Career apply

The agent interprets the JD and writes; the CLI validates facts and renders a PDF. The JD, company research, old resumes, and fictional `examples/data/` are **not** candidate evidence.

## Load only what is needed

1. Work from the repository root. Read [AGENTS.md](../../../AGENTS.md); stop if it or `pyproject.toml` is missing. If `data/` is missing, stop. For a real candidate, point to `docs/USER_GUIDE.md#real-candidate-setup` and `examples/blank-data/`; never silently install fictional data as evidence. If canonical facts are empty or the profile still has placeholder values, stop and ask for real evidence before any application draft.
2. Read [workflow](references/workflow.md), [evidence policy](references/evidence-policy.md), and [quality gates](references/quality-gates.md) for this JD. For a CLI-only demonstration, use the [user guide](../../../docs/USER_GUIDE.md).
3. Probe `uv run career --help` before choosing commands. Use `uv run career ...` from this root. No local generative-LLM commands (`polish`, `extract`) or external matching service are needed.

## Boundaries

- Candidate truth is `data/experience/*.yaml` plus `data/profile/*.yaml`. For a real candidate use a separate local checkout: keep `data/`, staging, application outputs, and generated PDFs there, ignored and unpublished; never put real candidate records in the shared public tree.
- Before drafting, classify each JD requirement as direct, transferable, or gap. If important requirements lack evidence, ask once about undocumented experience and pause for an answer. New facts are proposals: stage, validate, show a diff, obtain explicit approval, then and only then promote reviewed facts. An unapproved proposal cannot support a resume.
- Every written bullet cites canonical `source_fact_ids`; numbers match referenced metrics. Do not fabricate jobs, dates, titles, tools, credentials, projects, publications, skills, ownership, or study status. Label unsupported requests as gaps, not claims.
- Do not auto-commit, publish, submit applications, or auto-promote canonical facts. Review generated PDFs visually before delivery.

Run [workflow](references/workflow.md) in order and apply [quality gates](references/quality-gates.md). If approval is pending, report that blocker rather than declaring a completed application.
