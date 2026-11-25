from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Immutable audit log recording sensitive medical resource access and mutations.
    Enforces HIPAA/compliance traceability.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs"
    )
    action = models.CharField(max_length=50, db_index=True)
    resource_type = models.CharField(max_length=50, db_index=True)
    resource_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["user", "action"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        user_email = self.user.email if self.user else "Anonymous/System"
        return f"[{self.timestamp}] {user_email} performed {self.action} on {self.resource_type}:{self.resource_id}"
