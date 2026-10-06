# Quality gates

From root:
```bash
uv run career validate
uv run career validate-resume applications/<slug>/_work/resume.yaml
uv run career report applications/<slug>/_work/resume.yaml applications/<slug>/_work/jd.txt
uv run career render applications/<slug>/_work/resume.yaml
```
Stop on errors; review all warnings. Verify `generated/<name>.pdf` is nonempty; inspect layout, text, reading order and page count. Fix the spec, not the PDF. Variants need distinct names, repeated checks and evidence-map review. [AGENTS](../../../../AGENTS.md) governs approval/privacy/tests; pending approval or verification means incomplete.
