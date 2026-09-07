# ObjectStore fidelity

The active adapter is `src/adapters/object_store/s3.py`, an S3-compatible client pointed at the
supplied LocalStack container. **LocalStack is an Amazon Web Services (AWS) emulator**, not
managed object storage.

What it emulates depends on which build, edition, and configuration is running, so this is
pinned rather than implied. A limitation observed on one configuration is not a limitation of
LocalStack in general.

| Pinned | Value |
|---|---|
| Product and edition | LocalStack Community |
| Image | `localstack/localstack:4.9.1` |
| Digest | `sha256:ef90c3d6d69e36752d0154f9bc21099fc70dfbffc99a0145a6d7d04a721a6124` |
| Configuration | `SERVICES=s3`, `PERSISTENCE=0`, `EAGER_SERVICE_LOADING=1`, `DEBUG=0` |
| Region | `us-east-1` |
| Exercised API behavior | `CreateBucket`, `HeadBucket`, `PutObject`, `GetObject`, `ListObjectsV2` |

A divergence in an operation this repository never calls is outside the scope of the codes
below.

## What the local runtime proves

- The published `ObjectStore` port shape: `read`, `write`, and `list_keys`.
- That application code reaches stored objects only through that port. No module outside
  `src/adapters/object_store/` imports `boto3` or `botocore`, and both the authoring integrity
  check and a public contract test fail if one does.
- Bucket provisioning is idempotent, so a repeat start, a restart, and a Codespaces resume all
  converge on the same bucket and the same corpus artifacts.
- Provider errors are translated at the boundary: a missing key becomes `ObjectNotFound` and any
  other provider or transport error becomes `ObjectStoreUnavailable`.
- The corpus and its custody record are read from object storage rather than from the container
  filesystem, which is why the Task 2.1 boundary is observable rather than asserted.

## What the local runtime does not prove

LocalStack answering a request establishes nothing about managed S3. In particular this runtime
does **not** prove:

| Not proven | Why it matters |
|---|---|
| IAM and bucket-policy evaluation | The local endpoint accepts development credentials and evaluates no least-privilege policy. A call that succeeds here can be denied in a managed account. |
| Durability and replication | There is no multi-facility storage, no versioning guarantee, and no restore path behind this container. |
| Listing behavior at scale | Amazon S3 caps a `ListObjectsV2` response at 1000 keys and sets `IsTruncated` with a continuation token. This corpus is two objects, so the adapter's pagination loop exits on its first page and is never exercised here. |
| Multipart upload and large-object handling | The corpus artifacts are small; no multipart path is exercised. |
| Encryption at rest, key management, access logging, or object lock | None of these are configured or emulated. |
| Throughput, latency, request cost, or throttling | The container shares one host; no measurement here is a managed-service figure. |

## The qualified divergence codes

Task 2.8 asks for one of these codes.
[`infra/profiles/object-store-fidelity.yaml`](../../infra/profiles/object-store-fidelity.yaml) is
the machine-readable form and is what the check reads; the answer enum matches it exactly.

A code is published only when both halves of its evidence exist: an observation you can
reproduce against the pinned emulator above, and an authoritative description of what AWS does
instead. Sounding plausible is not a qualification. Each observation has a matching check in
`tests/contract/test_object_store_fidelity.py`, so a published claim cannot quietly stop being
true.

### `policy_enforcement_gap`

The local endpoint does not evaluate credentials, IAM identity policy, or bucket policy, so an
authorization outcome observed here says nothing about whether AWS would permit the same call.

- **Observation.** Signing a `ListObjectsV2` request for the corpus bucket with an *invented*
  access key and secret returns the bucket contents rather than an error.
- **AWS behavior.** AWS rejects a request whose signature does not verify against a real access
  key, and separately evaluates IAM identity policy and any bucket policy on every request,
  denying by default when nothing allows the action.
- **Scope.** Authorization only. It implies nothing about durability, consistency, or performance.

### `listing_pagination_not_exercised`

The adapter loops over continuation tokens to page a listing, and this corpus is too small to
ever truncate one, so that loop is never exercised locally.

- **Observation.** `ListObjectsV2` on the corpus prefix returns two keys with `IsTruncated`
  false and no `NextContinuationToken`, so `S3ObjectStore._list_keys` exits after its first page.
- **AWS behavior.** AWS returns at most 1000 keys per `ListObjectsV2` response, sets
  `IsTruncated` when more remain, and supplies `NextContinuationToken` for the next page.
- **Scope.** The listing path only. It describes what this environment leaves untested, not a
  defect in the adapter.

## Codes withdrawn from the earlier draft list

Recorded rather than deleted, so the withdrawal is reviewable. Neither is an accepted answer.

| Withdrawn | Why |
|---|---|
| `distributed_consistency_difference` | The claim it rested on is false. Amazon S3 has provided strong read-after-write consistency for PUT and DELETE, **including for list operations**, since December 2020. Locally, writing an object and immediately reading and listing it also succeeds, so there is no observed divergence to describe. |
| `upload_part_handling_divergence` | No code here can reach it. `S3ObjectStore.write` calls `PutObject` with a whole body, and the adapter exposes no create-multipart, upload-part, or complete-multipart path. A check asserts that, so the reason cannot quietly stop being true. |

A divergence no code here can reach is a difference between the emulator and AWS, but it is not
a limitation *of this system*. A divergence whose premise is untrue is not a limitation at all.

Object contents are deliberately **not persisted** between runs. The initializer re-uploads the
supplied artifacts on every start, so no state accumulates and no run depends on a previous one.

## Credentials

The values in `compose.yaml` are LocalStack development strings. They are not secrets, they grant
nothing outside the local Compose network, and they must never be replaced with a real account
credential in this repository. A managed deployment supplies credentials through its own protected
configuration, never through a file in a student repository.
