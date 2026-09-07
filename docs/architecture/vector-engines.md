# Vector engine technical profiles

Coldline stores its embeddings in PostgreSQL with the pgvector extension. As volume grows,
engineering teams weigh that against a dedicated vector engine such as Qdrant. This page is the
readable form of the two supplied profiles in
[`infra/profiles/vector-engines.yaml`](../../infra/profiles/vector-engines.yaml), which is what the
Task 2.8 checks read.

Nothing here is a recommendation, and nothing here was measured. Task 2.8 asks a factual question:
which storage layout does each engine implement?

## The shared retrieval need, and the assumptions declared for both

Comparing two engines against different needs, or against undisclosed assumptions, produces a
conclusion about the assumptions rather than about the engines. Both profiles answer the same
need under the same declared assumptions.

**The need.** Hybrid retrieval over a tenant-partitioned corpus of procedural documents: dense
similarity and full-text search over the same chunks, an access predicate applied at query time
rather than to the results, and per-stage evidence recoverable for one query.

**The declared assumptions.** A single write-primary datastore already owns the documents and
chunks; one deployment environment, with no multi-region or cross-account topology; corpus scale
in the thousands of chunks rather than the millions; the access predicate must be enforced inside
the search rather than after it; and operational ownership is one small team rather than a
dedicated platform group.

## The two storage layout patterns

| Code | Pattern |
|---|---|
| `integrated_relational_table` | Vector embeddings live as typed columns inside relational rows, beside the transactional entity data they belong to. One schema, one query planner, one durability boundary. |
| `dedicated_vector_payload_store` | Vectors and their metadata payloads live in collections maintained by a service built for similarity search. The vector store is a separate system from whichever database owns the entities. |

## PostgreSQL with pgvector

**Deployed in this repository**, as PostgreSQL 16 with pgvector from
`pgvector/pgvector:pg16`, pinned by digest in `compose.yaml`. You can read every claim below
out of the code.

**Storage and layout.** `infra/postgres/002_retrieval_corpus.sql` declares:

```sql
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents (document_id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(64) NOT NULL,
    tenant_id TEXT NOT NULL,
    ...
```

The embedding is a column. It sits in the same row as the chunk text, the tenancy label, and the
provenance record, and it is created, updated, and deleted with that row.

**Filtering.** One query plan. The access predicate and the distance ordering are written into the
same SQL statement, so the planner decides how to combine them. That is exactly why the Task 2.4
access constraint is a query-time filter and not a post-filter: look at
`src/adapters/retriever/postgres_hybrid.py` and you will find the constraint clause inside both
arms' `WHERE`, not applied to their results.

**Operational footprint.** One datastore to run, back up, and restore. The embeddings are inside
the same transaction boundary as the documents they belong to, so a restore cannot recover one
without the other, and a schema migration covers both.

**Backup, restore, and synchronization.** One backup covers documents, chunks, and vectors
together, and one restore returns them to a single consistent point. There is no second copy to
keep in step, so there is no synchronization path to own and no reindex-after-write step.

## Qdrant

**Not installed, not deployed, and not required by this Task.** Do not try to run it. The
comparison is a reading exercise; the profile is what the checks grade.

The rows below describe the Qdrant 1.x documented data model — collections, points, payloads,
payload filtering, and collection snapshots. No version is pinned, because nothing here runs it,
and nothing below was observed in a running cluster.

**Storage and layout.** Qdrant organizes data into *collections* of *points*. Each point carries a
vector and a JSON payload. There is no relational schema and no SQL planner: the collection exists
to serve similarity search over those points, and whatever database owns the business entities is a
different system.

**Filtering.** Payload conditions are evaluated against the point payload, either during index
traversal or as a stage around it. The filter and the distance search are parts of one
vector-search request rather than of one relational plan.

**Operational footprint.** A second service alongside the entity database: its own cluster, its own
snapshot and restore lifecycle, and a synchronization path to keep its points consistent with the
source of truth. That synchronization is the cost the integrated layout does not have, and the
independence is the benefit the integrated layout does not have.

**Backup, restore, and synchronization.** Two independent lifecycles: a collection snapshot and
the entity database's own backup are taken and restored separately, so a restore has to reconcile
the point in time each came from. Synchronization is owned by the application — every write to the
source of truth needs a matching upsert or delete against the collection, plus a way to detect and
repair divergence after a partial failure or a reindex.

## What this comparison does not claim

- No performance, scale, recall, or cost figure. None was measured, and this corpus of 18 documents
  could not support one.
- No preference. Both layouts are legitimate; which one fits depends on volume, team, and
  operational appetite, and this Task grades neither a recommendation nor an opinion.
- The Qdrant rows describe a documented data model, not an observation of a running cluster.
- CME independently verifies both profiles and the accepted answers before release. Until then
  the profile records `qualification.confirmed_by_cme: false`.
