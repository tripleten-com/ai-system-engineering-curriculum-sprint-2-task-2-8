# Coldline Task 2.8 — Miss attribution and held-out

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/tripleten-com/ai-system-engineering-curriculum-sprint-2-task-2-8/tree/main)

## Start the system

Prerequisites are Python 3.12 and Docker with Compose v2. The supplied bootstrap supports macOS
arm64/x86-64, Windows x86-64, and Linux x86-64/aarch64, and installs pinned uv 0.11.8 under
`.tools/bin`. If your computer cannot run the stack locally, use the Codespaces button above.

On macOS and most Linux distributions the interpreter is `python3`; substitute it wherever these
commands say `python`.

```shell
python infra/scripts/bootstrap.py
./.tools/bin/uv sync --frozen
./.tools/bin/uv run --frozen poe preflight
./.tools/bin/uv run --frozen poe start
./.tools/bin/uv run --frozen poe ready
./.tools/bin/uv run --frozen poe ingest
./.tools/bin/uv run --frozen poe baseline
```

PowerShell and POSIX wrappers are available under `infra/scripts/`. After uv is on `PATH`, the
shorter `uv run --frozen poe <task>` form works.

| Service | Local URL | Purpose |
|---|---|---|
| API | `http://localhost:8000` | Submit exception workflows and retrieval queries |
| Grafana | `http://localhost:3000` | Use the focused diagnostics dashboard |
| Prometheus | `http://localhost:9090` | Query bounded metrics |
| Jaeger | `http://localhost:16686` | Inspect local traces |
| LocalStack S3 | `http://localhost:4566` | Inspect the emulated object-storage endpoint |

Each of these ports can be overridden by setting the matching `COLDLINE_API_HOST_PORT`,
`COLDLINE_GRAFANA_HOST_PORT`, `COLDLINE_PROMETHEUS_HOST_PORT`, `COLDLINE_JAEGER_HOST_PORT`, or
`COLDLINE_LOCALSTACK_HOST_PORT` environment variable in your shell environment or a local `.env`
file (copy `.env.example`) if a default collides with something already running on your machine.
Keep the override in place for every `poe` command.

If you change the API port, also set `COLDLINE_API_HOST_PORT` in the shell that runs
`poe load-test`: this command does not read `.env`. Use the same port for startup and load testing.
For example, to use port 8001, run the command for your shell before starting the system:

| Shell | Set the API host port |
|---|---|
| PowerShell | `$env:COLDLINE_API_HOST_PORT = "8001"` |
| macOS/Linux (POSIX) | `export COLDLINE_API_HOST_PORT=8001` |

PostgreSQL, Redis, worker metrics, and OTLP remain inside the Compose network. Codespaces uses the
same `compose.yaml` and keeps every forwarded port private.

## Command path

For a fresh investigation, run the supplied commands in this order:

```text
poe start
poe ready
poe ingest
poe baseline
poe verify
```

| Command | Use |
|---|---|
| `poe ingest` | Run the supplied baseline corpus ingestion inside the API container |
| `poe baseline` | Run every published query and print the baseline evaluation report |
| `poe diagnose` | Print the per-stage and custody evidence for both supplied investigations |
| `poe attribution` | Rebuild, ingest, then run this Task's attribution checks |
| `poe held-out-dry-run` | Run the held-out grading procedure against a fake scenario, in the open |
| `poe benchmark-baseline` | Capture the baseline arm in `.benchmark/baseline.json` |
| `poe benchmark-experiment` | Capture the supplied configuration in `.benchmark/experiment.json` |
| `poe compare` | Read both captured reports, compare the cached judge evidence, and apply the adoption policy |
| `poe migrate` | Apply every migration inside the API container |
| `poe migrate-current` | Print the revision the database is stamped at |
| `poe migrate-down` | Roll back the most recent migration |
| `poe student-tests` | Run your own tests under `tests/student/` |
| `poe unit` | Run fast isolated behavior tests |
| `poe contract` | Check interfaces, boundaries, submissions, and repository structure |
| `poe smoke` | Check the initialized running platform |
| `poe e2e` | Run the external API-to-worker workflow |
| `poe verify` | Run the public student verification path |
| `poe scenario` | Run the supplied exception-workflow walkthrough |
| `poe load-test` | Run this repository's supplied traffic profile |
| `poe reset-baseline` | Clear exception and Redis data, then restart the worker between load runs |
| `poe restart` | Restart the existing API and worker containers **without rebuilding**; run `poe start` instead after editing source |
| `poe stop` | Remove containers and the network, keeping named volumes |
| `poe reset` | Remove containers, the network, and local named volumes |

`poe ingest` is idempotent: running it twice produces the same rows, the same counts, and the same
corpus digest. `poe reset` removes the database volume, so run `poe ingest` again after a reset.

For Task 2.8, `poe verify` rebuilds and starts the stack, ingests the supplied corpus, then runs
readiness, smoke tests, the end-to-end exception workflow, the answer-sheet checks, the attribution
checks, the held-out dry run, and your own tests under `tests/student/`.

`poe verify` begins with `poe start`, which is `up --build --wait`, so the container the checks read
is built from your checkout rather than from a previous one.

The attribution checks read the running pipeline through the same stage evidence `poe diagnose`
prints, and apply the published rule to it. There is no report file to record: the evidence is
produced fresh each run.

## Folder map

```text
repository root/
├── docs/                Student guidance, public contracts, and fidelity notes
│   ├── contracts/       Machine-readable public contracts
│   ├── fidelity/        Local-runtime boundary notes
│   ├── architecture/    Supplied vector engine technical profiles, in prose
│   ├── retrieval/       Supplied retrieval pipeline reference
│   └── student/         This Task's student contract
├── config/              Retrieval configuration, settled and supplied from this Task
├── infra/               Local setup and runtime configuration
│   ├── corpus/          Supplied synthetic corpus, query set, and the two investigations
│   ├── judge/           Supplied cached judge evidence and its provenance record
│   ├── profiles/        Supplied engine and emulator profiles, and their provenance record
│   └── postgres/        Database initialization and the migration baseline stamp
├── loadtest/            Supplied traffic profile and provider-latency harness
├── migrations/          Alembic environment, revision template, and revisions
│   └── versions/        The supplied baseline revision, and the one you write
├── src/
│   ├── api/             HTTP application code, the retrieval and document paths, composition
│   ├── worker/          Background application code
│   ├── domain/          Shared domain code, contracts, service and repository contracts
│   ├── ports/           Application interfaces
│   └── adapters/        Technology-specific implementations
└── tests/
    ├── unit/            Isolated behavior checks
    ├── benchmark/       Supplied evaluation harness, metrics, and adoption policy
    ├── contract/        Interface, retrieval, attribution, and repository checks
    ├── diagnostics/     Supplied stage inspector and the published attribution rule
    ├── doubles/         Supplied deterministic test doubles
    ├── student/         Your own tests
    ├── smoke/           Running-platform checks
    └── e2e/             Supplied workflow tools and checks
```

## Overview

Use the Task 2.8 lesson to decide what to do. This README covers local setup and repository
orientation.

1. `README.md` — local setup, commands, and permitted changes.
2. [`docs/student/task-2-8-contract.md`](docs/student/task-2-8-contract.md) — the published
   attribution rule, what "ruled out" means, the graded profiles, the held-out arrangement, and
   where each check looks.
3. `infra/corpus/investigation.jsonl` — the designated query, the contrast case, and the chunk
   that should answer each.
4. `tests/diagnostics/inspect.py` — the inspector `poe diagnose` runs.
5. `tests/diagnostics/attribution.py` — the published rule, in code.
6. [`infra/profiles/README.md`](infra/profiles/README.md) — what the supplied profiles are and why
   the classifications are graded against a file.
7. `tests/contract/held_out_review.py` — the held-out grading procedure. The scenario it grades is
   not here.

The application source lives in five flat packages:

| Package | Responsibility |
|---|---|
| `api` | HTTP delivery, API use cases, the retrieval workflow, versioned routes, configuration, and composition |
| `worker` | Background processing, retries, configuration, and composition |
| `domain` | Provider-neutral contracts, state rules, identity, redaction, embedding, chunking, fusion, access constraints, service and repository contracts |
| `ports` | Exactly five visible application interfaces |
| `adapters` | PostgreSQL, pgvector retrieval, Redis Streams, S3-compatible object storage, deterministic model, logs, traces |

`src/api/bootstrap.py` and `src/worker/bootstrap.py` compose each process from its settings and
adapters. Process settings live in `src/api/config.py` and `src/worker/config.py`; other modules
receive settings or collaborators through function and constructor arguments.

## The five ports

Find the available interfaces in `src/ports/`. A port describes an application capability; an
adapter provides it using a concrete technology. Determine which ports are active from your own
runtime evidence rather than from this guide.

| Port | General responsibility |
|---|---|
| `ModelProvider` | Call an AI model service |
| `Retriever` | Look up relevant context or documents |
| `ObjectStore` | Store large binary objects or files |
| `JobQueue` | Publish and consume background work |
| `SecretProvider` | Read API keys and credentials |

## The investigation

Two cases, and the chunk that should answer each:

```text
infra/corpus/investigation.jsonl   the queries, each caller's scope, and each target chunk
```

The first is the designated investigation and the one you answer. The second is supplied for
contrast and is graded by nothing. **Both are misses; only one is a defect.**

`poe diagnose` runs each with the stage evidence turned on and prints, stage by stage, whether the
target chunk was there — and prints the target document's custody record beside its access label,
so you can compare both kinds of observation. Attributing the designated miss to one stage,
and ruling another one out, is the Task. The published rule for both is in
[`docs/student/task-2-8-contract.md`](docs/student/task-2-8-contract.md).

## The held-out evaluation

Sprint 2's one held-out scenario is run by the CMS grading integration after the public checks. The
grading *procedure* is committed at `tests/contract/held_out_review.py`; the scenario it grades
arrives from private course assets at runtime. `poe held-out-dry-run` exercises that procedure against
a fake scenario written in the open, so you can watch the mechanism work without seeing the real
one.

The CMS worker runs the **supplied** tree rather than your branch, because it holds private assets
and this Task changes no application code. So it grades the delivered retrieval pipeline against
unseen content, and what it checks about your submission is that the pull request stayed inside
`submission.yaml` and `tests/student/`. See
[`docs/student/task-2-8-contract.md`](docs/student/task-2-8-contract.md) for what that does and
does not tell you, and for the difference between a `failure` and an `error` on the result.

## The settled experiment

Both configuration files are supplied and protected in this Task. For an optional local
comparison, start and ingest the system, then run `poe benchmark-baseline` and
`poe benchmark-experiment` before `poe compare`. The first two commands capture reports;
`poe compare` reads them without running the system or measuring again. Use the capture command's
`--recapture` option to replace its existing report. These local reports are not Task 2.8
submission artifacts and do not replace your Task 2.7 evidence.

The draft adoption policy still has unpublished latency constants. A comparison reports that
blocker and exits unsuccessfully; the supplied configuration is not evidence of an approved
keep/revert decision.

```text
config/retrieval-baseline.yaml   the original baseline
config/student/retrieval.yaml    the supplied checkpoint configuration
```

Both arms state their parameters per request through the supplied evaluation endpoint, so neither
side of the comparison pays a restart cost the other avoids.

```text
POST /api/v1/experiments/retrieval
  {"query_id": "...", "text": "...",
   "authorization": {"tenant_id": "...", "clearance": "standard"},
   "top_k": 3, "fusion_weight": 0.5}
  -> the fused ranking, its per-stage evidence, and the parameters applied
```

That endpoint is an evaluation surface, supplied and protected. It exists so two configurations can
be measured under identical conditions. `POST /api/v1/retrieval/search` keeps its own composed
defaults and takes no parameters from callers: tuning knobs do not belong on a product API.

Quality is still measured two ways, and only one of them is authoritative. See
[`infra/judge/README.md`](infra/judge/README.md) for what the cached judge evidence is and why it
never decides anything on its own.

## Schema ownership

Two mechanisms create schema in this repository, and they do not overlap.

| Mechanism | What it owns | When it runs |
|---|---|---|
| `infra/postgres/0*.sql` | The initialized schema: `exceptions`, `documents`, `chunks`, `idempotency_claims`, and the `alembic_version` stamp | The initializer, on every start, idempotently |
| `migrations/versions/` | Every change made *after* that point | `poe migrate`, on request |

The baseline revision is empty on purpose: it names the schema as initialized, and it is where a
rollback stops. From this Task the initializer also runs `alembic upgrade head` on every start, so
the service never serves traffic against a schema older than the code in this repository. Both
`infra/postgres/` and `migrations/` are protected here; Task 2.6's reference migration is supplied
and already applied.

## Document API

The document surface and the repository behind it are supplied.

```text
POST /api/v1/documents                        -> persist one document and its chunks atomically
GET  /api/v1/documents?tenant_id=&clearance=  -> list the documents one scope may read
GET  /api/v1/documents/{id}?tenant_id=&clearance=         -> one document, or 404 when out of scope
GET  /api/v1/documents/{id}/chunks?tenant_id=&clearance=  -> that document's readable chunks
```

## Versioned API

Version 1 and the version 2 document endpoint are both supplied from this Task onward.

```text
POST /api/v2/documents   DocumentV2Request  -> DocumentV2Response
```

The reference version 2 endpoint from Task 2.5 is composed for you here. Your own Task 2.5
implementation — of either supported operation — stays in that Task's pull request.

## Retrieval API

Both endpoints are supplied and are not student work.

```text
POST /api/v1/retrieval/search
  {"query_id": "...", "text": "...",
   "authorization": {"tenant_id": "...", "clearance": "standard"},
   "explain": false}
  -> ranked results, per-stage evidence, prompt context, citations

GET  /api/v1/corpus/objects?prefix=corpus/
  -> the object keys visible through the published ObjectStore port
```

Set `"explain": true` to add the authorization stage's readable pool to the evidence. That costs
one extra query, so ordinary requests leave it off.

## Test levels

| Level | Requires Compose | Main question |
|---|---:|---|
| Unit | No | Does one responsibility behave correctly, including failures? |
| Contract | Some | Do interfaces, schemas, paths, and dependency rules stay compatible? |
| Smoke | Yes | Did the complete local platform initialize and become observable? |
| E2E | Yes | Can an external client complete the supplied workflow? |

Contract checks marked `runtime` need the running stack. `poe contract` skips them; `poe verify`
and `poe runtime-contract` run them.

## Submission checks

Run `poe verify` locally before opening your student pull request. Public GitHub CI repeats
the student checks. The course platform (CMS) runs the required protected grading separately
and associates its results with your submission commit. A green template-export check, or a
skipped student check on an `export/` branch, is not a passing grade. You do not configure
GitHub grading secrets. Follow the Task lesson's instructor-review and progression policy.

## Task boundary

Task 2.8 asks you to attribute one designated retrieval miss to exactly **one** pipeline stage,
rule out one other stage with direct evidence, classify the storage layout each supplied engine
profile records, record one code from the draft object-store fidelity profile, and
confirm the protected held-out evaluation in CI.

The fidelity profile's qualification remains unresolved: the credential check covers one listing
request, and the pagination entry records missing test coverage rather than an observed AWS
divergence. The existing answer codes remain in the draft while that release issue is reviewed.

You change no code. The diagnostic, the attribution rule, the two investigation cases, the engine
profiles, the emulator profile, and the held-out grading procedure are all supplied. What you
contribute is five structured decision answers.

Note what is *not* asked. The designated fault is in the data, not in `src/`, and repairing it is
no part of this Task — you investigate and classify. The repair is nonetheless demonstrated during
authoring, so that the case is known to be caused by the one thing it is attributed to.

Both attribution answers are checked against the live stage evidence using the published rule, and
the three classifications are checked against the supplied profiles — never against outside
knowledge about these products.

These paths are student-editable:

- `submission.yaml`
- anything you add under `tests/student/`

Everything else is protected, and the CMS held-out grader refuses to grade a pull request that changed
anything else: it grades the supplied pipeline, so a submission that altered it would be graded on
a different system.

Do not install Qdrant, and do not try to inspect the held-out scenario. Neither is part of this
Task.

### Student walkthrough

See **Task 2.8: Miss attribution and held-out** in your course platform for the full walkthrough.
In outline: start the stack and ingest the corpus, run `poe diagnose` and read the per-stage and
custody evidence for both cases, apply the published rule to attribute the designated miss to one
stage and
to rule another one out, record both, read `infra/profiles/vector-engines.yaml` and record the two
storage layouts, read `infra/profiles/object-store-fidelity.yaml` and record one divergence that
applies here, run `poe attribution` and then `poe verify`, open your pull request, and read the
CMS protected held-out check's result.

## Operational limits

This local system does not authenticate users, terminate TLS, or manage production secrets.
A retrieval request states its own tenancy and clearance, so that context is an asserted
identity rather than a verified one. The Compose PostgreSQL password and the LocalStack access keys
are local-only non-secret credentials. Never place real credentials, personal data, or production
records in this repository, including in `infra/corpus/`.

The diagnosis here makes no production claim either. The dense arm uses a deterministic hashed
embedding rather than a trained one, the corpus is 18 synthetic documents, and the supplied engine
profiles were written for teaching rather than measured. An attribution is a true statement about
*this* pipeline, and a stage that fails here would not necessarily fail in a deployment with a
trained embedding and a real corpus.

The held-out scenario proves that this pipeline handled content it had not seen. It is one
scenario, on one corpus, and it is not a generalization guarantee.

Named volumes preserve local PostgreSQL, Redis, Prometheus, Grafana, and Jaeger state across
`poe stop`. LocalStack object contents are deliberately not persisted; the initializer re-uploads
the supplied corpus artifacts on every start. The `poe reset` command deletes the named volumes.
This topology makes no backup, replication, high-availability, disaster-recovery, capacity,
latency-SLO, or availability claim.

See [JobQueue fidelity](docs/fidelity/JobQueue.md),
[ModelProvider fidelity](docs/fidelity/ModelProvider.md),
[ObjectStore fidelity](docs/fidelity/ObjectStore.md), and
[Retriever fidelity](docs/fidelity/Retriever.md) for the active adapter boundaries. The
[local runtime evidence](docs/fidelity/local-runtime.md) records the current measurement and its
qualification limits.
