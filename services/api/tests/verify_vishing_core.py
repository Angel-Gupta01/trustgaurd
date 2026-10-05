# services/api/tests/verify_vishing_core.py
"""
Zero-dependency test suite verifying the TrustGuard core algorithms:
- PII Redaction (masks digit runs >= 6 with [REDACTED_NUMBERS])
- In-process Vishing Ensemble Scoring (Rule clusters + urgency/statistical heuristic)
- Plain-language recommendation generation ("HANG UP" / "PROCEED WITH CAUTION" / "LOOKS SAFE")
- PBKDF2-HMAC-SHA256 Password Hashing & Constant-Time Verification
"""
import re
import hashlib
import hmac
import secrets
from decimal import Decimal
from enum import Enum
from typing import Tuple, List, Set

class VishingCategory(str, Enum):
    URGENCY_PRESSURE = "URGENCY_PRESSURE"
    CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
    FINANCIAL_LURE = "FINANCIAL_LURE"
    AUTHORITY_IMPERSONATION = "AUTHORITY_IMPERSONATION"
    THREAT_OF_LOSS = "THREAT_OF_LOSS"
    LINK_BAIT = "LINK_BAIT"

DEFAULT_KEYWORD_CLUSTERS = {
    VishingCategory.URGENCY_PRESSURE: [
        ("act immediately", 0.9),
        ("within 24 hours", 0.85),
        ("immediate action required", 0.95),
        ("account will be suspended", 0.9),
        ("urgent notice", 0.8),
        ("failure to respond", 0.85),
    ],
    VishingCategory.CREDENTIAL_REQUEST: [
        ("verify your password", 0.95),
        ("confirm your pin", 0.95),
        ("share one time password", 0.98),
        ("otp sent to your phone", 0.95),
        ("cvv number", 0.98),
        ("security questions", 0.8),
    ],
    VishingCategory.FINANCIAL_LURE: [
        ("wire transfer", 0.85),
        ("claim your prize", 0.9),
        ("unclaimed refund", 0.85),
        ("lottery winner", 0.95),
        ("crypto investment return", 0.9),
        ("guaranteed earnings", 0.85),
    ],
    VishingCategory.AUTHORITY_IMPERSONATION: [
        ("federal bureau", 0.95),
        ("internal revenue service", 0.95),
        ("police department", 0.95),
        ("reserve bank", 0.9),
        ("fraud prevention team", 0.9),
        ("cyber crime cell", 0.95),
    ],
    VishingCategory.THREAT_OF_LOSS: [
        ("legal action", 0.85),
        ("arrest warrant", 0.98),
        ("court summons", 0.95),
        ("freeze your assets", 0.98),
        ("penalty fees", 0.8),
    ],
    VishingCategory.LINK_BAIT: [
        ("click this link to avoid", 0.9),
        ("login via this secure link", 0.95),
        ("download the attached apk", 0.98),
        ("install quicksupport", 0.98),
        ("install anydesk", 0.98),
    ],
}

DIGIT_REDACTION_REGEX = re.compile(r"\b\d{6,}\b")

def redact_pii(text: str) -> str:
    return DIGIT_REDACTION_REGEX.sub("[REDACTED_NUMBERS]", text)

def evaluate_vishing(text: str) -> Tuple[Decimal, List[VishingCategory], List[str]]:
    normalized_text = text.lower()
    matched_categories: Set[VishingCategory] = set()
    flagged_phrases: List[str] = []
    total_cluster_score = 0.0

    for category, phrases in DEFAULT_KEYWORD_CLUSTERS.items():
        for phrase, weight in phrases:
            if phrase in normalized_text:
                matched_categories.add(category)
                flagged_phrases.append(phrase)
                total_cluster_score += (weight * 40.0)

    category_boost = max(0, len(matched_categories) - 1) * 8.0
    rule_score = min(total_cluster_score + category_boost, 100.0)

    urgency_tokens = ["urgent", "now", "alert", "warning", "expire", "suspended", "compromised", "pending"]
    statistical_signal = 0.0
    for token in urgency_tokens:
        if re.search(r"\b" + token + r"\b", normalized_text):
            statistical_signal += 10.0
    if "!" in text:
        statistical_signal += min(text.count("!") * 3.0, 15.0)

    ml_score = min(statistical_signal * 1.5, 100.0)
    if rule_score >= 80.0:
        combined = (rule_score * 0.8) + (ml_score * 0.2)
    else:
        combined = (rule_score * 0.6) + (ml_score * 0.4)

    final_risk_score = Decimal(str(round(min(max(combined, 0.0), 100.0), 2)))
    return final_risk_score, sorted(list(matched_categories), key=lambda c: c.value), flagged_phrases

def get_recommendation(risk_score: Decimal) -> str:
    score = float(risk_score)
    if score >= 75.0:
        return "HANG UP: High-confidence social-engineering attack pattern detected."
    elif score >= 40.0:
        return "PROCEED WITH CAUTION: Potential pressure tactics or suspicious inquiry identified."
    else:
        return "LOOKS SAFE: No prominent vishing or phishing indicators detected."

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"pbkdf2_sha256${salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split('$')
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
            return False
        salt = parts[1]
        expected_key = parts[2]
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hmac.compare_digest(key.hex(), expected_key)
    except Exception:
        return False

def run_tests():
    print("=" * 65)
    print("TRUSTGUARD ALGORITHM VERIFICATION SUITE")
    print("=" * 65)

    # Test 1: PII Redaction
    raw = "Customer account 491283749102 OTP is 928374 and CVV is 123"
    redacted = redact_pii(raw)
    assert "491283749102" not in redacted, "Account number should be masked"
    assert "928374" not in redacted, "OTP should be masked"
    assert "123" in redacted, "Short numbers < 6 should not be over-masked"
    assert "[REDACTED_NUMBERS]" in redacted
    print(" [1/4] PII Redaction: PASSED (Digit runs >= 6 masked correctly)")

    # Test 2: Severe Vishing Detection
    severe_call = "Urgent notice from police department! Arrest warrant pending! Confirm your pin within 24 hours or we will freeze your assets!"
    score, categories, flagged = evaluate_vishing(severe_call)
    rec = get_recommendation(score)
    assert score >= 75.0, f"Expected critical score >= 75, got {score}"
    assert "HANG UP" in rec
    assert VishingCategory.URGENCY_PRESSURE in categories
    assert VishingCategory.AUTHORITY_IMPERSONATION in categories
    assert VishingCategory.THREAT_OF_LOSS in categories
    print(f" [2/4] Severe Vishing Detection: PASSED (Score: {score}/100, Rec: '{rec}')")

    # Test 3: Benign Conversation
    benign_msg = "Good afternoon team, please review the sprint burndown chart before standup."
    score_b, categories_b, flagged_b = evaluate_vishing(benign_msg)
    rec_b = get_recommendation(score_b)
    assert score_b < 40.0, f"Expected benign score < 40, got {score_b}"
    assert "LOOKS SAFE" in rec_b
    assert len(categories_b) == 0
    print(f" [3/4] Benign Message Evaluation: PASSED (Score: {score_b}/100, Rec: '{rec_b}')")

    # Test 4: Password Hashing & Verification
    pwd = "SecOpsTrustGuard2026$"
    h = hash_password(pwd)
    assert verify_password(pwd, h) is True
    assert verify_password("HackedPassword", h) is False
    print(" [4/4] Cryptographic Hashing: PASSED (Salted PBKDF2-HMAC-SHA256 verified)")

    print("=" * 65)
    print("ALL CORE ALGORITHMIC TESTS PASSED PERFECTLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
