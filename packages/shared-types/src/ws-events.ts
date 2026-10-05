// packages/shared-types/src/ws-events.ts
import type { DeepfakeJobStatus, DeepfakeResultDTO, RiskSignal } from "./domain";

// ---------- WebSocket event payloads (channel: user:{userId}) ----------
export type TrustGuardWSEventType =
  | "DEEPFAKE_JOB_STATUS_CHANGED"
  | "DEEPFAKE_RESULT_READY"
  | "PROVENANCE_TX_CONFIRMED"
  | "RISK_SIGNAL_RAISED";
 
export interface TrustGuardWSEventBase {
  type: TrustGuardWSEventType;
  sequence: number;   // monotonic per userId, for reconnect replay
  emittedAt: string;
}
 
export type TrustGuardWSEvent =
  | (TrustGuardWSEventBase & {
      type: "DEEPFAKE_JOB_STATUS_CHANGED";
      payload: { jobId: string; status: DeepfakeJobStatus };
    })
  | (TrustGuardWSEventBase & {
      type: "DEEPFAKE_RESULT_READY";
      payload: { jobId: string; result: DeepfakeResultDTO };
    })
  | (TrustGuardWSEventBase & {
      type: "PROVENANCE_TX_CONFIRMED";
      payload: { recordId: string; txHash: string; blockNumber: number };
    })
  | (TrustGuardWSEventBase & {
      type: "RISK_SIGNAL_RAISED";
      payload: RiskSignal;
    });
