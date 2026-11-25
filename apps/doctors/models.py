from django.db import models
from django.conf import settings


class Doctor(models.Model):
    """
    Doctor domain entity with optimistic locking and creator tracking.
    """
    id = models.BigAutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="doctors"
    )

    name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=150)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    qualifications = models.CharField(max_length=255, blank=True)
    experience_years = models.PositiveIntegerField(default=0)

    # Optimistic locking counter to prevent lost updates during concurrent edits
    version = models.PositiveIntegerField(
        default=1,
        help_text="Optimistic locking version counter"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "doctors"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["specialization"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return f"Dr. {self.name} - {self.specialization} (ID: {self.id})"
