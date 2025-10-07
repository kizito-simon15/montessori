from django import forms
from .models import Property
from apps.corecode.models import AcademicSession

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['name', 'quantity', 'description']  # Include description field
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter property name'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter quantity'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter description',
                'rows': 4,  # Set rows for better display
                'style': 'resize: vertical;'  # Allow vertical resizing of the textarea
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        current_session = AcademicSession.objects.filter(current=True).first()
        if not current_session:
            raise forms.ValidationError("No active session found.")
        return cleaned_data


class UpdatePropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['name', 'quantity', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter property name'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter quantity'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter description', 
                'rows': 4
            }),
        }
