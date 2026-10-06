---
name: career-apply
description: Tailor evidence-grounded resumes to a supplied JD, including ATS alignment, gaps, and honest or optional stretched variants.
---

# Career apply

Run from the repository root with `AGENTS.md`, `pyproject.toml`, and `data/` present. Read [AGENTS](../../../AGENTS.md) for approval, privacy, evidence, generation, testing and release constraints. If facts are empty or the profile contains placeholders, stop and use [real setup](../../../docs/USER_GUIDE.md#real-candidate-setup), never demo evidence.

Read all three references: [workflow](references/workflow.md), [evidence policy](references/evidence-policy.md), [quality gates](references/quality-gates.md). The agent writes; the CLI validates and renders. Probe `uv run career --help` before execution. Pending approval or verification means the application is incomplete.
