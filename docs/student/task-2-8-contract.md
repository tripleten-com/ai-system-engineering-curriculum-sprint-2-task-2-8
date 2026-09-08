# Task 2.8 — Miss attribution and held-out contract

Attribute one designated retrieval miss to exactly one pipeline stage, rule out one other stage
with direct evidence, classify the storage layout each supplied engine profile records, and record
one code from this stack's draft fidelity profile. You change no code.

One of the two misses you are shown is a defect and the other is the system working correctly.
Both look the same from the outside, and separating them is the first thing the published rule
asks you to do.

## The designated investigation, and the case beside it

`infra/corpus/investigation.jsonl` names **two** cases. The first is the one you answer; the
second is there to be compared against, and is graded by nothing.

```shell
poe diagnose                        # both cases
poe diagnose q-dock-seal-log        # the designated investigation
poe diagnose q-produce-humidity-band  # the contrast case
```

| Case | What it is |
|---|---|
| `q-dock-seal-log` | **The designated investigation.** A Coldline shift lead asks a question one of Coldline's own procedures answers. It does not come back. |
| `q-produce-humidity-band` | **The contrast case.** The same caller asks a question a *customer's* procedure answers. It does not come back either. |

Both are misses. Only one is a defect, and telling them apart is the point of the pair.

Each record carries `expected_readable`, which says whether that caller is supposed to be able to
read the target at all. The rule does not take that field's word for it — it reaches the same
conclusion from the evidence, and a supplied check compares the two. If they ever disagreed, this
Task would be wrong rather than your answer.

The inspector runs each query with the stage evidence turned on and prints, for each stage, whether
the target chunk was there. It prints evidence. It does not name a stage.

You can point it at any published query id to compare a miss against a query that works.

## The custody evidence

Every corpus document carries two independent records of where it belongs:

- its **access label**, which is what the retrieval boundary acts on, and
- its **custody record** in `infra/corpus/provenance.jsonl` — the desk that owns it and the source
  it came from.

Across this corpus each custodian appears under exactly one tenancy. So the two records can be
checked against each other, and a document whose label puts it in one tenancy while every other
document from the same desk sits in another is **internally inconsistent**. `poe diagnose` prints
that comparison as its `custody` lines, and you can re-derive it from the two fixture files with no
database at all.

That comparison is what separates the two cases above, and it is the only thing that can.

## The published attribution rule

The rule is ordered, and the order is the whole point. Read it as one question and then five,
each of which only becomes meaningful once the previous one is answered no. It is implemented in
`tests/diagnostics/attribution.py`, and the check applies exactly this rule to exactly the evidence
you read.

**Question 0 comes before everything.** Was the target chunk withheld by the authorization stage,
and does its custody record *agree* with the access label the stage acted on? Then the miss is not
a defect at all: a boundary that withholds another tenancy's content is the boundary working. The
rule returns **no defect** and names no stage.

That outcome is not in the answer contract, and cannot be recorded. It exists so the rule can
decline to blame a stage that did its job.

| Order | Question | Attribution |
|---:|---|---|
| 0 | Was it withheld, with label and custody in **agreement**? | *no defect — not answerable* |
| 1 | Was it withheld, with the custody record **contradicting** the label? | `authorization_filtering` |
| 2 | Did neither search arm surface it, *and* are the query's terms split across chunk boundaries? | `chunking` |
| 3 | Did the sparse arm surface it and the dense arm not? | `embedding` |
| 4 | Did the dense arm surface it and the sparse arm not? | `sparse_matching` |
| 5 | Did both arms surface it, and it still did not come out? | `fusion` |

Two orderings matter here, for opposite reasons.

**Question 0 before 1.** A drop on its own cannot tell a defect from correct enforcement — the
observable behavior is identical. A rule that skipped question 0 would attribute every denial to
`authorization_filtering`, which reads plausibly and would teach you to file the system's correct
behavior as a fault. The custody comparison is what makes the distinction, and it is the only
evidence in this repository that can.

**Question 5 last.** Candidate fusion cannot be blamed for a candidate that only one arm ever
offered it. A chunk one arm never surfaced was not lost by ranking; it was lost by retrieval. That
is the lesson's own common mistake, and the ordering is what prevents it.

If the evidence answers no to all of them — a readable chunk neither arm found, with no split — the
rule refuses to attribute and says so. That is a real possible outcome, not a bug.

A note on where a repair would go, since you are not asked to make one: correcting a mislabelled
tag is a data fix, not a code fix. Nothing in `src/` is wrong in the designated case, which is
part of why attributing it correctly matters.

## What "ruled out" means

A stage is ruled out only when the evidence **positively shows** it did its job for the target
chunk. Absence of evidence never counts: a stage that never saw the chunk is *unobserved*, not
exonerated.

| Stage | Ruled out when |
|---|---|
| `authorization_filtering` | The target chunk is in the readable pool and the constraint dropped nothing — **or** it was withheld and its label agrees with its custody record, which is the stage correctly applying a correct label |
| `chunking` | Some single chunk holds every one of the query's terms that occurs in the document (and there are at least two such terms) |
| `embedding` | The target chunk is in the dense arm's candidate list |
| `sparse_matching` | The target chunk is in the sparse arm's candidate list |
| `fusion` | The target chunk reached fusion **and** came out in the results |

For a miss, `fusion` can never be ruled out — the chunk did not come out. The recorded ruled-out
stage must also differ from the attributed one: a stage cannot be both the cause and proven fine.

The authorization row is the one exception to "absence of evidence never counts", and it is an
exception because the evidence is *present* rather than absent: the stage acted, and what it acted
on is demonstrably labelled right. That applies to the contrast case, not to the designated one —
where the stage acted on a label that is demonstrably wrong.

### How the term rule works

`shared terms` are the query's content tokens that also occur in the target document: lowercase,
split on every run of characters outside `a-z0-9`, tokens shorter than four characters discarded,
and these stop words discarded — `been does each from have must that then this when with`. It is
the same rule the corpus and the cached judge evidence document.

The comparison is **exact-string, and deliberately does not stem.** PostgreSQL's text search does
stem, so the sparse arm can match a passage this rule counts as sharing nothing — which is why the
two are separate lines in the report. The exact rule describes what a reader can verify from the
committed fixtures without a database, and it is conservative: it claims a split, and claims
chunking is fine, less often than a stemming rule would.

## The supplied engine profiles

`infra/profiles/vector-engines.yaml` is the graded source; `docs/architecture/vector-engines.md` is
the same content in prose.

| Code | Pattern |
|---|---|
| `integrated_relational_table` | Embeddings are typed columns inside relational rows, beside the entity data |
| `dedicated_vector_payload_store` | Vectors and payloads live in collections of a service built for similarity search |

Both profiles answer the **same retrieval need** under the **same declared deployment assumptions**,
which the profile states explicitly: comparing engines against different needs, or against
undisclosed assumptions, tells you about the assumptions rather than about the engines. Each profile
also records its version, its source references, and who owns backup, restore, and synchronization.

Classify each engine's layout from the profile. Do not install Qdrant, and do not deploy anything:
the comparison is a reading exercise, and the check reads the file this Task supplied rather than
grading you on outside knowledge about these products.

No preference is graded. Both layouts are legitimate, and no performance, scale, or cost claim is
made or assessed.

## The object-store fidelity evidence

`infra/profiles/object-store-fidelity.yaml` is the graded source;
`docs/fidelity/ObjectStore.md` is the prose form. LocalStack is an Amazon Web Services (AWS)
emulator, and the profile pins which build, edition, and configuration is running — a limitation
observed on one configuration is not a limitation of LocalStack in general.

`poe fidelity-observations` checks the profile's local observations. Its invented-credential
listing check does not test IAM or bucket-policy enforcement. Its single-page listing check
records a gap in pagination coverage; AWS can return the same single-page result.

**Release qualification remains unresolved.** The current draft accepts both existing codes,
but a coverage gap alone does not establish the emulator divergence required by proposed
ADR009-R08. Check success or enum membership cannot certify that release requirement. Keep the
draft answer contract unchanged until the qualification issue is reviewed.

The profile also records the codes that were **withdrawn**, with the reason, and those are absent
from the answer contract entirely — you cannot record one. Read those reasons too: one was
withdrawn because no code here can reach it, and the other because the claim it rested on was
untrue of AWS. A divergence nothing here can encounter is not a limitation of your system, and a
divergence whose premise is false is not a limitation at all.

## The held-out evaluation

Sprint 2 has exactly one held-out scenario. The CMS grading integration runs it in a protected
environment after the public checks and reports its result for the same submission commit.

- You do not run it, download it, or inspect it. The scenario reaches the grader from private assets
  and is never committed to this repository.
- What *is* committed is the grading procedure, `tests/contract/held_out_review.py`. It ingests the
  scenario's own documents through the supplied document API, runs its queries, requires each to
  retrieve the document the scenario expects, and requires a caller from another tenancy to
  retrieve none of them. So it exercises the data layer, the Task 2.4 authorization boundary, and
  both retrieval arms against content the public corpus does not contain.
- `poe held-out-dry-run` runs that procedure against a fake scenario written in the open, so you
  can see the mechanism work. It grades nothing.
- The grader reports only pass, fail, or "contact course support". Nothing about the scenario appears in the
  output, and no exception text is printed either — a traceback could carry a held-out document
  into a log you can read.

### What it grades, and what it does not

Read this part carefully, because it is easy to assume more than it does.

Task 2.8 is an **answers-only** Task: you change no application code. So the protected job runs
the **supplied** tree, at the base commit, rather than your branch — deliberately, and not as a
shortcut. The CMS worker holds the private scenario, and nothing candidate-authored executes inside it.
Checking out your branch would run your `bootstrap.py`, your compose files, and your Poe tasks in
that job, any of which could plant code that later runs in the step holding the secret.

Two consequences follow, and both are stated rather than glossed:

1. The scenario grades the **delivered retrieval pipeline** against unseen content. It is a release
   check on this Task's system, surfaced on your pull request — not a measurement of your answers.
   Your answers are graded by the public checks and the protected answer key.
2. What the job checks about *your* submission is the **boundary**: if the pull request changes
   anything outside `submission.yaml` and `tests/student/`, it refuses to grade and reports a
   failure. A held-out result about a modified pipeline would be a result about a different system.

The result is reported as a commit status on your exact head commit, with three outcomes kept
apart: `success`, `failure`, and `error`. An `error` means the run could not be carried out — a
missing secret, an unusable scenario, a stack that did not start — and never that your submission
was wrong.

## The answers

| Field | Type | Evidence source |
|---|---|---|
| `attributed_failure_stage` | one of five stages | `poe diagnose`, through the ordered rule above |
| `ruled_out_stage` | one of five stages | the same evidence, through the ruled-out table above |
| `pgvector_storage_layout` | one of two layouts | `infra/profiles/vector-engines.yaml` |
| `qdrant_storage_layout` | one of two layouts | the same profile |
| `fidelity_limitation` | one current draft code; release qualification pending | `infra/profiles/object-store-fidelity.yaml` |

## What the checks verify

| Check | What it looks at |
|---|---|
| `test_the_designated_query_still_misses_its_target_chunk` | The supplied system: the target is still withheld, still absent from the results, and still withheld *because* its label contradicts its custody record |
| `test_attributed_stage_matches_the_stage_evidence` | The recorded stage against the rule applied to live evidence |
| `test_ruled_out_stage_is_proven_by_the_stage_evidence` | The recorded stage against the set the evidence positively proves |
| `test_storage_layout_classifications_match_the_supplied_profiles` | Both classifications against `vector-engines.yaml` |
| `test_recorded_fidelity_limitation_is_a_qualified_code` | The recorded code against the current draft list in `object-store-fidelity.yaml`; this membership check does not certify release qualification |

Two supplied modules assess nothing and exist to keep the Task honest.
`tests/contract/test_object_store_fidelity.py` reproduces each published fidelity observation and
checks that neither withdrawn code has crept back.
`tests/contract/test_authorization_diagnosis.py` (`poe diagnosis-checks`) exercises both cases
above: it asserts that the designated miss is attributed to the access boundary, that the contrast
case comes back as no defect, and that exactly one document in the corpus disagrees with its
custody record — because the designated case is only identifiable while every other document
agrees with its own. `poe verify` runs both.

## Student-editable paths

- `submission.yaml`
- anything you add under `tests/student/`

Everything else is supplied, including the diagnostic, the attribution rule, the profiles, the
investigation fixture, and the held-out grading procedure. The held-out review grades the supplied
pipeline, so its CI job refuses to grade a pull request that changed anything outside these two
surfaces.
