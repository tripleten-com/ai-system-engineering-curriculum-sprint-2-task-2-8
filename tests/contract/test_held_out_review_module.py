"""Coldline.

===================

File:              tests/contract/test_held_out_review_module.py
Component:         Contract — Held-out review dry run
Purpose:           Confirm the held-out check mechanism works, using a fake, non-secret scenario.
Interacts With:    tests.contract.held_out_review, the live API
Sprint/Task:       Sprint 2 — Project 2 / Task 2.8
Concepts:          Held-out evaluation
Tools:             Python 3.12, pytest, httpx
"""

import json

import pytest

from tests.contract.held_out_review import (
    FAIL,
    INFRASTRUCTURE,
    PASS,
    ScenarioError,
    main,
    run_held_out_check,
)
from tests.runtime_config import host_port

pytestmark = pytest.mark.runtime

# A fake scenario, in the open, so the *mechanism* is testable without the real
# one. Its content is invented for this check and grades nothing: the protected
# CI job supplies the real scenario at runtime.
#
# The negatives below cover the branches a fake scenario can reach
# deterministically, and they check the *classification* as much as the outcome:
# an expectation the scenario never supplied, a malformed scenario, and an
# unreachable API are all faults on the grading side, so each must be reported
# as unusable rather than recorded as a failed submission. The "expected
# document was not retrieved" branch depends on what the pipeline ranks, so it
# is exercised by the real scenario in CI rather than asserted here against a
# two-document fixture that top_k would return in full.
FAKE_SCENARIO = {
    "clearance": "restricted",
    "documents": {
        "brine-line": {
            "title": "Held-out procedure: brine line purge",
            "body": (
                "Purge the brine line at the start of every night shift and record the purge "
                "duration against the bay number. A purge shorter than four minutes is a "
                "facility fault and the bay is taken out of service until the site engineer "
                "signs it back. Record the operator badge and the measured outlet temperature "
                "in the shift log."
            ),
            "access_tier": "standard",
        },
        "glycol-loop": {
            "title": "Held-out procedure: glycol loop top-up",
            "body": (
                "Top up the glycol loop when the reservoir sight glass falls below the lower "
                "mark. Record the volume added, the batch reference of the glycol drum, and "
                "the duty engineer name. A top-up larger than twelve litres in one week is "
                "raised with the site engineer as a suspected leak."
            ),
            "access_tier": "restricted",
        },
    },
    "queries": [
        {"text": "purge duration recorded against the bay number", "expects": "brine-line"},
        {"text": "volume of glycol added and the drum batch reference", "expects": "glycol-loop"},
    ],
}


def _base_url() -> str:
    """Return the API base URL, honoring the documented host-port override."""
    return f"http://localhost:{host_port('COLDLINE_API_HOST_PORT', 8000)}"


def test_held_out_check_mechanism_with_a_fake_scenario() -> None:
    """The mechanism must ingest, retrieve, and enforce tenancy on a fake scenario."""
    assert run_held_out_check(json.dumps(FAKE_SCENARIO), _base_url())


def test_a_query_expecting_an_unsupplied_document_is_unusable_not_a_failure() -> None:
    """A scenario that cannot be satisfied is a fault here, not a wrong answer.

    Without a negative case, a procedure that returned True unconditionally
    would look like a passing held-out review for every submission. Without the
    *classification*, an authoring mistake in the scenario would be recorded
    against a submission that had nothing to do with it.
    """
    scenario = json.loads(json.dumps(FAKE_SCENARIO))
    scenario["queries"] = [
        {"text": "purge duration recorded against the bay number", "expects": "no-such-document"}
    ]

    with pytest.raises(ScenarioError):
        run_held_out_check(json.dumps(scenario), _base_url())


def test_an_unreachable_api_is_unusable_not_a_failure() -> None:
    """A stack that did not answer is our fault: this job runs the supplied tree."""
    with pytest.raises(ScenarioError):
        run_held_out_check(json.dumps(FAKE_SCENARIO), "http://localhost:1")


@pytest.mark.parametrize(
    "scenario",
    [
        "",
        "not json",
        "{}",
        '{"documents": {}}',
        '{"documents": {"a": {"title": "t", "body": "b", "access_tier": "standard"}}}',
        '{"queries": [{"text": "t", "expects": "a"}]}',
        '{"documents": {"a": {"title": "t", "body": "b", "access_tier": "nope"}},'
        ' "queries": [{"text": "t", "expects": "a"}]}',
        '{"documents": {"a": {"title": "t", "body": "b", "access_tier": "standard"}},'
        ' "queries": [{"text": "t", "expects": "a"}], "surprise": 1}',
    ],
    ids=[
        "empty",
        "not-json",
        "no-keys",
        "no-queries",
        "documents-without-queries",
        "queries-without-documents",
        "unknown-access-tier",
        "unexpected-key",
    ],
)
def test_an_unusable_scenario_is_refused_before_anything_is_graded(scenario: str) -> None:
    """A missing or malformed scenario must be refused, never graded."""
    with pytest.raises(ScenarioError):
        run_held_out_check(scenario, _base_url())


def test_the_entry_point_separates_a_failed_grade_from_an_unusable_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 0, 1, and 2 must mean pass, failed grade, and unusable run.

    The workflow reads these codes to decide between reporting `success`,
    `failure`, and `error` on the pull request. Collapsing the last two would
    show a student a wrong answer where the fault was a missing secret or a
    stack that did not start.
    """
    assert main(json.dumps(FAKE_SCENARIO), _base_url()) == 0
    assert PASS in capsys.readouterr().out

    assert main("", _base_url()) == 2
    unusable = capsys.readouterr()
    assert INFRASTRUCTURE in unusable.err
    assert PASS not in unusable.out and FAIL not in unusable.out


def test_no_scenario_content_reaches_the_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A student reads this output, so nothing about the scenario may appear in it."""
    main(json.dumps(FAKE_SCENARIO), _base_url())
    captured = capsys.readouterr()
    printed = captured.out + captured.err
    for document in FAKE_SCENARIO["documents"].values():
        assert document["title"] not in printed
        assert document["body"] not in printed
    for query in FAKE_SCENARIO["queries"]:
        assert query["text"] not in printed
        assert query["expects"] not in printed
