from django import forms
from .models import SecretaryAnswers

class SecretaryAnswerForm(forms.ModelForm):
    class Meta:
        model = SecretaryAnswers
        fields = ['answer', 'audio_answer']  # Include the audio field for upload
        widgets = {
            'answer': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Enter your answer here...'
            }),
            'audio_answer': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/*'  # Accept only audio files
            }),
        }

    audio_answer = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'audio/*'  # Restrict to audio files
        }),
        label="Upload an audio file (optional)"
    )
