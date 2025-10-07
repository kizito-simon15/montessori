"""Staff & StaffAttendance models – June 2025
------------------------------------------------
• Two staff categories only (teaching / non‑teaching)
• Free‑text ``job_title`` replaces rigid occupation choices
• Optional ``special_allowance`` paid on top of basic salary; statutory deductions are based on ``gross_for_deductions`` (basic + allowance).
• HELSB rate stored in **percent** (15.00 ⇒ 15 %) but helper returns fraction.
• Robust Tanzanian phone validators + automatic “+255” normalisation.
• Auto‑incrementing ``staff_id`` as VST###.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Final

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.urls import reverse
from django.utils import timezone

__all__ = [
    "Staff",
    "StaffAttendance",
]

# ────────────────────────────────────────────────────────────────────────
# Validators / shared constants
# ────────────────────────────────────────────────────────────────────────
TZ_PHONE_REGEX: Final = RegexValidator(
    regex=r"^\+255[0-9]{9}$",
    message="Mobile number must be in the format +255XXXXXXXXX",
)
BANK_AC_REGEX: Final = RegexValidator(
    regex=r"^[0-9]{10,20}$",
    message="Bank account number must be 10‑20 digits",
)


class Staff(models.Model):
    """Master HR record for an employee."""

    # ───────── choice lists ─────────
    STATUS             = [("active", "Active"), ("inactive", "Inactive")]
    GENDER             = [("male", "Male"), ("female", "Female")]
    STAFF_CATEGORIES   = [
        ("teaching", "Teaching"),
        ("non_teaching", "Non‑Teaching"),
    ]
    DEPARTMENT_CHOICES = [
        ("teaching", "Teaching"),
        ("administration", "Administration"),
        ("maintenance", "Maintenance"),
        ("catering", "Catering"),
        ("security", "Security"),
    ]

    # ───────── identity ─────────
    staff_id            = models.CharField(max_length=10, unique=True, editable=False, blank=True)
    current_status      = models.CharField(max_length=10, choices=STATUS, default="active")
    firstname           = models.CharField(max_length=200)
    middle_name         = models.CharField(max_length=200, blank=True)
    surname             = models.CharField(max_length=200)
    gender              = models.CharField(max_length=10, choices=GENDER, default="male")
    date_of_birth       = models.DateField(default=timezone.now)
    date_of_admission   = models.DateField(default=timezone.now)

    # ───────── category / role ─────────
    staff_category = models.CharField(
        max_length=20,
        choices=STAFF_CATEGORIES,
        default="teaching",
    )
    job_title = models.CharField(
        max_length=120,
        blank=True,
        help_text="Free‑text vacancy / title (e.g. ‘Math Teacher’ or ‘Bursar’)",
    )
    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        default="teaching",
    )

    # ───────── remuneration ─────────
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    special_allowance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        blank=True,
        help_text="Optional additional allowance (e.g. Head‑master duty) paid on top of basic salary.",
    )

    has_helsb = models.BooleanField(
        default=False,
        help_text="Tick if this employee has an active HELSB loan deduction.",
    )
    helsb_rate = models.DecimalField(
        max_digits=5,  # 999.99 %
        decimal_places=2,
        default=Decimal("15.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="HELSB deduction **percent**. Example 15.00 ⇒ 15 %",
    )

    # ───────── contact / admin ─────────
    mobile_number            = models.CharField(max_length=13, blank=True, validators=[TZ_PHONE_REGEX])
    email                    = models.EmailField(max_length=254, unique=True, blank=True, null=True)
    address                  = models.TextField(blank=True)
    emergency_contact_name   = models.CharField(max_length=200, blank=True)
    emergency_contact_number = models.CharField(max_length=13, blank=True, validators=[TZ_PHONE_REGEX])
    guarantor                = models.CharField(max_length=200, blank=True)

    # IDs & docs
    registration_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    nida_id             = models.CharField(max_length=20, blank=True, null=True)
    tin_number          = models.CharField(max_length=20, blank=True, null=True)

    # Contract
    contract_duration    = models.CharField(max_length=50, blank=True)
    contract_start_date  = models.DateField(default=timezone.now)
    contract_end_date    = models.DateField(blank=True, null=True)

    # Banking
    bank_name           = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True, validators=[BANK_AC_REGEX])
    bank_branch         = models.CharField(max_length=100, blank=True, null=True)

    # Misc
    passport_photo = models.ImageField(upload_to="staffs/passports/", blank=True)
    others         = models.TextField(blank=True)

    # ───────── meta ─────────
    class Meta:
        ordering = ["surname", "firstname"]
        permissions = [
            ("view_staff_list", "Can view staff list"),
            ("view_staff_detail", "Can view staff details"),
        ]

    # ───────── helper props ─────────
    def __str__(self) -> str:  # noqa: D401 – simple description
        return f"{self.firstname} {self.middle_name} {self.surname} ({self.staff_id})"

    def get_absolute_url(self):
        return reverse("staff-detail", kwargs={"pk": self.pk})

    @property
    def helsb_rate_as_decimal(self) -> Decimal:
        """Return HELSB rate in fraction form (0.15 for 15 %)."""
        return (self.helsb_rate or Decimal("0")) / Decimal("100")

    @property
    def gross_for_deductions(self) -> Decimal:
        """Basic salary **plus** any special allowance – use for NSSF/WCF/HELSB calculations."""
        return (self.salary or Decimal("0")) + (self.special_allowance or Decimal("0"))

    # ───────── clean & save overrides ─────────
    def clean(self):
        # Normalise Tanzanian numbers to +255XXXXXXXXX
        if self.mobile_number:
            self.mobile_number = self._tz_format(self.mobile_number)
        if self.emergency_contact_number:
            self.emergency_contact_number = self._tz_format(self.emergency_contact_number)
        super().clean()

    @staticmethod
    def _tz_format(num: str) -> str:
        """Ensure number starts with +255 and contains 9 digits afterwards."""
        if num.startswith("+255"):
            return num
        digits = "".join(filter(str.isdigit, num))[-9:]
        return "+255" + digits

    def save(self, *args, **kwargs):
        # auto‑generate staff_id once
        if not self.staff_id:
            last = Staff.objects.order_by("-id").first()
            next_num = int(last.staff_id[3:]) + 1 if last and last.staff_id else 1
            self.staff_id = f"VST{next_num:03d}"
        self.full_clean()
        super().save(*args, **kwargs)


# ────────────────────────────────────────────────────────────────────────
# Attendance
# ────────────────────────────────────────────────────────────────────────
class StaffAttendance(models.Model):
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date            = models.DateField(default=timezone.now)
    is_present      = models.BooleanField(default=False)
    time_of_arrival = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date", "user"]

    def __str__(self) -> str:  # noqa: D401 – simple description
        arrival = self.time_of_arrival.strftime("%H:%M:%S") if self.time_of_arrival else "—"
        status  = "Present" if self.is_present else "Absent"
        return f"{self.user.username} – {status} on {self.date:%Y-%m-%d} at {arrival}"
