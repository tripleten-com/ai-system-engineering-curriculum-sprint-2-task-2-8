"""Coldline.

===================

File:              tests/contract/test_miss_attribution.py
Component:         Contract tests — Miss attribution and supplied profiles
Purpose:           Verify the attribution, the ruled-out stage, and the recorded classifications.
Interacts With:    The diagnostic, the running retrieval API, and the supplied profiles
Sprint/Task:       Sprint 2 — Project 2 / Task 2.8
Concepts:          Root-cause isolation, evidence-derived conclusions, supplied-fact grading
Tools:             Python 3.12, pytest, httpx
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from tests.diagnostics.attribution import (
    STAGES,
    AttributionError,
    ChunkFacts,
    CustodyFacts,
    StageObservation,
    attribute,
    custody_lines,
    evidence_lines,
    ruled_out,
)
from tests.diagnostics.inspect import (
    custody_for,
    designated_investigation,
    facts_for,
    observe,
    search,
)

TASK_ROOT = Path(__file__).resolve().parents[2]
VECTOR_PROFILES = TASK_ROOT / "infra/profiles/vector-engines.yaml"
FIDELITY_PROFILE = TASK_ROOT / "infra/profiles/object-store-fidelity.yaml"
# `assessed`: a fresh starter records nothing, so the four answer checks fail.
# `runtime`: the attribution checks read the running pipeline.
pytestmark = [pytest.mark.runtime, pytest.mark.assessed]


def _profiles() -> dict[str, Any]:
    """Return the supplied vector-engine profiles."""
    document = yaml.safe_load(VECTOR_PROFILES.read_text(encoding="utf-8"))
    engines = document.get("engines") if isinstance(document, dict) else None
    if not isinstance(engines, dict):
        pytest.fail(f"{VECTOR_PROFILES.name} declares no engines")
    return engines


def _profile_document() -> dict[str, Any]:
    """Return the supplied object-store fidelity profile."""
    document = yaml.safe_load(FIDELITY_PROFILE.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("limitations"), dict):
        pytest.fail(f"{FIDELITY_PROFILE.name} declares no limitations")
    return document


def answers() -> dict[str, Any]:
    """Return the recorded answer mapping, or fail with what is missing."""
    document = yaml.safe_load((TASK_ROOT / "submission.yaml").read_text(encoding="utf-8"))
    mapping = document.get("answers") if isinstance(document, dict) else None
    if not isinstance(mapping, dict):
        pytest.fail("submission.yaml must define an answers mapping")
    return mapping


def recorded(field: str, permitted: tuple[str, ...]) -> str:
    """Return one recorded enumerated answer."""
    value = answers().get(field)
    if not isinstance(value, str) or value not in permitted:
        pytest.fail(f"answers.{field} must be one of {list(permitted)}; found {value!r}")
    return value


Evidence = tuple[StageObservation, ChunkFacts, CustodyFacts]


@pytest.fixture(scope="module")
def evidence() -> Evidence:
    """Run the designated investigation once and return its stage evidence."""
    investigation = designated_investigation()
    with httpx.Client(timeout=30.0) as client:
        payload = search(client, investigation)
    return (
        observe(investigation, payload),
        facts_for(investigation),
        custody_for(investigation),
    )


def _report(observation: StageObservation, facts: ChunkFacts, custody: CustodyFacts) -> str:
    """Return the evidence as an assertion message a reader can act on."""
    lines = evidence_lines(observation, facts) + custody_lines(custody)
    return "\n  " + "\n  ".join(lines)


def test_the_designated_query_still_misses_its_target_chunk(evidence: Evidence) -> None:
    """The investigation has to have something to investigate.

    This check is about the supplied system, not about a submission. Three
    things have to stay true for the designated case to be the one this Task
    describes: the target chunk is withheld from the caller, it does not reach
    the results, and the withholding is a *defect* rather than the boundary
    working. The last one is the important one - the case is only a defect
    because the target's custody record contradicts its access label, and if
    that label were ever corrected the Task would be asking students to
    attribute a miss that no longer happens.
    """
    observation, facts, custody = evidence
    report = _report(observation, facts, custody)
    assert not observation.readable, (
        f"{observation.target_chunk_id} is now in the caller's readable pool, so the "
        "designated investigation is no longer the one this Task describes." + report
    )
    assert not observation.retrieved, (
        f"{observation.target_chunk_id} now reaches the final results, so the designated "
        "query no longer misses." + report
    )
    assert custody.contradicts_label, (
        f"{custody.document_id} is labelled {custody.labelled_tenant_id} and its custody "
        "record no longer contradicts that, so this miss is the access boundary working "
        "rather than the designated defect." + report
    )


def test_attributed_stage_matches_the_stage_evidence(evidence: Evidence) -> None:
    """The recorded stage must be the one the published rule derives from the evidence."""
    observation, facts, custody = evidence
    answer = recorded("attributed_failure_stage", STAGES)
    try:
        derived = attribute(observation, facts, custody)
    except AttributionError as exc:  # pragma: no cover - guarded by the check above
        pytest.fail(str(exc) + _report(observation, facts, custody))
    assert answer == derived, (
        f"answers.attributed_failure_stage records {answer!r}, and this evidence isolates "
        f"{derived!r}. The published rule is in docs/student/task-2-8-contract.md; run "
        "`poe diagnose` and read the per-stage lines." + _report(observation, facts, custody)
    )


def test_ruled_out_stage_is_proven_by_the_stage_evidence(evidence: Evidence) -> None:
    """The ruled-out stage must be one the evidence positively exonerates."""
    observation, facts, custody = evidence
    answer = recorded("ruled_out_stage", STAGES)
    proven = ruled_out(observation, facts, custody)
    attributed = attribute(observation, facts, custody)

    assert answer != attributed, (
        f"answers.ruled_out_stage records {answer!r}, which is also the stage this evidence "
        "attributes the miss to. A stage cannot be both the cause and ruled out."
    )
    assert answer in proven, (
        f"answers.ruled_out_stage records {answer!r}, and this evidence does not prove that "
        f"stage operated normally on the target chunk. It proves it for {sorted(proven)}. "
        "A stage that never saw the chunk is unobserved, not exonerated."
        + _report(observation, facts, custody)
    )


@pytest.mark.parametrize(
    "field,engine",
    [("pgvector_storage_layout", "pgvector"), ("qdrant_storage_layout", "qdrant")],
)
def test_storage_layout_classifications_match_the_supplied_profiles(
    field: str, engine: str
) -> None:
    """Each classification is graded against the profile this Task supplied."""
    document = yaml.safe_load(VECTOR_PROFILES.read_text(encoding="utf-8"))
    layouts = tuple(document["storage_layouts"])
    answer = recorded(field, layouts)
    profile = _profiles()[engine]
    assert answer == profile["storage_layout"], (
        f"answers.{field} records {answer!r}; the supplied profile for "
        f"{profile['display_name']} records a different layout. The profile is "
        f"infra/profiles/vector-engines.yaml and its prose form is "
        "docs/architecture/vector-engines.md."
    )


def test_recorded_fidelity_limitation_is_a_qualified_code() -> None:
    """The limitation must be one the supplied profile publishes as qualified.

    Every published code carries a reproducible local observation and an
    authoritative description of the AWS behavior it differs from; the
    observations themselves are reproduced by
    tests/contract/test_object_store_fidelity.py. Codes that could not be
    substantiated are recorded in the profile as withdrawn, with their reason,
    and are absent from the answer enum.
    """
    profile = _profile_document()
    limitations = profile["limitations"]
    answer = recorded("fidelity_limitation", tuple(limitations))
    withdrawn = profile.get("withdrawn", {})

    assert answer not in withdrawn, (
        f"answers.fidelity_limitation records {answer!r}, which the supplied profile withdrew: "
        f"{withdrawn.get(answer, {}).get('reason', '')}"
    )
    assert limitations[answer]["applies_here"], (
        f"answers.fidelity_limitation records {answer!r}, which the supplied profile does not "
        f"publish as applying here. The qualified codes are {sorted(limitations)}."
    )
