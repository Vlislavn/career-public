"""Pytest fixtures — synthetic two-domain fixture (§22)."""
import pytest
import yaml
from pathlib import Path


@pytest.fixture
def tmp_career(tmp_path):
    """Create a minimal career-source data tree in tmp_path."""
    data = tmp_path / "data"
    (data / "profile").mkdir(parents=True)
    (data / "experience").mkdir()
    (data / ".staging").mkdir()
    (data / "profile" / "photo.png").write_bytes(b"fixture")

    # basics
    (data / "profile" / "basics.yaml").write_text(yaml.safe_dump({
        "name": "Test Person",
        "email": "test@example.com",
        "phone": "+1-555-0100",
        "location": "Test City",
        "photo": "photo.png",
        "socials": {"LinkedIn": "test-person", "GitHub": "test-person"},
        "languages": {"en": "C1", "de": "A2"},
        "magnets": ["clinical AI", "complex problems"],
        "repellents": ["bureaucracy"],
    }))

    # education
    (data / "profile" / "education.yaml").write_text(yaml.safe_dump({
        "entries": [{
            "id": "edu_001",
            "institution": "Test University",
            "degree": "BS Test",
            "start_date": "2018",
            "end_date": "2022",
        }]
    }))

    # aliases
    (data / "aliases.yaml").write_text(yaml.safe_dump({
        "Python": ["python", "python3"],
        "Go": ["golang"],
        "RCA": ["root cause analysis"],
    }))

    # experiences
    (data / "experience" / "helix.yaml").write_text(yaml.safe_dump({
        "id": "helix",
        "organization": "Helix Diagnostics",
        "title": "QA Engineer",
        "start_date": "2023-01",
        "end_date": "2025-06",
        "domains": ["clinical_genomics", "quality_assurance"],
        "facts": [{
            "id": "hx_001",
            "kind": "technical",
            "text": "Built a QA pipeline for clinical genomics.",
            "skills": ["RCA", "quality_assurance", "benchmark design", "mentoring"],
            "tools": ["Python"],
            "metrics": [{"value": 40, "unit": "%", "context": "faster QA"}],
            "source_refs": [],
        }, {
            "id": "hx_002",
            "kind": "publication",
            "text": "Validated a clinical genomics workflow.",
            "skills": ["quality_assurance"],
            "tools": [],
            "metrics": [],
            "source_refs": [],
        }],
    }))

    (data / "experience" / "vectorstack.yaml").write_text(yaml.safe_dump({
        "id": "vectorstack",
        "organization": "VectorStack AI",
        "title": "ML Engineer",
        "start_date": "2023-06",
        "end_date": "present",
        "domains": ["llm_platform", "ml_engineering"],
        "facts": [{
            "id": "vs_001",
            "kind": "technical",
            "text": "Built an LLM platform with Python.",
            "skills": ["LLM evaluation"],
            "tools": ["Python"],
            "metrics": [{"value": 99, "unit": "%", "context": "uptime"}],
            "source_refs": [],
        }],
    }))

    return tmp_path


@pytest.fixture
def helix_resume():
    """A resume spec selecting Helix facts (clinical QA role)."""
    return {
        "schema_version": 1,
        "name": "helix_qa",
        "target": {"company": "Helix", "role": "QA Engineer"},
        "sections": {
            "work": [{
                "experience_id": "helix",
                "bullets": [{
                    "text": "Built a QA pipeline with 40% faster turnaround.",
                    "source_fact_ids": ["hx_001"],
                }],
            }],
            "education": [{"education_id": "edu_001"}],
            "skills": ["Python", "RCA"],
        },
    }


@pytest.fixture
def fabricated_resume():
    """A resume spec with an invented metric (should fail validation)."""
    return {
        "schema_version": 1,
        "name": "fabricated",
        "target": {"company": "X", "role": "Y"},
        "sections": {
            "work": [{
                "experience_id": "helix",
                "bullets": [{
                    "text": "Reduced latency by 99%.",
                    "source_fact_ids": ["hx_001"],
                }],
            }],
        },
    }
