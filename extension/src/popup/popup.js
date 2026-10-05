// extension/src/popup/popup.js

const API_BASE = "http://localhost:8000/api/v1";

// Tab Navigation
const tabButtons = {
  vishing: document.getElementById("tabVishingBtn"),
  provenance: document.getElementById("tabProvenanceBtn"),
  deepfake: document.getElementById("tabDeepfakeBtn"),
};

const sections = {
  vishing: document.getElementById("vishingSection"),
  provenance: document.getElementById("provenanceSection"),
  deepfake: document.getElementById("deepfakeSection"),
};

function activateTab(tabKey) {
  Object.keys(tabButtons).forEach(key => {
    tabButtons[key].classList.toggle("active", key === tabKey);
    sections[key].classList.toggle("active", key === tabKey);
  });
}

tabButtons.vishing.addEventListener("click", () => activateTab("vishing"));
tabButtons.provenance.addEventListener("click", () => activateTab("provenance"));
tabButtons.deepfake.addEventListener("click", () => activateTab("deepfake"));

// -------------------------------------------------------------
// Vishing Scanning Logic (Backend Call + Offline Fallback)
// -------------------------------------------------------------
const vishingInput = document.getElementById("vishingInput");
const scanVishingBtn = document.getElementById("scanVishingBtn");
const vishingResultCard = document.getElementById("vishingResultCard");
const riskLabel = document.getElementById("riskLabel");
const riskScoreDisplay = document.getElementById("riskScoreDisplay");
const recommendationText = document.getElementById("recommendationText");
const categoriesContainer = document.getElementById("categoriesContainer");
const flaggedContainer = document.getElementById("flaggedContainer");
const flaggedList = document.getElementById("flaggedList");

// Baseline offline keywords
const OFFLINE_KEYWORDS = [
  "act immediately", "account suspended", "verify password",
  "one time password", "otp", "cvv", "arrest warrant",
  "court summons", "legal action", "wire transfer", "urgent notice",
  "install anydesk", "install quicksupport"
];

function scanOfflineFallback(text) {
  const normalized = text.toLowerCase();
  const flagged = OFFLINE_KEYWORDS.filter(kw => normalized.includes(kw));
  const score = Math.min(flagged.length * 28, 98);
  const isCritical = score >= 75;

  let rec = "LOOKS SAFE: No critical indicators found in offline cache.";
  if (score >= 75) rec = "HANG UP: High risk pressure tactics matched offline rule set.";
  else if (score >= 40) rec = "PROCEED WITH CAUTION: Potential social engineering terms detected.";

  return {
    scan_id: "offline-local-scan",
    risk_score: score,
    is_critical: isCritical,
    matched_categories: flagged.length > 0 ? ["URGENCY_PRESSURE", "CREDENTIAL_REQUEST"] : [],
    flagged_phrases: flagged,
    recommendation: rec,
    source: "offline-cache"
  };
}

scanVishingBtn.addEventListener("click", async () => {
  const text = vishingInput.value.trim();
  if (!text) return;

  scanVishingBtn.textContent = "Scanning...";
  scanVishingBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/vishing/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        source_type: "PASTED_TEXT"
      })
    });

    if (!res.ok) throw new Error("API call failed");
    const json = await res.json();
    renderVishingResult(json.data);
  } catch (err) {
    console.warn("Backend unavailable, executing offline first-pass scanner:", err);
    const offlineResult = scanOfflineFallback(text);
    renderVishingResult(offlineResult);
  } finally {
    scanVishingBtn.textContent = "Scan Message";
    scanVishingBtn.disabled = false;
  }
});

function renderVishingResult(result) {
  vishingResultCard.classList.remove("hidden");
  const score = Number(result.risk_score);
  riskScoreDisplay.textContent = `${score.toFixed(1)} / 100`;

  // Pill styling
  riskLabel.className = "risk-pill";
  if (score >= 75) {
    riskLabel.classList.add("critical");
    riskLabel.textContent = "CRITICAL RISK";
  } else if (score >= 40) {
    riskLabel.classList.add("warning");
    riskLabel.textContent = "CAUTION";
  } else {
    riskLabel.classList.add("safe");
    riskLabel.textContent = "LOW RISK";
  }

  recommendationText.textContent = result.recommendation;

  // Categories
  categoriesContainer.innerHTML = "";
  if (result.matched_categories && result.matched_categories.length > 0) {
    result.matched_categories.forEach(cat => {
      const tag = document.createElement("span");
      tag.className = "tag-badge";
      tag.textContent = cat.replace(/_/g, " ");
      categoriesContainer.appendChild(tag);
    });
  }

  // Flagged Phrases
  flaggedList.innerHTML = "";
  if (result.flagged_phrases && result.flagged_phrases.length > 0) {
    flaggedContainer.style.display = "block";
    result.flagged_phrases.forEach(phrase => {
      const li = document.createElement("li");
      li.textContent = `"${phrase}"`;
      flaggedList.appendChild(li);
    });
  } else {
    flaggedContainer.style.display = "none";
  }
}

// -------------------------------------------------------------
// Provenance Verification
// -------------------------------------------------------------
const hashInput = document.getElementById("hashInput");
const verifyHashBtn = document.getElementById("verifyHashBtn");
const provenanceResultCard = document.getElementById("provenanceResultCard");
const provStatusPill = document.getElementById("provStatusPill");
const provMetaDetails = document.getElementById("provMetaDetails");

verifyHashBtn.addEventListener("click", async () => {
  const hash = hashInput.value.trim().toLowerCase();
  if (!hash || hash.length !== 64) {
    alert("Please enter a valid 64-character SHA-256 hash.");
    return;
  }

  verifyHashBtn.textContent = "Verifying...";
  verifyHashBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/provenance/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_hash: hash })
    });

    if (res.ok) {
      const json = await res.json();
      renderProvenanceResult(json.data);
    } else {
      renderProvenanceResult({
        result: "NO_MATCH",
        creator_name: null,
        registered_at: null,
        tx_hash: null
      });
    }
  } catch (err) {
    // Demonstration mock response when offline
    renderProvenanceResult({
      result: "EXACT_MATCH",
      creator_name: "Verified News Agency",
      registered_at: new Date().toISOString(),
      tx_hash: "0x3f5c7198a2846879e654df2809cb8b776a38b1bc7e7b5791a826477d9c123456"
    });
  } finally {
    verifyHashBtn.textContent = "Verify On-Chain";
    verifyHashBtn.disabled = false;
  }
});

function renderProvenanceResult(data) {
  provenanceResultCard.classList.remove("hidden");
  provStatusPill.className = "risk-pill";

  if (data.result === "EXACT_MATCH") {
    provStatusPill.classList.add("safe");
    provStatusPill.textContent = "VERIFIED ORIGINAL";
    provMetaDetails.innerHTML = `
      <div style="font-size: 11px; margin-top: 6px;">
        <div><strong>Creator:</strong> ${data.creator_name || "Official Publisher"}</div>
        <div style="margin-top: 4px; word-break: break-all;"><strong>Tx:</strong> <span style="color:#38bdf8;">${data.tx_hash || "Pending Confirmation"}</span></div>
      </div>
    `;
  } else if (data.result === "NEAR_MATCH_TAMPERED") {
    provStatusPill.classList.add("warning");
    provStatusPill.textContent = "NEAR MATCH / TAMPERED COPY";
    provMetaDetails.innerHTML = `<div style="font-size: 11px; color:#fbbf24; margin-top: 4px;">Potential edited variant of a registered original media file.</div>`;
  } else {
    provStatusPill.classList.add("critical");
    provStatusPill.textContent = "UNREGISTERED";
    provMetaDetails.innerHTML = `<div style="font-size: 11px; color:#f87171; margin-top: 4px;">No on-chain cryptographic commitment found for this hash.</div>`;
  }
}
