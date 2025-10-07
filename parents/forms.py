from django import forms
from .models import ParentComments, StudentComments, InvoiceComments

class ParentCommentsForm(forms.ModelForm):
    class Meta:
        model = ParentComments
        fields = ['comment', 'audio_comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter your comments here...'}),
        }
        labels = {
            'comment': 'Parent Comments',
            'audio_comment': 'Upload Audio Comment',
        }

class StudentCommentsForm(forms.ModelForm):
    class Meta:
        model = StudentComments
        fields = ['comment', 'audio_comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 10, 'cols': 80, 'style': 'resize:none;'}),
        }
        labels = {
            'comment': 'Student Comments',
            'audio_comment': 'Upload Audio Comment',
        }

class InvoiceCommentsForm(forms.ModelForm):
    class Meta:
        model = InvoiceComments
        fields = ['comment', 'audio_comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'cols': 40, 'placeholder': 'Dear parent, your comments for this invoice are required', 'style': 'border-radius: 10px;'}),
        }
        labels = {
            'comment': 'Invoice Comments',
            'audio_comment': 'Upload Audio Comment',
        }
