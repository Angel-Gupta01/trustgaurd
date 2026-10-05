# services/api/run_tests.py
"""
Stand-alone test execution script for TrustGuard core components.
Verifies:
1. PII Redaction
2. Vishing evaluation & recommendation logic
3. Security & password hashing
4. JWT token generation & decode
"""
import sys
import os

# Add trustguard_api directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from trustguard_api.modules.vishing.service import VishingScorer, perform_vishing_scan
from trustguard_api.modules.shared.schemas import VishingScanRequest, VishingSourceType, VishingCategory
from trustguard_api.core.security import hash_password, verify_password, create_access_token, decode_access_token

def run_all_checks():
    print("=" * 60)
    print("RUNNING TRUSTGUARD CORE VERIFICATION TESTS")
    print("=" * 60)

    # 1. PII Redaction
    sample_text = "Account: 987654321012, OTP: 543219, please call now!"
    redacted = VishingScorer.redact_pii(sample_text)
    assert "[REDACTED_NUMBERS]" in redacted
    assert "987654321012" not in redacted
    assert "543219" not in redacted
    print("✅ PII Redaction: PASSED (Digit runs >= 6 successfully masked)")

    # 2. Critical Vishing Scan
    scam_text = "URGENT WARNING: An arrest warrant has been issued! Confirm your pin within 24 hours to prevent immediate asset freeze!"
    req = VishingScanRequest(text=scam_text, source_type=VishingSourceType.PASTED_TEXT)
    import asyncio
    res = asyncio.run(perform_vishing_scan(req))
    assert res.risk_score >= 70
    assert res.is_critical is True
    assert "HANG UP" in res.recommendation
    assert VishingCategory.URGENCY_PRESSURE in res.matched_categories
    print(f"✅ Vishing Critical Detection: PASSED (Score: {res.risk_score}/100, Rec: '{res.recommendation}')")

    # 3. Benign Scan
    benign_text = "Hey John, please remember to bring your laptop to tomorrow's meeting."
    req_benign = VishingScanRequest(text=benign_text, source_type=VishingSourceType.PASTED_TEXT)
    res_benign = asyncio.run(perform_vishing_scan(req_benign))
    assert res_benign.risk_score < 40
    assert res_benign.is_critical is False
    assert "LOOKS SAFE" in res_benign.recommendation
    print(f"✅ Vishing Benign Detection: PASSED (Score: {res_benign.risk_score}/100, Rec: '{res_benign.recommendation}')")

    # 4. Password Hashing
    pwd = "HackathonSafePassword2026!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("Invalid", hashed) is False
    print("✅ PBKDF2 Password Hashing & Verification: PASSED")

    # 5. JWT Lifecycle
    token = create_access_token({"sub": "admin-uuid", "role": "ADMIN"})
    payload = decode_access_token(token)
    assert payload["sub"] == "admin-uuid"
    assert payload["role"] == "ADMIN"
    print("✅ JWT Issuance & Cryptographic Validation: PASSED")

    print("=" * 60)
    print("ALL CORE UNIT CHECKS COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    run_all_checks()
