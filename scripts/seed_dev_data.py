# scripts/seed_dev_data.py
"""
Deterministic mock generator for TrustGuard development and demonstrations.
Populates mock vishing scans, incidents, and provenance commitments.
"""
import uuid
import datetime

SAMPLE_VISHING_SNIPPETS = [
    {
        "text": "URGENT NOTICE: An unauthorized transaction of $940 was attempted on your account. Call our fraud prevention team within 24 hours to secure your funds.",
        "risk_score": 88.5,
        "is_critical": True,
        "category": "URGENCY_PRESSURE"
    },
    {
        "text": "This is Officer Miller from the Cyber Crime Cell. An arrest warrant has been issued in your name. Verify your identity and confirm your PIN immediately.",
        "risk_score": 96.0,
        "is_critical": True,
        "category": "AUTHORITY_IMPERSONATION"
    },
    {
        "text": "Hi Dad, I dropped my phone in water and this is my temporary number. Can you please wire transfer $250 for my train ticket?",
        "risk_score": 78.0,
        "is_critical": True,
        "category": "FINANCIAL_LURE"
    },
    {
        "text": "Your monthly dental appointment reminder for Tuesday at 10:30 AM. Reply 1 to confirm.",
        "risk_score": 5.0,
        "is_critical": False,
        "category": "BENIGN"
    }
]

SAMPLE_PROVENANCE_RECORDS = [
    {
        "media_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "creator": "Press Trust Network",
        "title": "Press Briefing Keynote 2026",
        "tx_hash": "0x4b78912bcde32456f91823746123498701abcdef1234567890abcdef12345678"
    }
]

def print_seed_summary():
    print("=" * 60)
    print("TRUSTGUARD SEED DATA GENERATOR")
    print("=" * 60)
    print(f"Generated {len(SAMPLE_VISHING_SNIPPETS)} sample vishing/incident scenarios.")
    print(f"Generated {len(SAMPLE_PROVENANCE_RECORDS)} on-chain provenance records.")
    print("Mock seed records ready for DB ingestion or local testing.")
    print("=" * 60)

if __name__ == "__main__":
    print_seed_summary()
