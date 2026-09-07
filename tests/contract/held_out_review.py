"""Coldline.

===================

File:              tests/contract/held_out_review.py
Component:         Contract — Held-out review
Purpose:           Replay a held-out retrieval scenario and grade it without exposing it.
Interacts With:    The live API, a runtime-supplied held-out scenario definition
Sprint/Task:       Sprint 2 — Project 2 / Task 2.8
Concepts:          Held-out evaluation, protected grading
Tools:             Python 3.12, httpx

Sprint 2's only held-out scenario runs here, in protected CI, after the public
checks. The scenario arrives at runtime and is never committed: this file
contains the *procedure*, not the content.

The procedure ingests the scenario's own documents through the supplied document
API, runs its queries through the retrieval API, and requires each query to
retrieve the document the scenario expects while a caller from another tenancy
retrieves none of them. That exercises the data layer, the authorization
constraint, and both retrieval arms against content the public corpus does not
contain.

Nothing about the scenario is printed. A student reading CI output learns
whether their pipeline passed, and nothing about what it was asked.
"""

import json
import os
import sys
import uuid
from typing import Any

import httpx

PASS = "HELD_OUT_CHECK_PASSED"
FAIL = "HELD_OUT_CHECK_FAILED"
# Printed instead of any exception text. A traceback here could carry a held-out
# document, a query, or an expectation into a log a student can read.
INFRASTRUCTURE = "HELD_OUT_INFRASTRUCTURE_ERROR: contact course support."
CLEARANCES = ("standard", "restricted")


class ScenarioError(Exception):
    """Report that the supplied scenario is unusable, without describing it.

    Distinct from a failed grade on purpose. A malformed scenario, an
    unreachable API, or a stack that did not come up is an infrastructure
    fault; reporting it as "did not pass" would blame the submission for a
    problem on this side. The message carries no detail for the same reason the
    grade carries none.
    """


def _validated_scenario(scenario_json: str) -> tuple[dict[str, Any], list[Any], str]:
    """Return the scenario's documents, queries, and clearance, or refuse to grade.

    The shape is checked strictly and up front. A scenario with an unexpected
    key, a missing field, or a query naming a document it does not supply
    cannot produce a meaningful grade, and silently treating it as a failure
    would record a wrong result rather than an unusable one.
    """
    try:
        scenario = json.loads(scenario_json)
    except ValueError as exc:
        raise ScenarioError("Invalid held-out configuration") from exc
    if not isinstance(scenario, dict) or not set(scenario) <= {
        "documents",
        "queries",
        "clearance",
    }:
        raise ScenarioError("Invalid held-out configuration")

    documents = scenario.get("documents")
    queries = scenario.get("queries")
    clearance = scenario.get("clearance", "restricted")
    if not isinstance(documents, dict) or not documents:
        raise ScenarioError("Invalid held-out configuration")
    if not isinstance(queries, list) or not queries:
        raise ScenarioError("Invalid held-out configuration")
    if clearance not in CLEARANCES:
        raise ScenarioError("Invalid held-out configuration")

    for document in documents.values():
        if not isinstance(document, dict) or not {"title", "body", "access_tier"} <= set(document):
            raise ScenarioError("Invalid held-out configuration")
        if document["access_tier"] not in CLEARANCES:
            raise ScenarioError("Invalid held-out configuration")
        if not all(
            isinstance(document[field], str) and document[field] for field in ("title", "body")
        ):
            raise ScenarioError("Invalid held-out configuration")
    for query in queries:
        if not isinstance(query, dict) or not {"text", "expects"} <= set(query):
            raise ScenarioError("Invalid held-out configuration")
        if not isinstance(query["text"], str) or not query["text"]:
            raise ScenarioError("Invalid held-out configuration")
        if str(query["expects"]) not in {str(name) for name in documents}:
            raise ScenarioError("Invalid held-out configuration")
    return documents, queries, str(clearance)


def _ingest(client: httpx.Client, document: dict[str, Any], tenant_id: str) -> str | None:
    """Persist one held-out document and return its identifier, or None on failure."""
    document_id = f"held-out-{uuid.uuid4().hex}"
    response = client.post(
        "/api/v1/documents",
        json={
            "document_id": document_id,
            "title": document["title"],
            "body": document["body"],
            "access": {"tenant_id": tenant_id, "access_tier": document["access_tier"]},
            "provenance": {
                "source_uri": f"s3://held-out/{document_id}.md",
                "custodian": "Coldline held-out review",
                "revision": "r1",
                "recorded_at": "2026-03-01T00:00:00+00:00",
            },
        },
    )
    if response.status_code != 201:
        return None
    return document_id


def _retrieved_documents(
    client: httpx.Client, text: str, tenant_id: str, clearance: str
) -> list[str] | None:
    """Return the document identifiers one query retrieves, or None on failure."""
    response = client.post(
        "/api/v1/retrieval/search",
        json={
            "query_id": f"held-out-{uuid.uuid4().hex}",
            "text": text,
            "authorization": {"tenant_id": tenant_id, "clearance": clearance},
        },
    )
    if response.status_code != 200:
        return None
    results = response.json().get("results")
    if not isinstance(results, list):
        return None
    return [str(item["document_id"]) for item in results]


def run_held_out_check(scenario_json: str, api_base_url: str) -> bool:
    """Ingest the held-out documents, run its queries, and grade the outcome.

    Returns True or False for a grade, and raises `ScenarioError` when it could
    not grade at all. Neither carries anything about the scenario, so a student
    reading CI output cannot recover the held-out content or its expectations.
    """
    documents, queries, clearance = _validated_scenario(scenario_json)
    tenant_id = f"held-out-{uuid.uuid4().hex[:12]}"
    other_tenant_id = f"held-out-{uuid.uuid4().hex[:12]}"

    try:
        with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
            ingested: dict[str, str] = {}
            for name, document in documents.items():
                document_id = _ingest(client, document, tenant_id)
                if document_id is None:
                    raise ScenarioError("Invalid held-out configuration")
                ingested[str(name)] = document_id

            for query in queries:
                expected = ingested[str(query["expects"])]
                retrieved = _retrieved_documents(client, str(query["text"]), tenant_id, clearance)
                if retrieved is None or expected not in retrieved:
                    return False

                # The same question asked from a different tenancy must reach
                # none of the held-out documents. A pipeline that answers this
                # one has lost the Task 2.4 boundary, however well it
                # retrieves.
                leaked = _retrieved_documents(
                    client, str(query["text"]), other_tenant_id, clearance
                )
                if leaked is None or set(leaked) & set(ingested.values()):
                    return False
    except httpx.HTTPError as exc:
        # The supplied stack did not answer. This job runs the base tree, so
        # that is a problem on this side rather than a failed grade, and it is
        # reported as one instead of being recorded as "did not pass".
        raise ScenarioError("Invalid held-out configuration") from exc
    except (KeyError, TypeError, ValueError) as exc:
        # The scenario passed validation, so a shape error this late means the
        # API answered in a form the procedure does not understand.
        raise ScenarioError("Invalid held-out configuration") from exc
    return True


def main(scenario_json: str, api_base_url: str) -> int:
    """Return 0 for a pass, 1 for a failed grade, and 2 for an unusable run.

    Three exit codes rather than two, so the workflow can report `error`
    instead of `failure` when the fault is on this side. A missing secret, a
    malformed scenario, or a stack that did not start must never look like a
    wrong answer.
    """
    try:
        passed = run_held_out_check(scenario_json, api_base_url)
    except Exception:
        # Never print the exception: its text may carry protected inputs or
        # protected responses.
        print(INFRASTRUCTURE, file=sys.stderr)
        return 2
    print(PASS if passed else FAIL)
    return 0 if passed else 1


if __name__ == "__main__":
    # The scenario arrives through the environment, never as an argument: a
    # command-line argument is readable from /proc/<pid>/cmdline by any other
    # process for as long as this one lives.
    scenario_env = os.environ.get("HELD_OUT_SCENARIO", "")
    api_base_url_env = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    sys.exit(main(scenario_env, api_base_url_env))
