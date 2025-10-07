from django import forms
from django.forms import modelformset_factory
from apps.corecode.models import StudentClass, AcademicSession, AcademicTerm, ExamType, Subject
from alevel_students.models import ALevelStudent
from alevel_results.models import ALevelResult, ALevelStudentInfos

class ClassSelectionForm(forms.Form):
    class_choices = forms.ModelChoiceField(queryset=StudentClass.objects.all(), widget=forms.RadioSelect)

class ResultEntryForm(forms.ModelForm):
    class Meta:
        model = ALevelResult
        fields = ['test_score', 'exam_score']
        widgets = {
            'test_score': forms.NumberInput(attrs={'class': 'form-control small-input', 'step': '0.01', 'min': '0', 'max': '100'}),
            'exam_score': forms.NumberInput(attrs={'class': 'form-control small-input', 'step': '0.01', 'min': '0', 'max': '100'}),
        }

class SessionTermExamSubjectForm(forms.Form):
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; max-width: 600px;'})
    )
    term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; max-width: 600px;'})
    )
    exam = forms.ModelChoiceField(
        queryset=ExamType.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; max-width: 600px;'})
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'subjects'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_exam = ExamType.objects.filter(current=True).first()

        if current_session:
            self.fields['session'].initial = current_session
        if current_term:
            self.fields['term'].initial = current_term
        if current_exam:
            self.fields['exam'].initial = current_exam

        if not self.fields['session'].queryset.exists():
            self.fields['session'].queryset = AcademicSession.objects.none()
        if not self.fields['term'].queryset.exists():
            self.fields['term'].queryset = AcademicTerm.objects.none()
        if not self.fields['exam'].queryset.exists():
            self.fields['exam'].queryset = ExamType.objects.none()

class DateInput(forms.DateInput):
    input_type = 'date'

class ALevelStudentInfosForm(forms.ModelForm):
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    exam = forms.ModelChoiceField(
        queryset=ExamType.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    date_of_closing = forms.DateField(
        widget=DateInput(attrs={'type': 'date', 'class': 'datepicker form-control form-control-lg'})
    )
    date_of_opening = forms.DateField(
        widget=DateInput(attrs={'type': 'date', 'class': 'datepicker form-control form-control-lg'})
    )

    class Meta:
        model = ALevelStudentInfos
        fields = ['session', 'term', 'exam', 'disprine', 'sports', 'care_of_property', 'collaborations', 'date_of_closing', 'date_of_opening', 'teacher_comments', 'head_comments']
        widgets = {
            'disprine': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'sports': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'care_of_property': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'collaborations': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'teacher_comments': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
            'head_comments': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields['session'].queryset = AcademicSession.objects.all()
            self.fields['term'].queryset = AcademicTerm.objects.all()
            self.fields['exam'].queryset = ExamType.objects.all()

            self.fields['session'].initial = AcademicSession.objects.filter(current=True).first()
            self.fields['term'].initial = AcademicTerm.objects.filter(current=True).first()
            self.fields['exam'].initial = ExamType.objects.filter(current=True).first()
        except Exception:
            self.fields['session'].queryset = AcademicSession.objects.none()
            self.fields['term'].queryset = AcademicTerm.objects.none()
            self.fields['exam'].queryset = ExamType.objects.none()

class CreateResults(forms.Form):
    session = forms.ModelChoiceField(queryset=AcademicSession.objects.all())
    term = forms.ModelChoiceField(queryset=AcademicTerm.objects.all())
    exam = forms.ModelChoiceField(queryset=ExamType.objects.all())
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(), widget=forms.CheckboxSelectMultiple
    )

EditResults = modelformset_factory(
    ALevelResult,
    fields=("test_score", "exam_score", "id"),
    extra=0,
    can_delete=True
)

class ViewResultsForm(forms.ModelForm):
    class Meta:
        model = ALevelResult
        fields = ['student', 'test_score', 'exam_score', 'current_class']
        widgets = {
            'test_score': forms.TextInput(attrs={'placeholder': '', 'value': ''}),
            'exam_score': forms.TextInput(attrs={'placeholder': '', 'value': ''}),
        }

ViewResultsFormSet = modelformset_factory(ALevelResult, form=ViewResultsForm, extra=0)