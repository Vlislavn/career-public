# Career Source

Local, evidence-grounded career facts and deterministic resume validation/rendering. Optional local-LLM utilities are separate from the agent application workflow.

```text
examples/data/       -> data/ (fictional demo only)
examples/blank-data/ -> data/ (private working checkout; fill in your facts)
                         -> career validate -> agent review -> render
```

## Install

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and allow access to the Python package index on first setup. From this repository root:

```bash
uv sync --python 3.12 --locked                # installs the project and runtime dependencies
# For contributors running tests instead: uv sync --python 3.12 --locked --extra dev
```

`pyproject.toml` declares the dependencies and `uv.lock` pins them. They include Pydantic, PyYAML, ruamel.yaml, Typer and **`rendercv[full]`**, which installs RenderCV, its fonts and the Python Typst package. No separate `pip install rendercv`, system `rendercv` or `typst` executable is needed for the supported rendering path. Python 3.12–3.13 is supported; the command above selects 3.12 even if your system Python is newer. `pdftotext` (Poppler) is optional for PDF text/reading-order checks, not rendering.

## Try it with fictional data

Choose **one** data path in a fresh checkout; never overwrite an existing `data/`:

```bash
cp -R examples/data data
uv run --locked career validate
uv run --locked career match examples/jd.txt
uv run --locked career master                 # → data/master_latest.pdf
```

Confirm `data/master_latest.pdf` is nonempty and inspect it before sharing.
For a real candidate, **instead** copy `examples/blank-data` to `data`, fill the profile
and create experience metadata; see [real setup](docs/USER_GUIDE.md#real-candidate-setup).
`data/` is ignored but can still be force-added: never commit or publish it.

For tests: `uv sync --python 3.12 --locked --extra dev`, then
`uv run --locked --extra dev pytest tests/`. Optional `career esco` calls the
public EU ESCO API. `career polish`/`career extract` need a separately running
local Ollama server and model; they are **not used** in the agent JD workflow.

Agents: **read [AGENTS.md](AGENTS.md) first** for ingestion, approval, evidence,
validation and privacy rules. The JD skill contains the detailed application
procedure. Changes: [Changelog](CHANGELOG.md). License: [MIT](LICENSE).
