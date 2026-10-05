# services/api/tests/test_vishing_service.py
import pytest
from decimal import Decimal
from trustguard_api.modules.vishing.service import VishingScorer, perform_vishing_scan
from trustguard_api.modules.shared.schemas import VishingScanRequest, VishingSourceType, VishingCategory

def test_pii_redaction():
    text = "Please verify your account 123456789012 and enter OTP 482910 immediately."
    redacted = VishingScorer.redact_pii(text)
    assert "123456789012" not in redacted
    assert "482910" not in redacted
    assert "[REDACTED_NUMBERS]" in redacted

def test_critical_vishing_scan():
    scam_text = "URGENT NOTICE: An arrest warrant has been issued! Verify your password and confirm your pin within 24 hours to avoid asset freeze!"
    req = VishingScanRequest(text=scam_text, source_type=VishingSourceType.PASTED_TEXT)
    res = perform_vishing_scan(req)

    assert res.risk_score >= Decimal("70.0")
    assert res.is_critical is True
    assert "HANG UP" in res.recommendation
    assert VishingCategory.URGENCY_PRESSURE in res.matched_categories
    assert VishingCategory.CREDENTIAL_REQUEST in res.matched_categories

def test_benign_text_scan():
    benign_text = "Hey Sarah, are we still meeting for lunch at 1 PM today? Let me know!"
    req = VishingScanRequest(text=benign_text, source_type=VishingSourceType.PASTED_TEXT)
    res = perform_vishing_scan(req)

    assert res.risk_score < Decimal("40.0")
    assert res.is_critical is False
    assert "LOOKS SAFE" in res.recommendation
