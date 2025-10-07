# apps/finance/models.py
# Modernised on 05 Jul 2025  •  reflects new PAYE, WCF-0 %, fee-categories & budget-types
from __future__ import annotations

import logging
from datetime import date
from decimal   import Decimal, ROUND_HALF_UP

from django.conf       import settings

from django.db         import models, transaction
from datetime import date

from django.db.models.functions import TruncMonth


from django.db.models.signals import post_save, post_delete
from django.dispatch   import receiver
from django.core.exceptions import ValidationError
from django.db              import models
from django.db.models        import (
    CheckConstraint, UniqueConstraint, Q, Sum, F, ExpressionWrapper, DecimalField
)
from django.utils            import timezone

# ───────────────────────────  cross-app look-ups  ───────────────────────────
from apps.corecode.models import AcademicSession, AcademicTerm, Installment, StudentClass
from apps.staffs.models   import Staff
from apps.students.models import Student

logger = logging.getLogger(__name__)



# ─── statutory constants ----------------------------------------------------
DEC2       = Decimal("0.01")
NSSF_RATE  = Decimal("0.10")     # 10 %
WCF_RATE   = Decimal("0.00")     # 0 %
_r2 = lambda v: Decimal(v or 0).quantize(DEC2, ROUND_HALF_UP)




class BudgetCategory(models.TextChoices):
    ANNUAL     = "ANNUAL",     "Annual"
    MONTHLY    = "MONTHLY",    "Monthly"
    TERM       = "TERM",       "Per Term"
    SEASONAL   = "SEASONAL",   "Seasonal"




import logging
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    CheckConstraint,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)


class Budget(models.Model):
    """
    Allocation envelope – tracks money IN (receipts) vs money OUT (salary +
    four expense streams).  No term/install granularity.
    """

    name             = models.CharField(max_length=80)
    category         = models.CharField(
        max_length=10,
        choices=BudgetCategory.choices,
        default=BudgetCategory.ANNUAL,
    )
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    session          = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                check=Q(allocated_amount__gt=0),
                name="budget_allocated_positive",
            )
        ]

    # ───────────── money IN – fee receipts (info only) ───────────
    @property
    def cash_received(self) -> Decimal:
        from apps.finance.models import Receipt  # late import
        return (
            Receipt.objects.filter(invoice__session=self.session)
            .aggregate(t=Sum("amount_paid"))["t"]
            or Decimal("0")
        )

    # ───────────── money OUT – 5 streams ─────────────────────────
    @property
    def used(self) -> Decimal:
        from expenditures.models import (
            Expenditure,
            KitchenPurchase,
            ProcessingBatch,
            SeasonalPurchase,
        )
        from apps.finance.models import SalaryInvoice

        salary_total = (
            SalaryInvoice.objects.filter(budget=self)
            .aggregate(t=Sum("net_salary"))["t"]
            or Decimal("0")
        )
        exp_total = (
            Expenditure.objects.filter(budget=self)
            .aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        )

        cost_expr = ExpressionWrapper(
            F("quantity") * F("price_per_unit"),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        )
        seasonal_total = (
            SeasonalPurchase.objects.filter(budget=self)
            .aggregate(t=Sum(cost_expr))["t"]
            or Decimal("0")
        )
        kitchen_total = (
            KitchenPurchase.objects.filter(budget=self)
            .aggregate(t=Sum(cost_expr))["t"]
            or Decimal("0")
        )
        proc_fee_total = (
            ProcessingBatch.objects.filter(source_purchase__budget=self)
            .aggregate(t=Sum("processing_fee"))["t"]
            or Decimal("0")
        )
        return _r2(
            salary_total + exp_total + seasonal_total + kitchen_total + proc_fee_total
        )

    @property
    def remaining(self) -> Decimal:
        return _r2(self.allocated_amount - self.used)

    def __str__(self):
        return f"{self.name} – {self.get_category_display()} • {self.session}"



# ═══════════════════════════════════════
#  SALARY-INVOICE
# ═══════════════════════════════════════
class SalaryInvoice(models.Model):
    """
    One payslip per employee per calendar-month.
    Snapshot columns (gross/net) are recalculated EVERY time a linked
    Deduction row is added / changed / deleted.
    """

    # bookkeeping
    budget = models.ForeignKey(
        Budget, on_delete=models.PROTECT, related_name="salary_invoices",
        help_text="Which budget envelope funds this payslip?"
    )
    staff  = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="salary_invoices"
    )

    month        = models.DateField(default=date.today)   # coerced → YYYY-MM-01
    issued_date  = models.DateField(default=date.today)

    # inputs
    basic_salary      = models.DecimalField(max_digits=12, decimal_places=2)
    special_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowance         = models.DecimalField(max_digits=12, decimal_places=2, default=0)   # untaxed
    paye_amount       = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # snapshots (readonly in form / template)
    gross_salary       = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    nssf_amount        = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    wcf_amount         = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    helsb_amount       = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    net_salary         = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    total_given_salary = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    remarks = models.TextField(blank=True)

    # ─── ORM meta ──────────────────────────────────────────────────────
    class Meta:
        ordering = ["-month", "-issued_date"]
        constraints = [
            CheckConstraint(check=Q(basic_salary__gt=0), name="slip_basic_positive"),
            CheckConstraint(check=Q(paye_amount__gte=0), name="slip_paye_nonneg"),
            models.UniqueConstraint(fields=["staff", "month"],
                                    name="uniq_staff_calendar_month"),
        ]

    # ─── computed properties ─────────────────────────────────────────
    @property
    def taxable_gross(self) -> Decimal:
        return _r2(self.basic_salary + self.special_allowance)

    @property
    def extra_deductions(self) -> Decimal:
        if not self.pk:
            return Decimal(0)
        return self.deductions.aggregate(t=Sum("amount"))["t"] or Decimal(0)

    # ─── internal helpers ────────────────────────────────────────────
    def _nssf (self) -> Decimal: return _r2(self.taxable_gross * NSSF_RATE)
    def _wcf  (self) -> Decimal: return _r2(self.taxable_gross * WCF_RATE)

    def _helsb(self) -> Decimal:
        if not self.staff.has_helsb:
            return Decimal(0)
        return _r2(self.taxable_gross * self.staff.helsb_rate_as_decimal)

    def _compute_snapshots(self) -> None:
        """Populate snapshot fields in-memory only (caller must .save())."""
        self.nssf_amount  = self._nssf()
        self.wcf_amount   = self._wcf()
        self.helsb_amount = self._helsb()

        self.gross_salary = _r2(self.taxable_gross + self.allowance)
        self.net_salary   = _r2(
            self.taxable_gross
            - (self.nssf_amount + self.wcf_amount +
               self.paye_amount  + self.helsb_amount)
            - self.extra_deductions
            + self.allowance
        )
        self.total_given_salary = self.net_salary

    # ─── clean & save overrides ──────────────────────────────────────
    def clean(self):
        super().clean()
        if self.month:
            self.month = self.month.replace(day=1)
        if self.paye_amount < 0:
            raise ValidationError({"paye_amount": "PAYE cannot be negative."})
        # duplicate guard
        if (self.staff and self.month and
            SalaryInvoice.objects
                       .filter(staff=self.staff, month=self.month)
                       .exclude(pk=self.pk)
                       .exists()):
            raise ValidationError(
                f"{self.staff} already has a salary slip for {self.month:%B %Y}."
            )

    def save(self, *args, **kwargs):
        # (1) pre-sets on first save
        if not self.pk:
            self.basic_salary      = self.basic_salary      or (self.staff.salary            or 0)
            self.special_allowance = self.special_allowance or (self.staff.special_allowance or 0)
        # (2) always recalc snapshots
        self._compute_snapshots()
        super().save(*args, **kwargs)

    # public: called by Deduction signals
    def recalc_from_deductions(self) -> None:
        self._compute_snapshots()
        super().save(update_fields=[
            "nssf_amount", "wcf_amount", "helsb_amount",
            "gross_salary", "net_salary", "total_given_salary"
        ])

    # readable repr
    def __str__(self) -> str:
        return f"{self.staff} – {self.month:%b %Y}"


# ═══════════════════════════════════════
#  EXTRA-DEDUCTION
# ═══════════════════════════════════════
class Deduction(models.Model):
    salary_invoice = models.ForeignKey(
        SalaryInvoice, on_delete=models.CASCADE, related_name="deductions"
    )
    reason = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["salary_invoice_id", "id"]
        constraints = [
            CheckConstraint(check=Q(amount__gte=0), name="deduction_nonneg"),
        ]

    def clean(self):
        if self.amount < 0:
            raise ValidationError({"amount": "Amount must be zero or positive."})

    def __str__(self) -> str:
        return f"{self.reason} – {self.amount:,.0f} TZS"

# ─── automatic snapshot sync: post-save & post-delete ───────────────────────
@receiver([post_save, post_delete], sender=Deduction, dispatch_uid="recalc_slip_totals")
def _refresh_parent_slip(sender, instance: Deduction, **_):
    """
    Keep the parent `SalaryInvoice` in sync any time a Deduction row
    is added, updated or removed – even via the admin or a script.
    """
    try:
        with transaction.atomic():
            instance.salary_invoice.recalc_from_deductions()
    except Exception:
        logger.exception("Failed to recalc salary slip %s", instance.salary_invoice_id)


# ════════════════════════════════════════════════════════════════════════════
#  3.  SCHOOL FEES  (per *session* **and** *category*)
# ════════════════════════════════════════════════════════════════════════════

class SchoolFees(models.Model):
    """
    Multiple fee-tiers per academic session:
    Allows user-defined categories.
    """
    session = models.ForeignKey(
        AcademicSession, on_delete=models.CASCADE, related_name="school_fees"
    )
    category = models.CharField(max_length=50)
    annual_amount = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["session__name", "category"]
        unique_together = [("session", "category")]
        constraints = [
            CheckConstraint(check=Q(annual_amount__gt=0), name="fees_positive")
        ]

    # helper – divide equally across existing Installments
    def installment_amount(self) -> int:
        count = Installment.objects.count() or 1
        return self.annual_amount // count  # Integer division for whole numbers

    def __str__(self):
        return f"{self.session} – {self.category} : {self.annual_amount:,} TZS"

# ════════════════════════════════════════════════════════════════════════════
#  4.  INVOICE / ITEMS / RECEIPT  (unchanged except FK → new SchoolFees shape)
#      – business logic will need to look up the fee that matches the student
# ════════════════════════════════════════════════════════════════════════════


# Assuming _r2 is defined elsewhere as:
_r2 = lambda v: Decimal(v or 0).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")



class Invoice(models.Model):
    """
    One invoice per student × session × installment.

    09 Jul 2025  • cross-session carry-forward enabled
    """

    STATUS = (("draft", "Draft"), ("active", "Active"), ("closed", "Closed"))

    # ---------- foreign keys ----------
    student      = models.ForeignKey(Student,        on_delete=models.CASCADE, related_name="invoices")
    session      = models.ForeignKey(AcademicSession,on_delete=models.CASCADE, related_name="invoices")
    installment  = models.ForeignKey(Installment,    on_delete=models.CASCADE, related_name="invoices")
    class_for    = models.ForeignKey(StudentClass,   on_delete=models.SET_NULL, null=True, editable=False)
    school_fees  = models.ForeignKey("SchoolFees",   on_delete=models.PROTECT,  related_name="invoices")

    # ---------- core data ----------
    invoice_number                = models.CharField(max_length=50, unique=True, blank=True)
    invoice_amount                = models.IntegerField(default=0)
    due_date                      = models.DateField(default=timezone.now)
    notes                         = models.TextField(blank=True)
    status                        = models.CharField(max_length=10, choices=STATUS, default="draft")
    balance_from_previous_install = models.IntegerField(default=0, editable=False)

    # ---------- bookkeeping ----------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering    = ["-created_at", "student__surname"]
        constraints = [
            CheckConstraint(check=Q(invoice_amount__gt=0), name="inv_amount_positive"),
            models.UniqueConstraint(
                fields=["student", "session", "installment"],
                name="unique_invoice_per_installment",
            ),
        ]

    # ───────────────────────────────────────────────────────────
    # helpers
    # ───────────────────────────────────────────────────────────
    def _outstanding_before(self) -> int:
        """Sum of unpaid balances in *earlier* periods (any session < this
        one, or same session with earlier installment)."""
        prior_qs = (
            Invoice.objects
            .filter(student=self.student)
            .filter(
                Q(session__id__lt=self.session_id) |
                Q(session_id=self.session_id, installment__id__lt=self.installment_id)
            )
        )
        exp  = prior_qs.aggregate(t=Sum("invoice_amount"))["t"]           or 0
        paid = prior_qs.aggregate(t=Sum("receipts__amount_paid"))["t"]    or 0
        return exp - paid

    def expected_amount (self) -> int: return self.invoice_amount
    def amount_paid     (self) -> int: return self.receipts.aggregate(t=Sum("amount_paid"))["t"] or 0
    def balance         (self) -> int: return self.expected_amount() - self.amount_paid()
    def overall_balance (self) -> int: return self.balance_from_previous_install + self.balance()

    # ───────────────────────────────────────────────────────────
    # validation
    # ───────────────────────────────────────────────────────────
    def clean(self):
        if self.invoice_amount <= 0:
            raise ValidationError("Invoice amount must be a positive whole number.")
        if self.school_fees.session_id != self.session_id:
            raise ValidationError("School-fees entry must belong to the selected session.")

        # prevent over-billing against the chosen tier
        used = (
            Invoice.objects
                   .filter(student_id=self.student_id, session_id=self.session_id)
                   .exclude(pk=self.pk)
                   .aggregate(t=Sum("invoice_amount"))["t"] or 0
        )
        if self.invoice_amount > self.school_fees.annual_amount - used:
            raise ValidationError("Invoice amount exceeds the tier’s remaining annual balance.")

    # ───────────────────────────────────────────────────────────
    # save()
    # ───────────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        brand_new = self.pk is None
        # carry-forward (now cross-session)
        self.balance_from_previous_install = self._outstanding_before()

        # default amount on first save
        if brand_new and self.invoice_amount == 0:
            self.invoice_amount = (
                self.school_fees.installment_amount() + self.balance_from_previous_install
            )

        # auto-number
        if not self.invoice_number:
            yr = timezone.now().year
            serial = Invoice.objects.filter(created_at__year=yr).count() + 1
            self.invoice_number = f"INV-{yr}-{self.student_id}-{serial:05d}"

        # take snapshot of current class
        if not self.class_for_id:
            self.class_for = self.student.current_class

        self.full_clean()
        super().save(*args, **kwargs)
        self._update_status()

    # ───────────────────────────────────────────────────────────
    def _update_status(self):
        new = "closed" if self.overall_balance() <= 0 else "active"
        if self.status != new:
            self.status = new
            super().save(update_fields=["status"])

    def __str__(self): return self.invoice_number or "<invoice>"



class InvoiceItem(models.Model):
    CATEGORY = (("TUITION", "Tuition"), ("TRANSPORT", "Transport"), ("UNIFORM", "Uniform"), ("OTHER", "Other"))

    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=200)
    category    = models.CharField(max_length=20, choices=CATEGORY, default="TUITION")
    quantity    = models.PositiveIntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    amount      = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        ordering = ["invoice", "description"]
        constraints = [
            CheckConstraint(check=Q(quantity__gt=0),  name="invitem_qty_positive"),
            CheckConstraint(check=Q(unit_price__gt=0), name="invitem_price_positive"),
        ]

    def save(self, *a, **kw):
        self.amount = _r2(self.quantity * self.unit_price)
        super().save(*a, **kw)

    def __str__(self): return f"{self.description} – {self.amount:,.0f}"


class Receipt(models.Model):
    PAYMENT_METHOD = [("NMB_BANK", "NMB Bank"), ("CRDB_BANK", "CRDB Bank"), ("MOBILE", "Mobile Payment"), ("CASH", "Cash")]

    invoice               = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="receipts")
    receipt_number        = models.CharField(max_length=50, unique=True, blank=True)
    amount_paid           = models.DecimalField(max_digits=11, decimal_places=2)
    date_paid             = models.DateField(default=timezone.now)
    payment_method        = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    transaction_reference = models.CharField(max_length=100, blank=True)
    comment               = models.CharField(max_length=200, blank=True)
    received_by           = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="received_receipts")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_paid"]
        get_latest_by = "date_paid"
        constraints = [
            CheckConstraint(check=Q(amount_paid__gt=0), name="receipt_amt_positive"),
            CheckConstraint(check=Q(amount_paid__lte=Decimal("999999999.99")), name="receipt_amt_ceiling"),
        ]

    def __str__(self): return self.receipt_number or "<receipt>"

    # basic validation
    def clean(self):
        if not self.invoice_id:
            return
        if self.amount_paid <= 0:
            raise ValidationError("Amount paid must be positive.")
        if self.amount_paid > self.invoice.overall_balance():
            raise ValidationError("Payment exceeds invoice balance.")

    # auto-number
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            year = (self.date_paid or timezone.now()).year
            serial = Receipt.objects.filter(date_paid__year=year).count() + 1
            self.receipt_number = f"REC-{year}-{serial:05d}"
        self.full_clean()
        super().save(*args, **kwargs)
        if self.invoice_id:
            self.invoice._update_status()


# ════════════════════════════════════════════════════════════════════════════
#  5.  UNIFORMS  (unchanged)
# ════════════════════════════════════════════════════════════════════════════
class UniformType(models.Model):
    name  = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["name"]
        constraints = [CheckConstraint(check=Q(price__gte=0), name="uniform_price_non_negative")]

    def __str__(self): return self.name


class Uniform(models.Model):
    student        = models.ForeignKey(Student,        on_delete=models.CASCADE, related_name="uniforms")
    session        = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term           = models.ForeignKey(AcademicTerm,    on_delete=models.CASCADE)
    student_class  = models.ForeignKey(StudentClass,    on_delete=models.CASCADE)
    uniform_type   = models.ForeignKey(UniformType,     on_delete=models.CASCADE)
    quantity       = models.PositiveIntegerField(default=1)
    price          = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    class Meta:
        ordering = ["student__surname", "uniform_type__name"]
        constraints = [CheckConstraint(check=Q(quantity__gt=0), name="uniform_quantity_positive")]

    def save(self, *a, **kw):
        self.price = _r2(self.uniform_type.price * self.quantity)
        super().save(*a, **kw)

    def __str__(self): return f"{self.student} – {self.uniform_type} × {self.quantity}"


class StudentUniform(models.Model):
    student        = models.ForeignKey(Student,        on_delete=models.CASCADE, related_name="student_uniforms")
    session        = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term           = models.ForeignKey(AcademicTerm,    on_delete=models.CASCADE)
    student_class  = models.ForeignKey(StudentClass,    on_delete=models.CASCADE)
    amount         = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["student__surname"]
        constraints = [
            CheckConstraint(check=Q(amount__gte=0), name="student_uniform_amount_positive"),
            UniqueConstraint(fields=["student", "session", "term", "student_class"], name="unique_student_uniform_payment"),
        ]

    def __str__(self): return f"{self.student} – {self.amount:,.0f}"
