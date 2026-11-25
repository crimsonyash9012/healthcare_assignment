from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def default_key_expiration():
    """Default key expiration is 24 hours from creation."""
    return timezone.now() + timedelta(hours=24)


class IdempotencyKey(models.Model):
    """
    Stores idempotency keys to ensure retry-safe POST operations.
    Prevents duplicate resource creation on client retries or network timeouts.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
        db_index=True,
    )
    key = models.CharField(max_length=255, db_index=True)
    endpoint = models.CharField(max_length=255, db_index=True)
    request_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the request payload to detect parameter divergence."
    )
    response_body = models.JSONField(
        null=True,
        blank=True,
        help_text="Stored response body to return on idempotent replays."
    )
    response_status = models.PositiveIntegerField(
        help_text="Original HTTP response status code."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_key_expiration, db_index=True)

    class Meta:
        db_table = "idempotency_keys"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "endpoint", "key"],
                name="unique_user_endpoint_idempotency_key"
            )
        ]
        indexes = [
            models.Index(fields=["user", "endpoint", "key"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user_id}:{self.endpoint}:{self.key}"
