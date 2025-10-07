# meetings/forms.py

from django import forms
from .models import Meeting, Agenda
from django.utils import timezone

class MeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['title', 'start_time', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter meeting title'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super(MeetingForm, self).__init__(*args, **kwargs)
        now = timezone.now()
        self.fields['start_time'].initial = now.strftime('%Y-%m-%dT%H:%M')
        self.fields['end_time'].initial = (now + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')


class AgendaForm(forms.ModelForm):
    class Meta:
        model = Agenda
        fields = ['description', 'start_time', 'end_time']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter agenda description'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super(AgendaForm, self).__init__(*args, **kwargs)
        now = timezone.now()
        self.fields['start_time'].initial = now.strftime('%Y-%m-%dT%H:%M')
        self.fields['end_time'].initial = (now + timezone.timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M')


# forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Meeting, Agenda, Participant, Notification

class EditMeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['title', 'start_time', 'end_time', 'is_active', 'is_past']

class EditAgendaForm(forms.ModelForm):
    class Meta:
        model = Agenda
        fields = ['description', 'start_time', 'end_time']

class EditParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['user', 'is_admin_invited', 'has_video', 'has_audio']

class EditNotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['user', 'message', 'is_read']

# Inline formsets for the related models with updated names
EditAgendaFormSet = inlineformset_factory(Meeting, Agenda, form=EditAgendaForm, extra=1, can_delete=True)
EditParticipantFormSet = inlineformset_factory(Meeting, Participant, form=EditParticipantForm, extra=1, can_delete=True)
EditNotificationFormSet = inlineformset_factory(Meeting, Notification, form=EditNotificationForm, extra=1, can_delete=True)
