# .ai/CONVENTIONS.md
 
## Response envelope (every REST response, success or error)
```json
{
  "success": boolean,
  "data": <object|array|null>,
  "error": { "code": string, "message": string, "field"?: string } | null,
  "requestId": string   // UUID, echoed from the X-Request-Id header
}
```
 
## Error code -> HTTP status
- `VALIDATION_ERROR`            -> 422
- `NOT_FOUND`                   -> 404
- `MEDIA_ALREADY_REGISTERED`    -> 409   (provenance_records hash collision)
- `FORBIDDEN_ROLE`              -> 403
- `UNAUTHENTICATED`             -> 401
- `RATE_LIMITED`                -> 429
- `UPSTREAM_TIMEOUT`            -> 502   (inference service / chain RPC)
- `CHAIN_TX_FAILED`             -> 502
- `IDEMPOTENCY_KEY_REUSED`      -> 200   (returns the original result)
- `INTERNAL`                    -> 500
 
## Naming
- Database & Python:      `snake_case`
- JSON wire format:       `camelCase`
  (Pydantic `alias_generator=to_camel`, `populate_by_name=True`)
- TypeScript types:       `PascalCase` types/interfaces, `camelCase` fields
- URL paths:               `kebab-case`, plural nouns (`/deepfake-jobs`)
- Celery task names:       `"<module>.<verb>_<noun>"`
  e.g. `"blockchain_anchor.submit_registration"`
 
## PII / content-safety rule (applies to vishing_scans specifically)
- Before INSERT, the API layer redacts any digit run of length >= 6
  (covers card numbers, account numbers, OTPs) from `text_snippet` with
  a fixed mask `[REDACTED_NUMBERS]`. The fraud-registry value of a scan is the SCAM
  LANGUAGE, not the victim's account data -- never persist the latter.
- Risk output is always phrased as a SIGNAL, never an accusation:
  "possible vishing pattern detected", not "this caller is a
  scammer" -- mirrors the assistive-AI pattern, not a final determination, and avoids defamation exposure.
 
## Blockchain conventions
- The signing key lives only in the worker's secrets-manager-injected
  environment, never in services/api or in git.
- A transaction is only ever submitted after its `blockchain_tx_log` row
  (with an allocated, uniquely-constrained nonce) is committed.
- `tx_confirmation_poller.py` polls at a fixed interval and marks
  `CONFIRMED` only after N block confirmations (configurable; default 5
  on Polygon Amoy) to tolerate shallow reorgs.
 
## Error handling pattern
- Domain exceptions live in `modules/<module>/exceptions.py`, subclass
  `AppError(code, http_status, message)`.
- One FastAPI `exception_handler(AppError)` maps to the envelope above.
- Celery tasks: `autoretry_for=(UpstreamTimeoutError,)`, `max_retries=3`,
  exponential backoff ($2^n \times 5\text{s}$). A chain-tx task that exhausts
  retries sets `anchor_status=FAILED` and raises a RISK-free internal
  alert for an operator -- never leaves a row stuck `PENDING` forever.
 
## Git / ownership
- Trunk-based development, short-lived branches:
  `<member-initials>/<module>-<short-desc>`
- Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`).
- Module ownership: CV/deepfake model -> `services/inference`; vishing NLP -> `modules/vishing`; blockchain
  -> `chain/` + `modules/provenance` + `blockchain_anchor` task; backend
  lead -> `services/api` core + `db/`; frontend -> `extension/`; devops ->
  `infra/` + `services/inference` deployment.
