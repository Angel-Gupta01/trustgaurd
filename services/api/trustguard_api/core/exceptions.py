# services/api/trustguard_api/core/exceptions.py
from typing import Optional

class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        field: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.field = field
        super().__init__(message)

class ValidationError(AppError):
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(code="VALIDATION_ERROR", message=message, http_status=422, field=field)

class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(code="NOT_FOUND", message=message, http_status=404)

class MediaAlreadyRegisteredError(AppError):
    def __init__(self, message: str = "Media hash already registered on-chain"):
        super().__init__(code="MEDIA_ALREADY_REGISTERED", message=message, http_status=409)

class ForbiddenRoleError(AppError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(code="FORBIDDEN_ROLE", message=message, http_status=403)

class UnauthenticatedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(code="UNAUTHENTICATED", message=message, http_status=401)

class RateLimitedError(AppError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(code="RATE_LIMITED", message=message, http_status=429)

class UpstreamTimeoutError(AppError):
    def __init__(self, message: str = "Upstream service timeout"):
        super().__init__(code="UPSTREAM_TIMEOUT", message=message, http_status=502)

class ChainTxFailedError(AppError):
    def __init__(self, message: str = "Blockchain transaction failed"):
        super().__init__(code="CHAIN_TX_FAILED", message=message, http_status=502)
