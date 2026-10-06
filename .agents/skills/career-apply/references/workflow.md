# JD workflow

Follow [AGENTS](../../../../AGENTS.md), [evidence policy](evidence-policy.md), [quality gates](quality-gates.md).

1. Save `applications/<slug>/_work/jd.txt`; avoid overwrite. For URLs record source/retrieval date; research original vacancy/official organization sources, separating verification from inference.
2. Run `uv run career validate` before mapping/drafting; stop on errors, review warnings. Inspect canonical experiences/education using `uv run career facts --json` and `uv run career match applications/<slug>/_work/jd.txt --json` (lexical). Map requirements to fact IDs: direct/transferable/gap; explain significant exclusions.
3. For material gaps, ask once about undocumented experience and wait. Retain gaps if none or declined; new facts follow AGENTS’ approval protocol, then refresh mapping.
4. Run `uv run career build --include <ids> --output applications/<slug>/_work/resume.yaml`. Set filename-stem `name`, truthful `target.company`, `target.role`; optionally education IDs. Empty `bullet.text` uses canonical text.
5. Save the gap report: `GAPS`, `TRANSFERABLE` (bounds/IDs), `STRENGTHS` (IDs). Apply quality gates; copy the checked PDF into `applications/<slug>/` before delivery.
