# services/api/trustguard_api/modules/vishing/service.py
import re
import uuid
from decimal import Decimal
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from trustguard_api.modules.shared.schemas import (
    VishingCategory,
    VishingScanRequest,
    VishingScanResponse,
    IncidentSourceType,
)
from trustguard_api.core.config import settings
from trustguard_api.db.models import VishingScan, Incident, User

# Built-in baseline rule dictionary for instant in-process scoring
DEFAULT_KEYWORD_CLUSTERS: dict[VishingCategory, list[tuple[str, float]]] = {
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

class VishingScorer:
    """
    Synchronous, in-process, CPU-only vishing detection ensemble.
    Sub-150ms execution profile matching §1.1 and §2.1.
    """

    @classmethod
    def redact_pii(cls, text: str) -> str:
        """
        Redacts digit runs >= 6 characters (cards, bank accounts, OTPs)
        before storing or logging, adhering strictly to .ai/CONVENTIONS.md.
        """
        return DIGIT_REDACTION_REGEX.sub("[REDACTED_NUMBERS]", text)

    @classmethod
    def evaluate(
        cls,
        text: str
    ) -> Tuple[Decimal, list[VishingCategory], list[str], Decimal, Decimal]:
        normalized_text = text.lower()
        matched_categories: set[VishingCategory] = set()
        flagged_phrases: list[str] = []
        total_cluster_score = 0.0

        for category, phrases in DEFAULT_KEYWORD_CLUSTERS.items():
            for phrase, weight in phrases:
                if phrase in normalized_text:
                    matched_categories.add(category)
                    flagged_phrases.append(phrase)
                    total_cluster_score += (weight * 40.0)

        # Multi-category convergence boost (hallmark of sophisticated vishing attacks)
        category_boost = max(0, len(matched_categories) - 1) * 8.0
        rule_score = min(total_cluster_score + category_boost, 100.0)

        # Statistical heuristic approximation (simulating linear TF-IDF signal)
        urgency_tokens = ["urgent", "now", "alert", "warning", "expire", "suspended", "compromised", "pending"]
        statistical_signal = 0.0
        for token in urgency_tokens:
            if re.search(r"\b" + token + r"\b", normalized_text):
                statistical_signal += 10.0
        if "!" in text:
            statistical_signal += min(text.count("!") * 3.0, 15.0)

        ml_score = min(statistical_signal * 1.5, 100.0)

        # Ensemble combined risk score:
        # Prioritizes whichever signal is strongest when rule match is clear
        if rule_score >= 80.0:
            combined = (rule_score * 0.8) + (ml_score * 0.2)
        else:
            combined = (rule_score * 0.6) + (ml_score * 0.4)

        final_risk_score = Decimal(str(round(min(max(combined, 0.0), 100.0), 2)))

        return (
            final_risk_score,
            sorted(list(matched_categories), key=lambda c: c.value),
            flagged_phrases,
            Decimal(str(round(rule_score, 2))),
            Decimal(str(round(ml_score, 2)))
        )

    @classmethod
    def get_recommendation(cls, risk_score: Decimal) -> str:
        score = float(risk_score)
        if score >= settings.VISHING_CRITICAL_THRESHOLD:
            return "HANG UP: High-confidence social-engineering attack pattern detected."
        elif score >= settings.VISHING_CAUTION_THRESHOLD:
            return "PROCEED WITH CAUTION: Potential pressure tactics or suspicious inquiry identified."
        else:
            return "LOOKS SAFE: No prominent vishing or phishing indicators detected."

async def perform_vishing_scan(
    payload: VishingScanRequest,
    db: Optional[AsyncSession] = None,
    user: Optional[User] = None,
) -> VishingScanResponse:
    # 1. Redact PII before persistence
    redacted_snippet = VishingScorer.redact_pii(payload.text)

    # 2. Synchronous evaluation (in-process, CPU-only)
    risk_score, matched_cats, flagged_phrases, rule_score, ml_score = VishingScorer.evaluate(payload.text)
    is_critical = (float(risk_score) >= settings.VISHING_CRITICAL_THRESHOLD)
    recommendation = VishingScorer.get_recommendation(risk_score)

    scan_id = uuid.uuid4()

    # 3. Persist to PostgreSQL (if db session active)
    if db is not None:
        scan_record = VishingScan(
            id=scan_id,
            user_id=user.id if user else None,
            source_type=payload.source_type,
            text_snippet=redacted_snippet[:4000],
            matched_categories=matched_cats,
            rule_score=rule_score,
            ml_score=ml_score,
            risk_score=risk_score,
            is_critical=is_critical,
            model_version="tfidf-cluster-v1.0",
        )
        db.add(scan_record)

        # If risk_score crosses critical threshold, write incident in SAME transaction
        if is_critical:
            incident = Incident(
                source_type=IncidentSourceType.VISHING,
                user_id=user.id if user else None,
                risk_score=risk_score,
                category=matched_cats[0].value if matched_cats else "URGENCY_PRESSURE",
                evidence={
                    "flaggedPhrases": flagged_phrases,
                    "matchedCategories": [c.value for c in matched_cats],
                    "recommendation": recommendation,
                    "ruleScore": float(rule_score),
                    "mlScore": float(ml_score),
                },
                related_vishing_scan_id=scan_id,
                related_deepfake_job_id=None,
            )
            db.add(incident)

        await db.flush()

    return VishingScanResponse(
        scan_id=scan_id,
        risk_score=risk_score,
        is_critical=is_critical,
        matched_categories=matched_cats,
        flagged_phrases=flagged_phrases,
        recommendation=recommendation,
    )
