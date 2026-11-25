import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    MethodNotAllowed,
    Throttled,
)

from common.exceptions import ApplicationError
from common.middleware import get_current_request_id

logger = logging.getLogger('healthcare.exceptions')


def custom_exception_handler(exc, context):
    """
    Centralized DRF exception handler providing unified JSON response structure:
    {
        "success": false,
        "error": {
            "code": "<ERROR_CODE>",
            "message": "<Human readable description>",
            "details": <Field errors or null>,
            "request_id": "<UUID>"
        }
    }
    """
    request = context.get('request')
    request_id = getattr(request, 'request_id', None) or get_current_request_id()

    # Handle domain/application errors
    if isinstance(exc, ApplicationError):
        return Response(
            {
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            },
            status=exc.status_code
        )

    # Let DRF handle standard HTTP/DRF exceptions first
    response = exception_handler(exc, context)

    if response is not None:
        code = "API_ERROR"
        message = "A validation or request error occurred."
        details = response.data

        if isinstance(exc, DRFValidationError):
            code = "VALIDATION_ERROR"
            message = "Validation failed for one or more fields."
        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            code = "AUTHENTICATION_FAILED"
            message = "Authentication credentials were not provided or are invalid."
        elif isinstance(exc, PermissionDenied):
            code = "PERMISSION_DENIED"
            message = "You do not have permission to access this resource."
        elif isinstance(exc, NotFound):
            code = "NOT_FOUND"
            message = "The requested resource does not exist."
        elif isinstance(exc, MethodNotAllowed):
            code = "METHOD_NOT_ALLOWED"
            message = f"Method '{request.method}' not allowed for this endpoint."
        elif isinstance(exc, Throttled):
            code = "RATE_LIMIT_EXCEEDED"
            message = f"Request limit exceeded. Available in {exc.wait} seconds."
        elif isinstance(exc, APIException):
            code = exc.default_code.upper() if hasattr(exc, 'default_code') else "API_ERROR"
            message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)

        # Simplify details if it's a simple string or dict
        if isinstance(details, (str, list)):
            if len(details) == 1 and isinstance(details[0], str):
                message = details[0]
                details = None

        return Response(
            {
                "success": False,
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                    "request_id": request_id,
                }
            },
            status=response.status_code
        )

    # Unhandled server errors (500)
    logger.exception(f"Unhandled server error: {exc}", extra={'request_id': request_id})
    return Response(
        {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "details": None,
                "request_id": request_id,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
