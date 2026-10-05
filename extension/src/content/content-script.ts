// extension/src/content/content-script.ts
import { scanTextLocally } from "../lib/local-keyword-scan";

console.log("[TrustGuard] Content script initialized on:", window.location.hostname);

// Context-menu listener for selected text or media inspection
document.addEventListener("selectionchange", () => {
  const selection = window.getSelection()?.toString().trim();
  if (selection && selection.length > 20) {
    const localResult = scanTextLocally(selection);
    if (localResult.hasSuspiciousSignal) {
      console.warn("[TrustGuard] Local suspicious vishing signal in selection:", localResult);
      chrome.runtime.sendMessage({
        type: "SUSPICIOUS_TEXT_SELECTION",
        payload: {
          text: selection.slice(0, 1000),
          localScore: localResult.score,
          flagged: localResult.flaggedKeywords
        }
      });
    }
  }
});

// Passive page-level first pass (respecting allowlist)
window.addEventListener("DOMContentLoaded", () => {
  const bodyText = document.body?.innerText || "";
  if (bodyText.length > 50) {
    const preview = bodyText.slice(0, 3000);
    const result = scanTextLocally(preview);
    if (result.score >= 50) {
      chrome.runtime.sendMessage({
        type: "PAGE_SCAN_ALERT",
        payload: {
          url: window.location.href,
          score: result.score,
          flaggedKeywords: result.flaggedKeywords
        }
      });
    }
  }
});
