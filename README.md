# TRUSTGUARD 🛡️
### Unified Social-Engineering (Vishing) Detection & Deepfake / Content-Provenance Defense Extension
*Engineering Handoff · Foundation-to-Build Phase · Smart India Hackathon (SIH 2026)*

TrustGuard is an end-to-end security system unifying real-time text-based vishing/social-engineering detection with computer-vision deepfake analysis and on-chain content provenance verification.

---

## 🏛️ System Architecture

- **Client**: Manifest V3 Chrome Extension (`extension/`) with passive page-text scanning, paste-and-check popup, media context menu, and local keyword matching.
- **API Monolith**: FastAPI (`services/api/`) orchestrating auth, synchronous CPU-only vishing scoring (<150ms budget), deepfake job lifecycle, provenance deduplication, and unified incidents feed.
- **Deepfake Inference**: Dedicated PyTorch service (`services/inference/`) exposing a gRPC bidirectional frame-streaming endpoint with face-detection, CNN/ViT classification, and Grad-CAM heatmap generation.
- **Background Workers**: Celery + Redis (`services/worker/`) handling ffmpeg frame extraction, deepfake orchestration, and nonce-managed blockchain anchoring.
- **Blockchain**: Solidity smart contract (`chain/contracts/ProvenanceRegistry.sol`) on Polygon Amoy testnet for cryptographic content provenance.
- **Data Stores**: PostgreSQL 16 (system of record), Redis 7 (broker/cache/rate-limit), MinIO / S3 (short-retention object storage).

---

## 📁 Repository Layout

```
trustguard/
├── .ai/                      # Architecture, canonical schema, conventions & API contracts
│   ├── ARCHITECTURE.md
│   ├── SCHEMA.sql
│   ├── API_CONTRACTS.md
│   └── CONVENTIONS.md
├── chain/                    # Hardhat smart contract project
│   └── contracts/ProvenanceRegistry.sol
├── extension/                # Manifest V3 browser extension (React + TypeScript + Vite)
├── infra/                    # Docker Compose & deployment topologies
│   └── docker-compose.yml
├── packages/
│   └── shared-types/         # Shared domain, WebSocket events, and API envelope contracts
├── services/
│   ├── api/                  # FastAPI modular monolith
│   ├── inference/            # PyTorch Deepfake inference gRPC service
│   └── worker/               # Celery async task workers
└── scripts/                  # Seed scripts, schema dump, type generation
```

---

## 🚀 Quick Start (Local Development)

1. **Start Infrastructure**:
   ```bash
   cd infra && docker-compose up -d postgres redis minio
   ```
2. **Apply Database Schema**:
   Execute `.ai/SCHEMA.sql` against PostgreSQL 16.
3. **Run API Monolith**:
   ```bash
   cd services/api
   uvicorn trustguard_api.main:app --reload --port 8000
   ```
