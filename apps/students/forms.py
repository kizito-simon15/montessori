from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from .models import Student

class StudentForm(forms.ModelForm):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control shadow-sm', 'id': 'id_gender'})
    )

    class Meta:
        model = Student
        fields = [
            'registration_number', 'current_status', 'firstname', 'middle_name', 'surname', 'gender', 'date_of_birth',
            'current_class', 'date_of_admission', 'category', 'guardian1_mobile_number', 'guardian2_mobile_number',
            'has_nhif', 'nhif_source', 'nhif_number', 'address', 'others', 'passport', 'parent_student_id', 'completed'
        ]
        widgets = {
            'registration_number': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'S1234567/0032/2025'}),
            'current_status': forms.Select(attrs={'class': 'form-control shadow-sm'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'First Name'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Middle Name'}),
            'surname': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Surname'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control shadow-sm'}),
            'current_class': forms.Select(attrs={'class': 'form-control shadow-sm'}),
            'date_of_admission': forms.DateInput(attrs={'type': 'date', 'class': 'form-control shadow-sm'}),
            'category': forms.Select(attrs={'class': 'form-control shadow-sm'}),
            'guardian1_mobile_number': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Guardian 1 Mobile Number'}),
            'guardian2_mobile_number': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'Guardian 2 Mobile Number (Optional)'}),
            'has_nhif': forms.CheckboxInput(attrs={'class': 'form-check-input custom-toggle'}),
            'nhif_source': forms.Select(attrs={'class': 'form-control shadow-sm'}),
            'nhif_number': forms.TextInput(attrs={'class': 'form-control shadow-sm', 'placeholder': 'NHIF Number'}),
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
        return registration_number

    def clean_guardian1_mobile_number(self):
        phone_number = self.cleaned_data.get('guardian1_mobile_number')
        if phone_number and not phone_number.startswith('+255'):
            raise forms.ValidationError(_("Guardian 1's mobile number must start with +255."))
        return phone_number

    def clean_guardian2_mobile_number(self):
        phone_number = self.cleaned_data.get('guardian2_mobile_number')
        if phone_number and not phone_number.startswith('+255'):
            raise forms.ValidationError(_("Guardian 2's mobile number must start with +255."))
        return phone_number

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth is None:
            raise forms.ValidationError(_("Date of birth is required."))
        return date_of_birth

    def clean(self):
        cleaned_data = super().clean()
        has_nhif = cleaned_data.get('has_nhif')
        nhif_source = cleaned_data.get('nhif_source')
        nhif_number = cleaned_data.get('nhif_number')
        if has_nhif:
            if not nhif_source:
                self.add_error('nhif_source', "NHIF source is required if the student has NHIF.")
            if not nhif_number:
                self.add_error('nhif_number', "NHIF number is required if the student has NHIF.")
        else:
            if nhif_source or nhif_number:
                self.add_error('has_nhif', "Please confirm if the student has NHIF coverage to provide NHIF details.")
        return cleaned_data