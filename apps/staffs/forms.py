"""Staff app – forms
Matches Staff model (teaching / non-teaching, job_title, special_allowance)."""

from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError

from .models import Staff, StaffAttendance


# ──────────────────────────────────────────────────────────────
#  MAIN STAFF FORM
# ──────────────────────────────────────────────────────────────
class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        exclude = ["staff_id"]                       # auto-generated
        widgets = {
            # dates
            "date_of_birth":       forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "date_of_admission":   forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "contract_start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "contract_end_date":   forms.DateInput(attrs={"type": "date", "class": "form-control"}),

            # selects
            "current_status": forms.Select(attrs={"class": "form-select"}),
            "gender":         forms.Select(attrs={"class": "form-select"}),
            "staff_category": forms.Select(attrs={"class": "form-select"}),
            "department":     forms.Select(attrs={"class": "form-select"}),

            # text / nums
            "firstname":               forms.TextInput(attrs={"class": "form-control"}),
            "middle_name":             forms.TextInput(attrs={"class": "form-control"}),
            "surname":                 forms.TextInput(attrs={"class": "form-control"}),
            "job_title":               forms.TextInput(attrs={"class": "form-control"}),
            "salary":                  forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "special_allowance":       forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "mobile_number":           forms.TextInput(attrs={"class": "form-control"}),
            "emergency_contact_number":forms.TextInput(attrs={"class": "form-control"}),
            "email":                   forms.EmailInput(attrs={"class": "form-control"}),
            "bank_name":               forms.TextInput(attrs={"class": "form-control"}),
            "bank_account_number":     forms.TextInput(attrs={"class": "form-control"}),
            "bank_branch":             forms.TextInput(attrs={"class": "form-control"}),
            "registration_number":     forms.TextInput(attrs={"class": "form-control"}),
            "guarantor":               forms.TextInput(attrs={"class": "form-control"}),
            "contract_duration":       forms.TextInput(attrs={"class": "form-control"}),
            "nida_id":                 forms.TextInput(attrs={"class": "form-control"}),
            "tin_number":              forms.TextInput(attrs={"class": "form-control"}),
            "address":                 forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "others":                  forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            # HELSB
            "has_helsb":  forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "helsb_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            # file
            "passport_photo": forms.FileInput(attrs={"class": "form-control"}),
        }

    # ── pretty labels & initial values
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.mobile_number:
            self.fields["mobile_number"].initial = "+255"
        if not self.instance.emergency_contact_number:
            self.fields["emergency_contact_number"].initial = "+255"

        self.fields["helsb_rate"].label = "HELSB rate (%)"
        self.fields["special_allowance"].label = "Special Allowance (TZS)"

    # ── custom validators
    def clean_registration_number(self):
        reg = self.cleaned_data.get("registration_number")
        if reg and Staff.objects.filter(registration_number=reg).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This registration number is already in use.")
        return reg

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and Staff.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This email is already in use.")
        return email


# ──────────────────────────────────────────────────────────────
#  ATTENDANCE TICK FORM
# ──────────────────────────────────────────────────────────────
class StaffAttendanceForm(forms.ModelForm):
    class Meta:
        model   = StaffAttendance
        fields  = ["is_present"]
        widgets = {"is_present": forms.CheckboxInput(attrs={"class": "form-check-input"})}
        labels  = {"is_present": "Mark attendance"}
