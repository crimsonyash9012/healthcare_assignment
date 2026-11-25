from django.db import models
from django.conf import settings


class Patient(models.Model):
    """
    Patient domain entity with optimistic locking and creator tracking.
    Stores date_of_birth instead of age because age changes over time.
    """
    id = models.BigAutoField(primary_key=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patients"
    )

    name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)

    # Optimistic locking counter to prevent lost updates during concurrent requests
    version = models.PositiveIntegerField(
        default=1,
        help_text="Optimistic locking version counter"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patients"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_by"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} (ID: {self.id}, Version: {self.version})"
