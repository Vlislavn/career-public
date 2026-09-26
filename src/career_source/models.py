"""Pydantic v2 models for canonical career data and resume selection schema."""
from __future__ import annotations
import re
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
FactKind = Literal["responsibility", "achievement", "project", "leadership",
                   "technical", "research", "publication", "certification", "other"]
FACT_ID_RE = r"^[a-z0-9]+(_[a-z0-9]+)*_[0-9]{3}$"
EDU_ID_RE = r"^edu_\d{3}$"
DATE_RE = re.compile(r"^\d{4}(-\d{2})?$")

def number_claims(text):
    """Extract quantities, excluding explicit dates, versions and citation IDs."""
    text = text.replace("\u2212", "-")
    for pattern in (
        r"https?://\S+|\bdoi:\S+",
        r"\b(?:19|20)\d{2};\d+(?:\([^)]*\))?:[a-z]?\d+(?:[–-]\d+)?",
        r"\b(?:No\.?|ID:?|Certificate(?:\s+No\.?)?)\s*\d+\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(?:19|20)\d{2}\b",
        r"\b(?:version\s+|v)\d+(?:\.\d+)+(?!\d|%|\.\d)\b",
    ):
        text = re.sub(pattern, " ", text, flags=re.I)
    for match in re.finditer(r"(?<![\w.])[+-]?\d+(?:,\d{3})*(?:\.\d+)?\b", text):
        token = match.group()
        unit = re.match(r"\s*(%|percentage points\b|percent\b|pp\b|(?:hour|day|minute|week|month|year|record|report|patient|team|run|task|case|dollar|euro)s?\b|people\b)", text[match.end():], re.I)
        if not unit and re.fullmatch(r"(?:19|20)\d{2}", token):
            continue
        yield float(token.replace(",", "")), unit.group(1).lower() if unit else ""

def metric_unit(unit):
    return {"percent": "%", "percentage points": "pp"}.get(unit.lower(), unit.lower().rstrip("s"))

def number_errors(text, metrics):
    return [f"number '{value:g}{unit}' has no provenance in referenced fact metrics"
            for value, unit in number_claims(text)
            if not any(value == m.value and (not unit or metric_unit(unit) == metric_unit(m.unit)) for m in metrics)]

def _check_date(v: str | None, field_name: str) -> str | None:
    if v is None or v == "present":
        return v
    if not DATE_RE.match(v):
        raise ValueError(f"{field_name} must be YYYY-MM or YYYY (got '{v}')")
    return v
# ── canonical data models ──────────────────────────────────────────────

class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    value: float
    unit: str
    context: str = ""

class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=FACT_ID_RE)
    kind: FactKind
    text: str
    date: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    # SOTA quality tracking (hybrid: stored metadata + computed metrics)
    # confidence: 0-1 (source support level, Knowledge Vault pattern)
    # source: where the fact came from (CV, notes, transcript, user)
    # verified: user has confirmed this fact
    # detail: sparse|adequate|rich (text depth)
    # last_updated: ISO date
    quality: dict = Field(default_factory=dict)

    @field_validator("date")
    @classmethod
    def _vdate(cls, v: str | None) -> str | None:
        return _check_date(v, "date")

    @model_validator(mode="after")
    def _evidence(self):
        from .normalize import normalize
        overlap = {normalize(s) for s in self.skills} & {normalize(t) for t in self.tools}
        errors = number_errors(self.text, self.metrics)
        if overlap: errors.append(f"skill/tool overlap: {sorted(overlap)}")
        if errors: raise ValueError(f"{self.id}: {'; '.join(errors)}")
        return self

class Experience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
    organization: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    domains: list[str] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)

    @field_validator("start_date", "end_date")
    @classmethod
    def _vdate(cls, v: str | None) -> str | None:
        return _check_date(v, "date")

    @model_validator(mode="after")
    def _order(self) -> "Experience":
        if self.end_date and self.end_date != "present" and self.start_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be >= start_date")
        if len({f.id for f in self.facts}) != len(self.facts):
            raise ValueError(f"duplicate fact id in {self.id}")
        return self

class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=EDU_ID_RE)
    institution: str
    degree: str
    start_date: str
    end_date: Optional[str] = None
    focus: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _vdate(cls, v: str | None) -> str | None:
        return _check_date(v, "date")

class Basics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    orcid: Optional[str] = None
    photo: str = ""
    socials: dict[str, str] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)
    magnets: list[str] = Field(default_factory=list)
    repellents: list[str] = Field(default_factory=list)

class Profile(BaseModel):
    basics: Basics
    education: list[EducationEntry] = Field(default_factory=list)
# ── resume selection schema (§11) ──────────────────────────────────────

class ResumeTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str
    role: str
    jd_url: Optional[str] = None

class ResumeDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template: Optional[str] = None

class ResumeBullet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Optional[str] = None
    source_fact_ids: list[str]

    @model_validator(mode="after")
    def _nonempty(self) -> "ResumeBullet":
        if not self.source_fact_ids:
            raise ValueError("source_fact_ids must not be empty")
        return self

class ResumeWorkEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experience_id: str
    title: Optional[str] = None  # if supplied, must equal the canonical title
    bullets: list[ResumeBullet]

class ResumeProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    url: Optional[str] = None
    bullets: list[ResumeBullet]

class ResumePublication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact_id: str

class ResumeEducation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    education_id: str

class ResumeSections(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work: list[ResumeWorkEntry] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    publications: list[ResumePublication] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    skill_groups: dict[str, list[str]] = Field(default_factory=dict)

    def fact_ids(self):
        return {fid for entry in [*self.work, *self.projects] for b in entry.bullets for fid in b.source_fact_ids} | {p.fact_id for p in self.publications}

class ResumeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    name: str
    target: ResumeTarget
    design: Optional[ResumeDesign] = None
    summary: Optional[str] = None
    sections: ResumeSections
# ── validation result ──────────────────────────────────────────────────
ValidationLevel = Literal["ERROR", "WARN"]

class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: ValidationLevel
    message: str
