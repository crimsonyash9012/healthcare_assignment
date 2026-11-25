import json
import hashlib
import functools
from typing import Callable, Tuple, Any
from django.db import transaction, IntegrityError, OperationalError
import time
from django.utils import timezone
from rest_framework.response import Response

from common.exceptions import IdempotencyConflictError, ValidationError
from common.idempotency.models import IdempotencyKey


def calculate_request_hash(payload: Any) -> str:
    """Computes a deterministic SHA-256 hash of the request payload."""
    if payload is None:
        serialized = ""
    elif isinstance(payload, bytes):
        serialized = payload.decode('utf-8', errors='ignore')
    elif isinstance(payload, str):
        serialized = payload
    else:
        # Sort keys to ensure deterministic serialization regardless of key ordering
        serialized = json.dumps(payload, sort_keys=True, default=str)

    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def sanitize_response_data(data: Any) -> Any:
    """
    Sanitizes response data before storing in idempotency table.
    Redacts password or credential fields if present.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if k.lower() in ('password', 'token', 'access', 'refresh', 'secret'):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_response_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_response_data(item) for item in data]
    return data


class IdempotencyService:
    """
    Coordinates idempotent execution for sensitive mutating POST endpoints.
    Handles key collisions, payload verification, response replay, and concurrency races.
    """
    @classmethod
    def execute_with_idempotency(
        cls,
        user,
        endpoint: str,
        idempotency_key: str,
        request_data: Any,
        operation_callable: Callable[[], Tuple[Any, int]]
    ) -> Tuple[Any, int, bool]:
        """
        Executes operation_callable atomically, or replays the previous response if
        a matching valid key exists for the user and endpoint.

        Returns:
            Tuple[response_data, response_status, is_replayed]
        """
        if not idempotency_key or not idempotency_key.strip():
            raise ValidationError(
                message="Idempotency-Key header is required for this POST operation.",
                code="MISSING_IDEMPOTENCY_KEY"
            )

        clean_key = idempotency_key.strip()
        request_hash = calculate_request_hash(request_data)

        # Quick check outside transaction
        existing = (
            IdempotencyKey.objects
            .filter(user=user, endpoint=endpoint, key=clean_key)
            .first()
        )
        if existing and not existing.is_expired():
            if existing.request_hash != request_hash:
                raise IdempotencyConflictError(
                    "Idempotency key has already been used with different request parameters."
                )
            return existing.response_body, existing.response_status, True

        # Atomic transaction to guarantee safe concurrent execution
        try:
            with transaction.atomic():
                existing = (
                    IdempotencyKey.objects.select_for_update()
                    .filter(user=user, endpoint=endpoint, key=clean_key)
                    .first()
                )

                if existing:
                    if existing.is_expired():
                        existing.delete()
                    else:
                        if existing.request_hash != request_hash:
                            raise IdempotencyConflictError(
                                "Idempotency key has already been used with different request parameters."
                            )
                        return existing.response_body, existing.response_status, True

                # Execute the mutating business operation
                response_data, response_status = operation_callable()

                # Atomically record the key alongside resource creation
                IdempotencyKey.objects.create(
                    user=user,
                    endpoint=endpoint,
                    key=clean_key,
                    request_hash=request_hash,
                    response_body=sanitize_response_data(response_data),
                    response_status=response_status,
                )

                return response_data, response_status, False

        except (IntegrityError, OperationalError):
            # Concurrency race: Another thread committed or is committing the key.
            # Poll with brief backoff for the winner's committed response
            for delay in (0.05, 0.1, 0.2, 0.3):
                time.sleep(delay)
                try:
                    winner_key = (
                        IdempotencyKey.objects
                        .filter(user=user, endpoint=endpoint, key=clean_key)
                        .first()
                    )
                    if winner_key and not winner_key.is_expired():
                        if winner_key.request_hash != request_hash:
                            raise IdempotencyConflictError(
                                "Idempotency key has already been used with different request parameters."
                            )
                        return winner_key.response_body, winner_key.response_status, True
                except OperationalError:
                    continue
            raise


def idempotent_action(endpoint: str):
    """
    Decorator for DRF view actions (e.g. create) enforcing idempotency:
    - Reads 'Idempotency-Key' from request headers
    - Verifies user authentication
    - Invokes IdempotencyService
    - Sets 'X-Cache: HIT' header on replayed responses
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            idempotency_key = request.headers.get('Idempotency-Key')
            if not idempotency_key:
                raise ValidationError(
                    message="Idempotency-Key header is required for this operation.",
                    code="MISSING_IDEMPOTENCY_KEY"
                )

            def execute():
                resp = view_func(self, request, *args, **kwargs)
                return resp.data, resp.status_code

            data, status_code, is_replayed = IdempotencyService.execute_with_idempotency(
                user=request.user,
                endpoint=endpoint,
                idempotency_key=idempotency_key,
                request_data=request.data,
                operation_callable=execute
            )

            headers = {}
            if is_replayed:
                headers['X-Cache'] = 'HIT'
                headers['Idempotent-Replay'] = 'true'

            return Response(data, status=status_code, headers=headers)
        return wrapper
    return decorator
