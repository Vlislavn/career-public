# Application quality gates

Run from the repository root after editing a spec:

```bash
uv run career validate
uv run career validate-resume applications/<slug>/_work/resume.yaml
uv run career report applications/<slug>/_work/resume.yaml applications/<slug>/_work/jd.txt
uv run career render applications/<slug>/_work/resume.yaml
```

`render` prints its PDF path under `generated/`; ensure it exists and is nonempty. For additional variants, use a distinct spec `name` and repeat validation, report, and render. Run `uv run --extra dev pytest tests/` when changing code or sample data.

- Stop on validation errors; inspect every warning. `report` measures lexical coverage, not whether a claim is supported. Check each bullet against its fact IDs, metric units and scope; validate summary and project names manually. Check any variant-to-variant differences against the evidence map.
- Review a PDF's text/reading order (for example, with `pdftotext` if installed), page count and visual rendering. Verify no clipping, missing sections, or garbled numbers. Fix the spec and rerun checks before sharing. Never edit the PDF to hide a source problem.
- Record any unresolved gaps and pending staging approvals. An application is incomplete when required human approval or factual verification is pending. Do not auto-commit, publish, or submit it.
