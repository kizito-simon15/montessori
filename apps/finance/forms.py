"""
apps/finance/forms.py
────────────────────────────────────────────────────────────────────────────
Modern “iPhone-style” Django forms  •  refreshed 05 Jul 2025

Includes:
    • BudgetForm         – category-aware; Term & Installment only for Per-Term
    • SchoolFeesForm     – per-session + per-category annual fees
    • SalaryInvoiceForm  – absolute PAYE + 0 % WCF
    • Invoice / Receipt  – cycle-aware helpers
    • Uniform & Student-Uniform forms
"""

from __future__ import annotations
from django.contrib import messages
import logging, re
from django.conf import settings    
from decimal import Decimal, InvalidOperation
from typing  import Any
from django.forms import BaseInlineFormSet, inlineformset_factory
from django import forms
from django.core.exceptions import ValidationError
from django.utils            import timezone
from django.db.models import Q, Sum   
from apps.corecode.models   import AcademicSession, AcademicTerm, Installment, StudentClass
from apps.staffs.models      import Staff
from apps.students.models    import Student, StudentTermAssignment
from .models                 import (
    Budget, BudgetCategory,
    Deduction,
    Invoice,
    Receipt,
    SalaryInvoice,
    SchoolFees,
    StudentUniform,
    Uniform, UniformType,
)
from .widgets                import StaffSelectWithData   # custom <select>

logger = logging.getLogger(__name__)


# ───────────────────────── Tailwind helpers ────────────────────────────────
TW_INPUT = (
    "block w-full rounded-full border border-gray-300 "
    "bg-white px-4 py-2 text-gray-900 placeholder-gray-400 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
)
TW_SELECT = (
    "block w-full rounded-full border border-gray-300 "
    "bg-white px-4 py-2 pr-8 text-gray-900 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
)
TW_TEXTAREA = (
    "block w-full rounded-2xl border border-gray-300 "
    "bg-white px-4 py-3 text-gray-900 placeholder-gray-400 shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600"
)
TW_TEXT = (
    "block w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 "
    "text-gray-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-600"
)

AMOUNT_RE = re.compile(r"[^\d.]")    # keep digits + dot only



# ─── Tailwind helpers (reuse if you already defined them higher up) ─────────
TW_INPUT   = ("block w-full rounded-full border border-gray-300 bg-white "
              "px-4 py-2 text-gray-900 placeholder-gray-400 shadow-sm "
              "focus:outline-none focus:ring-2 focus:ring-indigo-600 "
              "focus:border-indigo-600")
TW_SELECT  = TW_INPUT + " pr-8"
TW_TEXT    = ("block w-full rounded-2xl border border-gray-300 bg-white "
              "px-4 py-3 text-gray-900 shadow-sm focus:outline-none "
              "focus:ring-2 focus:ring-indigo-600")

def tw(cls: str, **extra: Any) -> dict[str, str]:
    """Tiny shortcut: build widget `attrs` dict with Tailwind classes."""
    attrs = {"class": cls}
    attrs.update({k: str(v) for k, v in extra.items()})
    return attrs



def sanitize_decimal(value: str | Decimal) -> Decimal:
    """Convert user-supplied string → positive 2-dp Decimal."""
    if isinstance(value, Decimal):
        cleaned = value
    else:
        try:
            cleaned = Decimal(AMOUNT_RE.sub("", str(value)))
        except (InvalidOperation, ValueError):
            raise ValidationError("Enter a valid number.") from None
    if cleaned <= 0:
        raise ValidationError("Amount must be positive.")
    return cleaned.quantize(Decimal("0.01"))

def tw(cls, **extra):            # attrs builder
    a = {"class": cls}
    a.update({k: str(v) for k, v in extra.items()})
    return a


# ═══════════════════════  BUDGET FORM  ═════════════════════════════════════
class BudgetForm(forms.ModelForm):
    """
    Minimal envelope:
      • Name, Category (radio pills), Session, Allocated amount
      • No term/installment fields any longer
    """

    class Meta:
        model  = Budget
        fields = ("name", "category", "session", "allocated_amount")
        widgets = {
            "name": forms.TextInput(
                attrs=tw(TW_INPUT, placeholder="e.g. ICT Supplies 2025",
                         autocomplete="off")
            ),
            # hidden; value set by Alpine radio-pills in the template
            "category": forms.Select(attrs=tw(TW_SELECT)),
            "session":  forms.Select(attrs=tw(TW_SELECT)),
            "allocated_amount": forms.NumberInput(
                attrs=tw(TW_INPUT, step="0.01", min="0.01",
                         placeholder="Amount in TZS")
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # hide the real <select> for category
        self.fields["category"].widget = forms.HiddenInput()

    def clean_allocated_amount(self):
        amt = self.cleaned_data["allocated_amount"]
        if amt <= 0:
            raise ValidationError("Allocated amount must be positive.")
        return amt


# ═══════════════════════  SCHOOL-FEES FORM  ════════════════════════════════

class SchoolFeesForm(forms.ModelForm):
    class Meta:
        model = SchoolFees
        fields = ("session", "category", "annual_amount")
        widgets = {
            "session": forms.Select(attrs={
                'class': 'form-select shadow-sm',
                'placeholder': 'Select academic session'
            }),
            "category": forms.TextInput(attrs={
                'class': 'form-control shadow-sm',
                'placeholder': 'Enter category (e.g., Boarding, Day Scholar)'
            }),
            "annual_amount": forms.NumberInput(attrs={
                'class': 'form-control shadow-sm',
                'min': '1',
                'placeholder': 'Annual amount (e.g., 1000000)'
            }),
        }

    def clean_category(self):
        category = self.cleaned_data.get("category")
        if not category:
            raise ValidationError("Category is required.")
        if len(category) > 50:
            raise ValidationError("Category cannot exceed 50 characters.")
        return category.strip()

    def clean_annual_amount(self):
        amt = self.cleaned_data.get("annual_amount")
        if not isinstance(amt, int) or amt <= 0:
            raise ValidationError("Annual amount must be a positive whole number.")
        return amt

    def clean(self):
        cd = super().clean()
        sess, cat = cd.get("session"), cd.get("category")
        if sess and cat:
            qs = SchoolFees.objects.filter(session=sess, category=cat).exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Fees for this session and category already exist.")
        return cd

class BudgetForm(forms.ModelForm):
    """
    Minimal envelope:
      • Name, Category (radio pills), Session, Allocated amount
      • No term/installment fields any longer
    """

    class Meta:
        model  = Budget
        fields = ("name", "category", "session", "allocated_amount")
        widgets = {
            "name": forms.TextInput(
                attrs=tw(TW_INPUT, placeholder="e.g. ICT Supplies 2025",
                         autocomplete="off")
            ),
            # hidden; value set by Alpine radio-pills in the template
            "category": forms.Select(attrs=tw(TW_SELECT)),
            "session":  forms.Select(attrs=tw(TW_SELECT)),
            "allocated_amount": forms.NumberInput(
                attrs=tw(TW_INPUT, step="0.01", min="0.01",
                         placeholder="Amount in TZS")
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # hide the real <select> for category
        self.fields["category"].widget = forms.HiddenInput()

    def clean_allocated_amount(self):
        amt = self.cleaned_data["allocated_amount"]
        if amt <= 0:
            raise ValidationError("Allocated amount must be positive.")
        return amt



# ═══════════════════════════════════════════════════════════════════════════
#  SalaryInvoiceForm
# ═══════════════════════════════════════════════════════════════════════════
class SalaryInvoiceForm(forms.ModelForm):
    """
    One payslip per staff × month.

    • Budget list limited to the current academic session.
    • Staff list limited to “active” employees.
    • Month is normalised → first-day so uniqueness checks work.
    • 🏷  Duplicate slip guard in `clean()`.
    """

    class Meta:
        model  = SalaryInvoice
        fields = (
            "budget", "staff", "month",
            "basic_salary", "special_allowance", "allowance",
            "paye_amount", "remarks",
        )
        widgets = {
            "budget":            forms.Select(attrs=tw(TW_SELECT)),
            "staff":             forms.Select(attrs=tw(TW_SELECT)),
            "month":             forms.DateInput(attrs=tw(TW_INPUT, type="date")),
            "basic_salary":      forms.NumberInput(attrs=tw(TW_INPUT, step="0.01", min="0")),
            "special_allowance": forms.NumberInput(attrs=tw(TW_INPUT, step="0.01", min="0")),
            "allowance":         forms.NumberInput(attrs=tw(TW_INPUT, step="0.01", min="0")),
            "paye_amount":       forms.NumberInput(attrs=tw(TW_INPUT, step="0.01", min="0")),
            "remarks":           forms.Textarea(attrs=tw(TW_TEXT, rows="3")),
        }

    # ── dynamic query-sets / defaults ────────────────────────────────────
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        current_session = AcademicSession.objects.filter(current=True).first()

        # budget list → only envelopes of the current session
        self.fields["budget"].queryset = (
            Budget.objects.filter(session=current_session) if current_session
            else Budget.objects.none()
        )

        # staff selector → active only
        self.fields["staff"].queryset = (
            Staff.objects.filter(current_status="active")
            .order_by("surname", "firstname")
        )

    # ── field clean-ups ───────────────────────────────────────────────────
    def clean_month(self):
        """Coerce any YYYY-MM-DD into first-day-of-month (YYYY-MM-01)."""
        month = self.cleaned_data["month"]
        return month.replace(day=1) if month else month

    def clean_allowance(self):
        """Absorb empty string → Decimal('0.00') for servers running with JS off."""
        raw = self.cleaned_data.get("allowance")
        return Decimal("0.00") if raw in (None, "") else raw

    # ── object-level validation ───────────────────────────────────────────
    def clean(self):
        cd     = super().clean()
        staff  = cd.get("staff")
        month  = cd.get("month")          # already first-day
        paye   = cd.get("paye_amount", Decimal("0"))

        if paye < 0:
            self.add_error("paye_amount", "PAYE cannot be negative.")

        # duplicate guard
        if staff and month and SalaryInvoice.objects.filter(
            staff=staff, month=month
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError(
                f"{staff} already has a salary slip for {month:%B %Y}."
            )
        return cd


# ═══════════════════════════════════════════════════════════════════════════
#  Inline extra-deductions
# ═══════════════════════════════════════════════════════════════════════════
class DeductionForm(forms.ModelForm):
    class Meta:
        model   = Deduction
        fields  = ("reason", "amount")
        widgets = {
            "reason": forms.TextInput(attrs=tw(TW_INPUT, placeholder="Reason")),
            "amount": forms.NumberInput(attrs=tw(TW_INPUT, step="0.01", min="0")),
        }

    def clean_amount(self):
        amt = self.cleaned_data["amount"]
        if amt < 0:
            raise ValidationError("Amount must be zero or positive.")
        return amt

# ──────────────────────────────────────────────────────────────
#  Salary‑invoice inline deductions
# ──────────────────────────────────────────────────────────────


class _BaseDeductionFormSet(BaseInlineFormSet):
    """
    Treat a form that has *all* its fields blank as ‘empty’ so it does not
    trigger a validation error when the user leaves the initial row untouched.
    """
    def clean(self):
        super().clean()
        # Nothing else – BaseInlineFormSet already skips empty forms,
        # we just keep the hook here for future custom cross‑row checks.



DeductionFormSet = inlineformset_factory(
    SalaryInvoice, Deduction,
    form        = DeductionForm,
    formset     = _BaseDeductionFormSet,
    extra       = 0,          # JS creates rows; Django receives them
    can_delete  = True,
    min_num     = 0,
    validate_min= False,
)


# ═════════════════════  INVOICE  ════════════════════════════════════════════

class InvoiceForm(forms.ModelForm):
    """
    Invoice form – now shows *cross-session* previous balance.
    """

    balance_from_previous_install = forms.IntegerField(
        label="Previous Balance",
        required=False,
        disabled=True,
        widget=forms.NumberInput(
            attrs=tw(TW_INPUT + " opacity-60", readonly="readonly"),
        ),
    )

    class Meta:
        model  = Invoice
        fields = [
            "student", "session", "installment", "school_fees",
            "invoice_amount", "due_date", "notes", "status",
        ]
        widgets = {
            "student":        forms.Select(attrs=tw(TW_SELECT)),
            "session":        forms.Select(attrs=tw(TW_SELECT)),
            "installment":    forms.Select(attrs=tw(TW_SELECT)),
            "school_fees":    forms.Select(attrs=tw(TW_SELECT)),
            "invoice_amount": forms.NumberInput(attrs=tw(TW_INPUT, min="0")),
            "due_date":       forms.DateInput(attrs=tw(TW_INPUT, type="date")),
            "notes":          forms.Textarea(attrs=tw(TW_TEXTAREA, rows="3")),
            "status":         forms.Select(attrs=tw(TW_SELECT)),
        }

    # ----------------------------------------------------------
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        cur_session = AcademicSession.objects.filter(current=True).first()
        cur_install = Installment.objects.filter(current=True).first()

        # student dropdown (active + registered this term)
        reg_ids = StudentTermAssignment.objects.filter(
            academic_session=cur_session, academic_term__current=True
        ).values_list("student_id", flat=True)

        self.fields["student"].queryset = (
            Student.objects.filter(id__in=reg_ids,
                                   current_status="active", completed=False)
                   .order_by("surname", "firstname")
        )

        # defaults
        if cur_session:
            self.fields["session"].initial = cur_session
            if self.request and not getattr(self.request.user, "is_superuser", False):
                self.fields["session"].queryset = AcademicSession.objects.filter(current=True)
        if cur_install:
            self.fields["installment"].initial = cur_install

        # fees picker limited to selected session
        sess_id = (
            self.data.get("session")
            or self.instance.session_id
            or getattr(cur_session, "id", None)
        )
        if sess_id:
            self.fields["school_fees"].queryset = (
                SchoolFees.objects.filter(session_id=sess_id).order_by("category")
            )
        else:
            self.fields["school_fees"].queryset = SchoolFees.objects.none()

        # ---------- previous balance (cross-session) ----------
        if self.instance.pk:
            bal = self.instance.balance_from_previous_install
        else:
            bal = 0
            sid  = self.data.get("student")
            inst = self.data.get("installment")
            if sid and sess_id and inst:
                prev = (
                    Invoice.objects
                           .filter(student_id=sid)
                           .filter(
                               Q(session__id__lt=sess_id) |
                               Q(session_id=sess_id, installment__id__lt=inst)
                           )
                           .aggregate(
                               exp=Sum("invoice_amount"),
                               paid=Sum("receipts__amount_paid"),
                           )
                )
                bal = (prev["exp"] or 0) - (prev["paid"] or 0)

        self.fields["balance_from_previous_install"].initial = bal

    # ---------- validation ----------
    def clean_invoice_amount(self):
        amt = self.cleaned_data.get("invoice_amount")
        if amt is None or amt < 0:
            raise ValidationError("Amount must be a non-negative whole number.")
        return amt

    def clean(self):
        cd       = super().clean()
        session  = cd.get("session")
        sf       = cd.get("school_fees")
        amount   = cd.get("invoice_amount") or 0
        student  = cd.get("student")

        if not all([session, sf, student]):
            return cd

        if sf.session_id != session.id:
            raise ValidationError("Selected fees entry must belong to the chosen session.")

        used = (
            Invoice.objects.filter(student=student, session=session)
                           .exclude(pk=self.instance.pk)
                           .aggregate(t=Sum("invoice_amount"))["t"] or 0
        )
        if amount > sf.annual_amount - used:
            raise ValidationError("Invoice amount exceeds the tier’s remaining annual balance.")
        return cd


class ReceiptForm(forms.ModelForm):
    """
    • Caps payment at the *current* outstanding balance (edit-aware).  
    • Hard upper-limit 999 999 999.99 enforced client & server side.  
    • Uses glass-UI widgets consistent with the rest of the refresh.
    """
    HARD_CAP = Decimal("999999999.99")        # absolute ceiling

    class Meta:
        model  = Receipt
        fields = [
            "amount_paid", "date_paid", "payment_method",
            "transaction_reference", "comment",
        ]
        widgets = {
            "amount_paid": forms.TextInput(
                attrs=tw(
                    TW_INPUT,
                    inputmode="decimal",
                    placeholder="e.g. 1 234 567.80",
                    **{"data-maxhard": "999999999.99"},
                )
            ),
            "date_paid":  forms.DateInput(attrs=tw(TW_INPUT, type="date")),
            "payment_method": forms.Select(attrs=tw(TW_SELECT)),
            "transaction_reference": forms.TextInput(
                attrs=tw(TW_INPUT, placeholder="Bank / M-Pesa ref.")
            ),
            "comment": forms.Textarea(attrs=tw(TW_TEXTAREA, rows="3")),
        }

    # ──────────────────────────────────────────────────────────
    #  ctor – now swallows invoice *and* request kwargs gracefully
    # ──────────────────────────────────────────────────────────
    def __init__(self, *args, invoice=None, request=None, **kwargs):
        # allow CBVs to push kwargs without exploding
        invoice = invoice or kwargs.pop("invoice", None)
        request = request or kwargs.pop("request", None)

        self.invoice = invoice
        self.request = request                # future customisation hook

        super().__init__(*args, **kwargs)

        # default “today” when adding a brand-new receipt
        if not self.instance.pk and "date_paid" not in self.initial:
            self.initial["date_paid"] = timezone.now().date()

        # Front-end helper – limit & placeholder show current balance
        max_payable = self._allowed_balance()
        self.fields["amount_paid"].widget.attrs.update(
            {
                "data-max": f"{max_payable:.2f}",
                "placeholder": f"Up to {max_payable:,.2f} TZS",
            }
        )

    # ──────────────────────────────────────────────────────────
    #  helpers
    # ──────────────────────────────────────────────────────────
    def _allowed_balance(self) -> Decimal:
        """
        Returns the maximum the user can pay on *this* invoice at this moment.
        If editing an existing receipt we add its original amount back in so
        the user can adjust up/down freely without false “exceeds balance”.
        """
        if not self.invoice:
            return self.HARD_CAP

        bal = Decimal(self.invoice.overall_balance() or 0)
        if self.instance.pk:
            bal += self.instance.amount_paid
        return min(bal, self.HARD_CAP)

    # ──────────────────────────────────────────────────────────
    #  field-level validation
    # ──────────────────────────────────────────────────────────
    def clean_amount_paid(self):
        amt = sanitize_decimal(self.data.get(self.add_prefix("amount_paid"), ""))
        if amt > self.HARD_CAP:
            raise ValidationError("Amount exceeds 999 999 999.99 TZS.")

        max_payable = self._allowed_balance()
        if amt > max_payable:
            raise ValidationError(
                f"Payment exceeds remaining balance "
                f"({max_payable:,.2f} TZS)."
            )
        return amt

    def clean_date_paid(self):
        dp = self.cleaned_data.get("date_paid")
        if not dp:
            raise ValidationError("Date paid is required.")
        if dp > timezone.now().date():
            raise ValidationError("Date paid cannot be in the future.")
        return dp
    


InvoiceReceiptFormSet = forms.inlineformset_factory(
    Invoice, Receipt,
    fields=("amount_paid", "date_paid", "comment", "payment_method"),
    extra=0, can_delete=True
)


# ═════════════════════  UNIFORMS  ═══════════════════════════════════════════
class UniformForm(forms.ModelForm):
    class Meta:
        model  = Uniform
        fields = ["student", "student_class", "uniform_type", "quantity"]
        widgets = {
            "student":       forms.Select(attrs=tw(TW_SELECT)),
            "student_class": forms.Select(attrs=tw(TW_SELECT)),
            "uniform_type":  forms.Select(attrs=tw(TW_SELECT)),
            "quantity":      forms.NumberInput(attrs=tw(TW_INPUT, min="1", step="1")),
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["student"].queryset = Student.objects.filter(
            current_status="active", completed=False, current_class__isnull=False
        ).order_by("surname", "firstname")
        self.fields["student_class"].queryset = StudentClass.objects.order_by("name")
        self.fields["uniform_type"].queryset  = UniformType.objects.order_by("name")

    def clean_quantity(self):
        q = self.cleaned_data["quantity"]
        if q <= 0:
            raise ValidationError("Quantity must be positive.")
        return q

UniformFormSet = forms.formset_factory(UniformForm, extra=1)


class StudentUniformForm(forms.ModelForm):
    class Meta:
        model  = StudentUniform
        fields = ["amount"]
        widgets = {
            "amount": forms.NumberInput(attrs=tw(TW_INPUT, min="0.01", step="0.01")),
        }

    def clean_amount(self):
        amt = self.cleaned_data["amount"]
        if amt < 0:
            raise ValidationError("Amount cannot be negative.")
        return amt


class UniformTypeForm(forms.ModelForm):
    class Meta:
        model  = UniformType
        fields = ["name", "price"]
        widgets = {
            "name":  forms.TextInput(attrs=tw(TW_INPUT, placeholder="Shirt / Skirt / Sweater ...")),
            "price": forms.NumberInput(attrs=tw(TW_INPUT, min="0.01", step="0.01")),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        if UniformType.objects.filter(name=name).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Uniform type with this name already exists.")
        return name

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price < 0:
            raise ValidationError("Price cannot be negative.")
        return price


# ═════════════════════  BULK-INVOICE formset (unchanged)  ═══════════════════
Invoices = forms.modelformset_factory(
    Invoice,
    fields=[
        "student", "session", "installment", "school_fees",
        "invoice_amount", "due_date", "notes", "status",
    ],
    extra=4,
)
