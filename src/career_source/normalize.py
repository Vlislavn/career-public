"""Alias + case normalization (§5.4). Not an ontology."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import yaml

def _aliases_path() -> Path:
    from .load import DATA_DIR
    return DATA_DIR / "aliases.yaml"

@lru_cache(maxsize=1)
def load_aliases() -> dict[str, list[str]]:
    path = _aliases_path()
    if not path.exists():
        return {}
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return {k: list(v) for k, v in raw.items()}

@lru_cache(maxsize=1)
def _reverse_map() -> dict[str, str]:
    rev: dict[str, str] = {}
    for canon, aliases in load_aliases().items():
        rev[canon.lower()] = canon
        for a in aliases:
            rev[a.lower()] = canon
    return rev

def normalize(token: str) -> str:
    """Normalize a skill/tool token to its canonical form via aliases.yaml."""
    return _reverse_map().get(token.strip().lower(), token.strip())

def esco_lookup(term: str, kind: str = "skill") -> dict | None:
    """Query ESCO API (keyless EU service). Cached in data/.esco_cache.json.
    Uses word-boundary matching to filter false matches (CAPA↎capacity)."""
    import json as _j, re, urllib.request as u, ssl, sys
    from .load import DATA_DIR
    cp = DATA_DIR / ".esco_cache.json"
    cache = _j.loads(cp.read_text()) if cp.exists() else {}
    key = f"{kind}:{term}"
    if key in cache:
        return cache[key]
    url = f"https://ec.europa.eu/esco/api/search?text={u.quote(term)}&language=en&type={kind}&limit=5"
    try:
        ctx = None
        try:
            import certifi; ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            pass
        with u.urlopen(url, timeout=5, context=ctx) if ctx else u.urlopen(url, timeout=5) as r:
            data = _j.loads(r.read())
    except (u.URLError, _j.JSONDecodeError, OSError) as e:
        print(f"WARN: ESCO API error for '{term}': {e}", file=sys.stderr); return None
    tl = term.lower()
    for h in data.get("_embedded", {}).get("results", []):
        title = h.get("title", "")
        if re.search(r"\b" + re.escape(tl) + r"\b", title.lower()):
            cache[key] = {"uri": h.get("uri"), "label": title}
            cp.write_text(_j.dumps(cache, ensure_ascii=False)); return cache[key]
    cache[key] = None; cp.write_text(_j.dumps(cache, ensure_ascii=False))
    return None
