# forms.py
from django import forms
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'participants', 'location']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'font-size: 1.2em; padding: 10px; border-radius: 8px;',
                'placeholder': 'Enter event title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'style': 'font-size: 1.2em; padding: 10px; border-radius: 8px; height: 120px;',
                'placeholder': 'Enter event description'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'style': 'font-size: 1.2em; padding: 10px; border-radius: 8px;',
                'type': 'date'
            }),
            'participants': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'font-size: 1.2em; padding: 10px; border-radius: 8px; height: 120px;'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'font-size: 1.2em; padding: 10px; border-radius: 8px;',
                'placeholder': 'Enter event location'
            }),
        }
