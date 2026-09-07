"""Coldline.

===================

File:              tests/contract/test_submission.py
Component:         Contract tests — Test Submission
Purpose:           Tests for the public answer and path checks for this Task's submission.
Interacts With:    Published interfaces and repository boundaries
Sprint/Task:       Sprint 2 — Project 2
Concepts:          Compatibility, ownership, export safety
Tools:             Python 3.12, pytest
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.contract.submission_validation import (
    SubmissionError,
    _load_one_document,
    main,
    validate_changed_paths,
    validate_submission,
)

ROOT = Path(__file__).parents[2]
SCHEMA = ROOT / "docs/contracts/submission.schema.json"

STAGES = ("chunking", "embedding", "sparse_matching", "authorization_filtering", "fusion")
LAYOUTS = ("integrated_relational_table", "dedicated_vector_payload_store")
LIMITATIONS = ("policy_enforcement_gap", "listing_pagination_not_exercised")
# Codes the profile withdrew. They are absent from the answer contract, so the
# public verifier must reject them outright rather than leave them to a runtime
# check: a student cannot record a divergence the Task no longer publishes.
WITHDRAWN = ("distributed_consistency_difference", "upload_part_handling_divergence")


def valid_answers(**overrides: Any) -> dict[str, object]:
    """Return a complete answer sheet in the published shape."""
    answers: dict[str, Any] = {
        "attributed_failure_stage": "embedding",
        "ruled_out_stage": "sparse_matching",
        "pgvector_storage_layout": "integrated_relational_table",
        "qdrant_storage_layout": "dedicated_vector_payload_store",
        "fidelity_limitation": "policy_enforcement_gap",
    }
    answers.update(overrides)
    return {"answers": answers}


def _task_root(tmp_path: Path, submission_text: str) -> Path:
    """Stage a minimal Task root the public verifier can validate."""
    (tmp_path / "docs/contracts").mkdir(parents=True)
    (tmp_path / "submission.yaml").write_text(submission_text, encoding="utf-8")
    (tmp_path / "submission-sample.yaml").write_text(
        (ROOT / "submission-sample.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "docs/contracts/submission.schema.json").write_text(
        SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp_path


@pytest.mark.parametrize("stage", STAGES)
def test_every_stage_is_well_formed(tmp_path: Path, stage: str) -> None:
    """The public schema must not privilege one stage; the live evidence decides that.

    Whether a stage is the *right* answer depends on the running pipeline, and
    the runtime checks settle it. The public verifier only decides what is
    well-formed.
    """
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers(attributed_failure_stage=stage)))

    validate_submission(root / "submission.yaml", SCHEMA)


@pytest.mark.parametrize("limitation", LIMITATIONS)
def test_every_published_limitation_is_well_formed(tmp_path: Path, limitation: str) -> None:
    """Both qualified codes are well-formed; only the profile says which one is recorded."""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers(fidelity_limitation=limitation)))

    validate_submission(root / "submission.yaml", SCHEMA)


@pytest.mark.parametrize("limitation", WITHDRAWN)
def test_a_withdrawn_limitation_is_rejected(tmp_path: Path, limitation: str) -> None:
    """Catch a code the profile withdrew being offered as an answer."""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers(fidelity_limitation=limitation)))

    with pytest.raises(SubmissionError, match="fidelity_limitation"):
        validate_submission(root / "submission.yaml", SCHEMA)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_both_storage_layouts_are_well_formed(tmp_path: Path, layout: str) -> None:
    """Neither layout is privileged by the schema; the supplied profile decides."""
    root = _task_root(
        tmp_path,
        yaml.safe_dump(valid_answers(pgvector_storage_layout=layout, qdrant_storage_layout=layout)),
    )

    validate_submission(root / "submission.yaml", SCHEMA)


def test_blank_template_fails_with_field_address(tmp_path: Path) -> None:
    """An untouched answer sheet must identify the first incomplete field."""
    root = _task_root(tmp_path, (ROOT / "submission.yaml").read_text(encoding="utf-8"))

    with pytest.raises(SubmissionError, match="answers.attributed_failure_stage"):
        validate_submission(root / "submission.yaml", SCHEMA)


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"attributed_failure_stage": "reranking"}, "attributed_failure_stage"),
        ({"ruled_out_stage": "ingestion"}, "ruled_out_stage"),
        ({"pgvector_storage_layout": "relational"}, "pgvector_storage_layout"),
        ({"qdrant_storage_layout": "dedicated"}, "qdrant_storage_layout"),
        ({"fidelity_limitation": "no_iam"}, "fidelity_limitation"),
        ({"attributed_failure_stage": "the embedding stage"}, "attributed_failure_stage"),
    ],
    ids=[
        "unlisted-stage",
        "unlisted-ruled-out-stage",
        "unlisted-pgvector-layout",
        "unlisted-qdrant-layout",
        "unlisted-limitation",
        "prose-instead-of-an-enum",
    ],
)
def test_values_outside_the_published_contract_are_rejected(
    tmp_path: Path, overrides: dict[str, Any], message: str
) -> None:
    """The public schema must name the field it rejected, and reject the right ones."""
    root = _task_root(tmp_path, yaml.safe_dump(valid_answers(**overrides)))

    with pytest.raises(SubmissionError, match=message):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_a_missing_answer_is_rejected(tmp_path: Path) -> None:
    """Five answers describe this Task; four describe an incomplete submission."""
    answers = valid_answers()
    mapping = answers["answers"]
    assert isinstance(mapping, dict)
    del mapping["fidelity_limitation"]
    root = _task_root(tmp_path, yaml.safe_dump(answers))

    with pytest.raises(SubmissionError, match="fidelity_limitation"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_unexpected_answer_field_is_rejected(tmp_path: Path) -> None:
    """Fields outside the published direct-answer schema must fail validation."""
    answers = valid_answers()
    mapping = answers["answers"]
    assert isinstance(mapping, dict)
    mapping["attribution_evidence"] = "no free text is assessed in this Task"
    root = _task_root(tmp_path, yaml.safe_dump(answers))

    with pytest.raises(SubmissionError, match="Additional properties"):
        validate_submission(root / "submission.yaml", SCHEMA)


def test_exact_sample_copy_is_rejected(tmp_path: Path) -> None:
    """The published sample must not be accepted as a student submission."""
    root = _task_root(tmp_path, (ROOT / "submission-sample.yaml").read_text(encoding="utf-8"))

    with pytest.raises(SubmissionError, match="fictional sample"):
        validate_submission(
            root / "submission.yaml",
            SCHEMA,
            sample_path=root / "submission-sample.yaml",
        )


def test_student_editable_paths_and_prefixes_are_permitted() -> None:
    """Only the answer sheet and a student's own tests may change in this Task."""
    validate_changed_paths(["submission.yaml"])
    validate_changed_paths(["tests/student/test_my_reading.py"])

    for protected in (
        "config/student/retrieval.yaml",
        "infra/corpus/investigation.jsonl",
        "infra/profiles/vector-engines.yaml",
        "infra/profiles/object-store-fidelity.yaml",
        "tests/diagnostics/attribution.py",
        "tests/diagnostics/inspect.py",
        "tests/contract/held_out_review.py",
        "tests/contract/test_miss_attribution.py",
        "docs/fidelity/ObjectStore.md",
        "src/adapters/object_store/s3.py",
    ):
        with pytest.raises(SubmissionError, match="protected path changed"):
            validate_changed_paths([protected])


def test_public_entrypoint_reports_an_incomplete_answer_sheet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch a verifier entrypoint that skips the real submission contract."""
    root = _task_root(tmp_path, (ROOT / "submission.yaml").read_text(encoding="utf-8"))

    assert main(root, changed_paths=[]) == 1
    assert "answers.attributed_failure_stage is incomplete" in capsys.readouterr().err


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "answers: {value: first, value: second}\n",
        "answers: &answer {value: fictional}\n",
        "answers: *missing\n",
        "answers: {<<: {value: fictional}}\n",
        "answers: {value: 2026-09-04}\n",
        "answers: {value: !custom fictional}\n",
        "answers: {1: fictional}\n",
    ],
    ids=[
        "duplicate-key",
        "anchor",
        "alias",
        "merge-key",
        "date",
        "custom-tag",
        "non-string-key",
    ],
)
def test_non_json_yaml_constructs_are_rejected(tmp_path: Path, unsafe_text: str) -> None:
    """Reject restricted syntax before schema validation can mask a parser defect."""
    submission = tmp_path / "submission.yaml"
    submission.write_text(unsafe_text, encoding="utf-8")

    with pytest.raises(SubmissionError, match="restricted YAML"):
        _load_one_document(submission)


def test_multiple_yaml_documents_are_rejected(tmp_path: Path) -> None:
    """A second document cannot supply or replace the answer mapping."""
    submission = tmp_path / "submission.yaml"
    submission.write_text("answers: {}\n---\nanswers: {}\n", encoding="utf-8")

    with pytest.raises(SubmissionError, match="exactly one YAML mapping"):
        _load_one_document(submission)
