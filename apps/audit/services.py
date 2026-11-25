import logging
from typing import Optional
from apps.audit.models import AuditLog

logger = logging.getLogger('healthcare.audit')


class AuditService:
    """Service handling audit trail logging for security, compliance, and traceability."""

    @staticmethod
    def log_action(
        user,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: str = ""
    ) -> Optional[AuditLog]:
        """
        Creates an immutable audit log entry.
        Silently logs exceptions so business transactions aren't broken by non-critical logging failures.
        """
        try:
            user_obj = user if (user and hasattr(user, 'is_authenticated') and user.is_authenticated) else None
            return AuditLog.objects.create(
                user=user_obj,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                details=details
            )
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}", exc_info=True)
            return None
