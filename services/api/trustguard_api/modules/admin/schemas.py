# services/api/trustguard_api/modules/admin/schemas.py
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from trustguard_api.modules.shared.schemas import VishingCategory

class KeywordClusterCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: VishingCategory
    phrase: str = Field(..., min_length=2, max_length=200)
    weight: Decimal = Field(..., ge=0, le=1)
    is_active: bool = True

class KeywordClusterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category: VishingCategory
    phrase: str
    weight: Decimal
    is_active: bool
    created_at: datetime
