from django.db import models
from django.utils import timezone

# If you later want to join back to Student / Staff just uncomment:
# from apps.students.models import Student
# from apps.staffs.models   import Staff


class SentSMS(models.Model):
    """
    Archive of every outbound Beem message
    (deduplicated per number × text).
    """

    RECIPIENT_CHOICES = [
        ("guardian", "Guardian"),
        ("staff",    "Staff"),
        ("other",    "Other"),
    ]

    # ── primary data ────────────────────────────────────────────
    dest_addr   = models.CharField(
        "Destination (+255…)", max_length=13, db_index=True
    )
    first_name  = models.CharField(
        max_length=50, null=True, blank=True
    )
    last_name   = models.CharField(
        max_length=50, null=True, blank=True
    )
    message     = models.TextField()
    status      = models.CharField(max_length=16, default="Sent", db_index=True)
    sent_date   = models.DateTimeField(default=timezone.now, db_index=True)

    # ── meta / diagnostics ─────────────────────────────────────
    recipient_type = models.CharField(
        max_length=10, choices=RECIPIENT_CHOICES, default="guardian"
    )
    # student = models.ForeignKey(Student, null=True, blank=True,
    #                             on_delete=models.SET_NULL)
    # staff   = models.ForeignKey(Staff,   null=True, blank=True,
    #                             on_delete=models.SET_NULL)
    network      = models.CharField(max_length=50, blank=True, null=True)
    source_addr  = models.CharField(max_length=50, default="VICTORY-PPS")
    length       = models.PositiveIntegerField(default=0)
    sms_count    = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-sent_date"]
        indexes  = [
            models.Index(fields=["dest_addr"]),
            models.Index(fields=["sent_date"]),
        ]

    # ── auto-populate helpers ──────────────────────────────────
    def save(self, *args, **kwargs):
        if not self.length:
            self.length = len(self.message)
        if not self.sms_count:
            self.sms_count = ((len(self.message) - 1) // 160) + 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:          # noqa: D401
        name = f"{self.first_name or ''} {self.last_name or ''}".strip() or "N/A"
        return f"{name} – {self.dest_addr} ({self.status})"
