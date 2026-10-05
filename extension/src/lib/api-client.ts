// extension/src/lib/api-client.ts
import type {
  ApiResponse,
  VishingScanResponseDTO,
  ProvenanceVerifyResponseDTO,
  DeepfakeResultDTO
} from "../../../packages/shared-types/src";

const API_BASE_URL = "http://localhost:8000/api/v1";

export class TrustGuardApiClient {
  private static async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });

    const envelope: ApiResponse<T> = await res.json();
    if (!envelope.success || !envelope.data) {
      throw new Error(envelope.error?.message || "Unknown TrustGuard API error");
    }
    return envelope.data;
  }

  // Vishing Scan (Anonymous-friendly)
  public static async scanVishingText(text: string, sourceType: "PASTED_TEXT" | "LIVE_PAGE_SCAN" = "PASTED_TEXT"): Promise<VishingScanResponseDTO> {
    return this.request<VishingScanResponseDTO>("/vishing/scan", {
      method: "POST",
      body: JSON.stringify({
        text,
        source_type: sourceType
      })
    });
  }

  // Provenance Verify (Public)
  public static async verifyProvenanceHash(mediaHash: string): Promise<ProvenanceVerifyResponseDTO> {
    return this.request<ProvenanceVerifyResponseDTO>("/provenance/verify", {
      method: "POST",
      body: JSON.stringify({
        media_hash: mediaHash
      })
    });
  }
}
