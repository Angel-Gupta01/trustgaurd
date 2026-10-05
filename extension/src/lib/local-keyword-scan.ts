// extension/src/lib/local-keyword-scan.ts

export interface LocalScanResult {
  hasSuspiciousSignal: boolean;
  score: number;
  flaggedKeywords: string[];
}

// Small bundled baseline keyword list for zero-latency offline first pass
export const OFFLINE_BASELINE_KEYWORDS: string[] = [
  "act immediately",
  "account suspended",
  "verify password",
  "one time password",
  "otp",
  "cvv",
  "arrest warrant",
  "court summons",
  "legal action",
  "wire transfer",
  "urgent notice",
  "failure to respond",
  "install anydesk",
  "install quicksupport"
];

export function scanTextLocally(text: string): LocalScanResult {
  const normalized = text.toLowerCase();
  const flagged: string[] = [];

  for (const kw of OFFLINE_BASELINE_KEYWORDS) {
    if (normalized.includes(kw)) {
      flagged.push(kw);
    }
  }

  const score = Math.min(flagged.length * 25, 100);

  return {
    hasSuspiciousSignal: flagged.length > 0,
    score,
    flaggedKeywords: flagged
  };
}
