# ADR 001: Add Qdrant as a vector store backend

**Status:** Accepted  
**Date:** 2026-05-05

## Context

The production backend uses AWS OpenSearch to store and search 15M image signatures
produced by the Goldberg algorithm. OpenSearch is expensive to operate, requires
careful index tuning for ANN workloads, and the managed AWS service adds operational
overhead. A purpose-built vector database should be cheaper and faster for this use case.

## Decision

Add a `SignatureQdrant` driver to `image-match` backed by [Qdrant](https://qdrant.tech/).

Key design choices:

- **Same distance formula.** The Goldberg signature is stored as a Qdrant float32
  vector. Qdrant's HNSW index retrieves ANN candidates; the exact `normalized_distance`
  formula from `signature_database_base.py` is then applied in Python. Distance values
  are identical to those returned by `SignatureES7`/`SignatureES8`.

- **Migration is idempotent.** Each point's ID is a deterministic UUID derived from
  the image path (`md5(path)`), so re-running the migration script is safe.

- **Shadow mode before cutover.** During migration the backend runs both OpenSearch
  and Qdrant for every search request. OpenSearch serves the response; Qdrant runs in
  a background thread and discrepancies are logged. Shadow mode runs for ≥ 7 days
  before any cutover.

- **Recall gate.** A validation script compares ES vs Qdrant results on a random
  sample. Cutover only proceeds when mean recall ≥ 0.97 and P5 recall ≥ 0.90.

## Consequences

- `qdrant-client>=1.17.1` added as an optional dependency (`[qdrant]` extra).
- `SignatureQdrant` is a standalone driver; it does not extend `_SignatureESBase`.
- The ES7/ES8 drivers are unchanged — no regressions for existing users.
- Production infrastructure: single EC2 instance + EFS volume (storage survives
  instance replacement); daily snapshots to S3 with a 30-day lifecycle rule.
