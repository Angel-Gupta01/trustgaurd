# services/api/trustguard_api/core/envelope.py
import uuid
from typing import Any, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from trustguard_api.modules.shared.schemas import ApiResponse, ApiError

def build_envelope_response(
    data: Optional[Any] = None,
    error: Optional[ApiError] = None,
    request_id: Optional[str] = None,
    status_code: int = 200
) -> JSONResponse:
    payload = ApiResponse(
        success=(error is None),
        data=data,
        error=error,
        request_id=request_id or str(uuid.uuid4())
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))

def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))
