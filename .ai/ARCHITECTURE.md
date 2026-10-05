# .ai/ARCHITECTURE.md
 
## Paradigm
Modular monolith (services/api) + a dedicated GPU-capable inference
service (services/inference) + async task workers (services/worker).
See §1.1 of the blueprint for the full justification, including why
vishing scoring stays synchronous while deepfake inference does not.
 
## Hard rules for AI code-gen tools and contributors
 
1. `modules/vishing/service.py` MUST remain synchronous, in-process,
   and CPU-only. If a future model requires GPU or exceeds a ~150ms
   p95 budget, split it into its own service -- do not silently make
   the vishing path async, which would break the extension's
   real-time scanning UX.
 
2. `modules/deepfake/service.py` NEVER calls the PyTorch model
   in-process. It always calls services/inference over gRPC. This
   keeps the API process free of GPU dependencies entirely.
 
3. Domain modules under services/api/trustguard_api/modules/* own
   their own SQLAlchemy models. Cross-module access is ONLY through a
   module's public service.py functions.
 
4. Every Celery task MUST be idempotent. blockchain_anchor.py in
   particular must allocate its nonce via a DB row in
   blockchain_tx_log inside the SAME transaction that marks the
   provenance_records row SUBMITTED -- never sign a transaction before
   that row is committed (§6.1 nonce-race mitigation).
 
5. provenance_records.media_hash is globally UNIQUE. The service layer
   MUST check for an existing row before ever submitting a chain
   transaction -- a transaction expected to revert is a wasted gas
   spend and a worker-retry footgun.
 
6. deepfake_jobs.status and provenance_records.anchor_status are each
   mutated ONLY by their owning module's state-machine helper, never
   by a direct UPDATE from another module.
 
7. Model weights (inference service) and the blockchain signing key
   (worker) are never committed to git. Weights load from object
   storage at process start; the signing key comes from a secrets
   manager, never an environment file in the repo.
 
8. Every risk-producing module (vishing, deepfake) writes exactly one
   row to `incidents` per detection event, in the shared RiskSignal
   shape -- the extension and dashboard render ONE alert component
   regardless of source_type.
 
9. .ai/SCHEMA.sql is a generated artifact (scripts/dump_schema.sh, run
   in CI after every Alembic migration). Never hand-edit it.
