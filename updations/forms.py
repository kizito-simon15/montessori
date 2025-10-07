from django import forms
from .models import StudentClass
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType

class MoveStudentsForm(forms.Form):
    from_class = forms.ModelChoiceField(queryset=StudentClass.objects.all(), label='From Class')
    to_class = forms.ModelChoiceField(queryset=StudentClass.objects.all(), label='To Class')

class DeleteStudentsForm(forms.Form):
    class_to_delete = forms.ModelChoiceField(queryset=StudentClass.objects.all(), label='Class to Delete Students From')

class CopyResultsForm(forms.Form):
    source_session = forms.ModelChoiceField(queryset=AcademicSession.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    source_term = forms.ModelChoiceField(queryset=AcademicTerm.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    source_exam_type = forms.ModelChoiceField(queryset=ExamType.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    destination_session = forms.ModelChoiceField(queryset=AcademicSession.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    destination_term = forms.ModelChoiceField(queryset=AcademicTerm.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    destination_exam_type = forms.ModelChoiceField(queryset=ExamType.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for source session, term, and exam type
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_exam_type = ExamType.objects.filter(current=True).first()

        if current_session:
            self.fields['source_session'].initial = current_session
            self.fields['destination_session'].initial = current_session
        if current_term:
            self.fields['source_term'].initial = current_term
            self.fields['destination_term'].initial = current_term
        if current_exam_type:
            self.fields['source_exam_type'].initial = current_exam_type
            self.fields['destination_exam_type'].initial = current_exam_type
