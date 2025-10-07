from django import forms
from .models import Attendance
from apps.corecode.models import AcademicSession, AcademicTerm

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['session', 'term', 'attendance_date']
        widgets = {
            'session': forms.Select(attrs={'class': 'form-control selectpicker', 'data-live-search': 'true', 'data-size': '10'}),
            'term': forms.Select(attrs={'class': 'form-control selectpicker', 'data-live-search': 'true', 'data-size': '10'}),
            'attendance_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(AttendanceForm, self).__init__(*args, **kwargs)

        # Get the current session and term
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()

        # Set initial values for session and term fields
        if current_session:
            self.fields['session'].initial = current_session.id
        if current_term:
            self.fields['term'].initial = current_term.id
