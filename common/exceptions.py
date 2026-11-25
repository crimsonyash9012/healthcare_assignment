from typing import Any, Optional


class ApplicationError(Exception):
    """Base application exception for business and domain logic errors."""
    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Any] = None
    ):
        if message:
            self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ResourceNotFoundError(ApplicationError):
    code = "RESOURCE_NOT_FOUND"
    status_code = 404
    message = "The requested resource was not found."


class ConflictError(ApplicationError):
    code = "RESOURCE_CONFLICT"
    status_code = 409
    message = "A conflict occurred with the current state of the resource."


class OptimisticLockError(ConflictError):
    code = "OPTIMISTIC_LOCK_CONFLICT"
    status_code = 409
    message = "Resource was modified by another process. Please refresh and try again."


class IdempotencyConflictError(ConflictError):
    code = "IDEMPOTENCY_CONFLICT"
    status_code = 409
    message = "An idempotency key collision occurred with differing request parameters."


class AuthorizationError(ApplicationError):
    code = "FORBIDDEN"
    status_code = 403
    message = "You do not have permission to perform this action."


class ValidationError(ApplicationError):
    code = "VALIDATION_ERROR"
    status_code = 400
    message = "Invalid input data provided."
