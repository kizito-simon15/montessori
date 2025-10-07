
from __future__ import annotations

import re
from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import (
    CustomUser,
    ParentUser,
    TeacherUser,
    BursorUser,
    SecretaryUser,
    AcademicUser,
    HeadTeacherUser,
)
from apps.students.models import Student
from apps.staffs.models import Staff

# ────────────────────────────── constants ──────────────────────────────
DATE_WIDGET  = forms.DateInput(attrs={"type": "date"})
BASE_ATTRS   = {"class": "form-control"}
PW_REGEX     = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$")  # ≥6, letters+digits

# ───────────────────────── shared helpers ──────────────────────────────
class _BaseModelForm(forms.ModelForm):
    """Automatically applies .form-control to every widget."""
    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        for field in self.fields.values():
            field.widget.attrs = {**BASE_ATTRS, **field.widget.attrs}


class _BaseUserCreation(UserCreationForm, _BaseModelForm):
    """Adds password rules + eye-toggle-ready classes."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        pw_attrs = {
            **BASE_ATTRS,
            "class": BASE_ATTRS["class"] + " password-input",
            "autocomplete": "new-password",
            "minlength": 6,
            "pattern": PW_REGEX.pattern,   # browser-side hint
        }
        self.fields["password1"].widget.attrs = pw_attrs
        self.fields["password2"].widget.attrs = pw_attrs

    # additional rule after default Django checks
    def clean_password2(self) -> str:
        password = super().clean_password2()
        if not PW_REGEX.match(password):
            raise ValidationError(
                _(
                    "Password must be at least 6 characters long and "
                    "contain both letters and numbers."
                ),
                code="weak_password",
            )
        return password

# ───────────────────────── generic users ───────────────────────────────
class CustomUserCreationForm(_BaseUserCreation):
    class Meta:
        model  = CustomUser
        fields = ["username", "password1", "password2"]

# ───────────────────────── parent accounts ─────────────────────────────
class ParentUserCreationForm(_BaseUserCreation):
    student            = forms.ModelChoiceField(queryset=Student.objects.all())
    parent_first_name  = forms.CharField(max_length=200)
    parent_middle_name = forms.CharField(max_length=200, required=False)
    parent_last_name   = forms.CharField(max_length=200)

    class Meta:
        model  = ParentUser
        fields = [
            "username", "password1", "password2",
            "student",
            "parent_first_name", "parent_middle_name", "parent_last_name",
        ]

# ───────────────────────── staff-derived accounts ──────────────────────
class StaffUserCreationForm(_BaseUserCreation):
    staff = forms.ModelChoiceField(queryset=Staff.objects.all())

    class Meta:
        model  = CustomUser  # overridden in subclasses
        fields = ["username", "password1", "password2", "staff"]


class TeacherUserCreationForm(StaffUserCreationForm):
    class Meta(StaffUserCreationForm.Meta):
        model = TeacherUser


class BursorUserCreationForm(StaffUserCreationForm):
    class Meta(StaffUserCreationForm.Meta):
        model = BursorUser


class SecretaryUserCreationForm(StaffUserCreationForm):
    class Meta(StaffUserCreationForm.Meta):
        model = SecretaryUser


class AcademicUserCreationForm(StaffUserCreationForm):
    class Meta(StaffUserCreationForm.Meta):
        model = AcademicUser


class HeadTeacherUserCreationForm(StaffUserCreationForm):
    class Meta(StaffUserCreationForm.Meta):
        model = HeadTeacherUser

# ───────────────────────── profile picture upload ──────────────────────
class ProfilePictureForm(_BaseModelForm):
    class Meta:
        model  = CustomUser
        fields = ["profile_picture"]


from django import forms
from .models import UserProfile, CustomUser

class ProfileUpdateForm(forms.ModelForm):
    """
    Edits the UserProfile (phone, bio …) *and* lets the user swap avatar.
    """
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model  = UserProfile
        fields = ["phone", "bio"]          # add more if you extend the model
        widgets = {
            "bio": forms.Textarea(attrs={"rows":4, "class":"form-control"}),
            "phone": forms.TextInput(attrs={"class":"form-control"}),
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        # save avatar on the related CustomUser instance
        pic = self.cleaned_data.get("profile_picture")
        if pic:
            profile.user.profile_picture = pic
            profile.user.save(update_fields=["profile_picture"])
        if commit:
            profile.save()
        return profile
