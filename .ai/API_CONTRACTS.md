# .ai/API_CONTRACTS.md

## Route Table

| Method | Path | Auth | Request -> Response | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Public | `RegisterRequest` -> `AuthTokenResponse` | USER or CREATOR role at sign-up. |
| `POST` | `/api/v1/auth/login` | Public | `LoginRequest` -> `AuthTokenResponse` | email + password. |
| `POST` | `/api/v1/auth/refresh` | Refresh token | `RefreshRequest` -> `AuthTokenResponse` | Rotates the refresh token. |
| `POST` | `/api/v1/vishing/scan` | Public (anonymous allowed) | `VishingScanRequest` -> `VishingScanResponse` | Synchronous, <150ms p95 budget. |
| `GET` | `/api/v1/vishing/scans/{id}` | Owner \| ADMIN | -- -> `VishingScanResponse` | Retrieve a past scan. |
| `POST` | `/api/v1/deepfake/jobs` | Bearer | `DeepfakeJobCreateRequest` -> `DeepfakeJobCreateResponse` | Issues a pre-signed upload URL. |
| `POST` | `/api/v1/deepfake/jobs/{id}/confirm` | Bearer, owner | -- -> `DeepfakeJobStatusResponse` | Enqueues frame extraction + analysis. |
| `GET` | `/api/v1/deepfake/jobs/{id}` | Bearer, owner | -- -> `DeepfakeJobStatusResponse` | Poll fallback; WS is primary (§2.2). |
| `GET` | `/api/v1/deepfake/jobs/{id}/result` | Bearer, owner | -- -> `DeepfakeResultOut` | Available once status=DONE. |
| `POST` | `/api/v1/provenance/register` | Bearer (CREATOR) | `ProvenanceRegisterRequest` -> `ProvenanceRegisterResponse` | 409 on existing hash, checked before chain call. |
| `POST` | `/api/v1/provenance/verify` | Public | `ProvenanceVerifyRequest` -> `ProvenanceVerifyResponse` | Exact + near-match (pHash) lookup. |
| `GET` | `/api/v1/incidents` | Bearer | Query: `source_type`, `page` -> `IncidentOut[]` | Unified feed across both detectors. |
| `GET` | `/api/v1/admin/keyword-clusters` | Bearer (ADMIN) | -- -> `KeywordClusterOut[]` | Vishing rule management. |
| `POST` | `/api/v1/admin/keyword-clusters` | Bearer (ADMIN) | `KeywordClusterCreateRequest` -> `KeywordClusterOut` | No redeploy needed to add a new scam phrase. |
| `WS` | `/api/v1/ws/updates` | Bearer via query token | `subscribe: {job_id \| record_id}` -> `TrustGuardWSEvent` stream | Deepfake job + provenance tx events. |

## Standard Response Envelope
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "requestId": "uuid"
}
```

On Error:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Detailed error explanation",
    "field": "text"
  },
  "requestId": "uuid"
}
```

## Smart Contract ABI Contract
The smart-contract ABI (`chain/artifacts/ProvenanceRegistry.json`, produced by Hardhat compilation) is treated as a generated artifact, never hand-edited, and regenerated whenever `ProvenanceRegistry.sol` changes.
