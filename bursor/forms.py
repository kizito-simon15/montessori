from __future__ import annotations
"""
bursor/forms.py
Updated 03 Jul 2025

• Removes non‑editable `amount` from InvoiceItem inline‑formset
  (avoids FieldError).
• Shares finance app models – no duplicate business logic.
• Keeps helper filters & answer form unchanged.
"""

from typing import Any, List, Tuple

from django import forms
from django.forms import inlineformset_factory, modelformset_factory

from apps.finance.models import Invoice, InvoiceItem, Receipt
from apps.corecode.models import AcademicSession, Installment, StudentClass

from .models import BursorAnswer

# ────────────────────────────────────────────────────────────────────────────
# 1. Inline formsets
# ────────────────────────────────────────────────────────────────────────────

# Invoice items – omit the non‑editable “amount” column
BursorInvoiceItemFormset = inlineformset_factory(
    parent_model=Invoice,
    model=InvoiceItem,
    fields=["description", "category", "quantity", "unit_price"],
    extra=1,
    can_delete=True,
)

# Receipts – keep all editable fields
BursorInvoiceReceiptFormSet = inlineformset_factory(
    Invoice,
    Receipt,
    fields=["amount_paid", "date_paid", "comment", "payment_method"],
    extra=0,
    can_delete=True,
)

# ────────────────────────────────────────────────────────────────────────────
# 2. Bulk‑invoice model formset
# ────────────────────────────────────────────────────────────────────────────

Invoices = modelformset_factory(
    Invoice,
    fields="__all__",  # include only editable fields
    extra=4,
)

# ────────────────────────────────────────────────────────────────────────────
# 3. Filter helper (session / installment / class)
# ────────────────────────────────────────────────────────────────────────────

class BursorSessionInstallFilterForm(forms.Form):
    """Dropdown + search helpers for invoice/receipt tables."""

    session = forms.ChoiceField(label="Session", required=False)
    install = forms.ChoiceField(label="Installment", required=False)
    class_for = forms.ChoiceField(label="Class", required=False)
    student_name = forms.CharField(label="Student", required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["session"].choices = self._choices(AcademicSession, "All Sessions")
        self.fields["install"].choices = self._choices(Installment, "All Installments")
        self.fields["class_for"].choices = self._choices(StudentClass, "All Classes")

    @staticmethod
    def _choices(model, all_label: str) -> List[Tuple[str | None, str]]:
        try:
            return [(None, all_label)] + list(model.objects.values_list("id", "name"))
        except Exception:
            # model table might not exist during migrations / tests
            return [(None, all_label)]

# ────────────────────────────────────────────────────────────────────────────
# 4. Answer form (Q&A feature)
# ────────────────────────────────────────────────────────────────────────────

class BursorAnswerForm(forms.ModelForm):
    class Meta:
        model = BursorAnswer
        fields = ["answer", "audio_answer"]
        widgets = {
            "answer": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter your answer here…",
                }
            ),
            "audio_answer": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "audio/*"}
            ),
        }

    audio_answer = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": "audio/*"}
        ),
        label="Upload audio (optional)",
    )
