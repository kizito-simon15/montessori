from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from .models import ALevelStudent

class ALevelStudentForm(forms.ModelForm):
    class Meta:
        model = ALevelStudent
        fields = [
            'registration_number', 'current_status', 'firstname', 'middle_name', 'surname', 'gender', 'date_of_birth',
            'current_class', 'date_of_admission', 'father_mobile_number', 'mother_mobile_number',
            'address', 'others', 'passport', 'parent_student_id', 'completed'
        ]
        widgets = {
            'registration_number': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Registration Number'}),
            'current_status': forms.Select(attrs={'class': 'form-control shadow-sm'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'First Name'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Middle Name'}),
            'surname': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Surname'}),
            'gender': forms.Select(attrs={'class': 'form-control shadow-sm'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control shadow-sm'}),
            'current_class': forms.Select(attrs={'class': 'form-control shadow-sm'}),
            'date_of_admission': forms.DateInput(attrs={'type': 'date', 'class': 'form-control shadow-sm'}),
            'father_mobile_number': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Father Mobile Number'}),
            'mother_mobile_number': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Mother Mobile Number'}),
            'address': forms.Textarea(attrs={'class': 'form-control shadow-sm', 'rows': 2, 'placeholder': 'Address'}),
            'others': forms.Textarea(attrs={'class': 'form-control shadow-sm', 'rows': 2, 'placeholder': 'Additional Information'}),
            'passport': forms.ClearableFileInput(attrs={'class': 'form-control shadow-sm'}),
            'parent_student_id': forms.NumberInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Parent Student ID'}),
            'completed': forms.CheckboxInput(attrs={'class': 'form-check-input custom-toggle'}),
        }

    def clean_registration_number(self):
        registration_number = self.cleaned_data.get('registration_number')
        if not registration_number:
            raise forms.ValidationError(_("Registration number is required."))
        
        # Use the same regex as in the model to validate registration_number
        import re
        if not re.match(r"^[A-Za-z0-9/-]+$", registration_number):
            raise forms.ValidationError(_("Registration number must contain only letters, numbers, slashes, or hyphens (e.g., S0196/001/2025, S133-212-2025)."))
        return registration_number

    def clean_father_mobile_number(self):
        phone_number = self.cleaned_data.get('father_mobile_number')
        if not phone_number:
            raise forms.ValidationError(_("Father's mobile number is required."))
        if not phone_number.startswith('+255'):
            raise forms.ValidationError(_("Father's mobile number must start with +255."))
        return phone_number

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth is None:
            raise forms.ValidationError(_("Date of birth is required."))
        return date_of_birth