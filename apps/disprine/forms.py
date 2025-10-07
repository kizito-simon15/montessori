from django import forms
from .models import DisciplineIssue, Action
from apps.students.models import Student
from apps.staffs.models import Staff

class DisciplineIssueForm(forms.ModelForm):
    reported_by_choice = forms.ChoiceField(
        choices=[
            ('student', 'Student'),
            ('staff', 'Staff'),
            ('both', 'Both')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    reported_by_student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg', 'id': 'student-select'})
    )
    reported_by_staff = forms.ModelChoiceField(
        queryset=Staff.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg', 'id': 'staff-select'})
    )

    class Meta:
        model = DisciplineIssue
        fields = [
            'student',
            'reported_by_choice',
            'reported_by_student',
            'reported_by_staff',
            'issue_description',
            'action_taken',
            'resolved',
            'issue_file'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control form-control-lg', 'id': 'student-select-main'}),
            'issue_description': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
            'action_taken': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
            'resolved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'issue_file': forms.FileInput(attrs={'class': 'form-control form-control-lg'}),
        }

class ActionForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = ['action_description', 'action_taker']
        widgets = {
            'action_description': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
            'action_taker': forms.Select(attrs={'class': 'form-control form-control-lg'})
        }
