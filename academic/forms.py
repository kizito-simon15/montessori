from django import forms
from apps.corecode.models import StudentClass, AcademicSession, AcademicTerm, ExamType, Subject
from apps.result.models import Result, StudentInfos
from .models import AcademicAnswer

# Define choices for behavior evaluation fields
BEHAVIOR_GRADES = [
    ('A', 'A (Excellent)'),
    ('B', 'B (Very Good)'),
    ('C', 'C (Good)'),
    ('D', 'D (Satisfactory)'),
    ('F', 'F (Needs Improvement)'),
]

class ClassSelectionForm(forms.Form):
    class_choices = forms.ModelChoiceField(queryset=StudentClass.objects.all(), widget=forms.RadioSelect)

class ResultEntryForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['test_score', 'exam_score']
        widgets = {
            'test_score': forms.NumberInput(attrs={'class': 'form-control small-input', 'step': '0.01'}),
            'exam_score': forms.NumberInput(attrs={'class': 'form-control small-input', 'step': '0.01'}),
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
        # Set initial values if current session, term, or exam exist
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_exam = ExamType.objects.filter(current=True).first()
        
        if current_session:
            self.fields['session'].initial = current_session
        if current_term:
            self.fields['term'].initial = current_term
        if current_exam:
            self.fields['exam'].initial = current_exam

        # If there are no entries, set to None (or handle as needed)
        if not self.fields['session'].queryset.exists():
            self.fields['session'].queryset = AcademicSession.objects.none()
        if not self.fields['term'].queryset.exists():
            self.fields['term'].queryset = AcademicTerm.objects.none()
        if not self.fields['exam'].queryset.exists():
            self.fields['exam'].queryset = ExamType.objects.none()

class DateInput(forms.DateInput):
    input_type = 'date'

class StudentInfosForm(forms.ModelForm):
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
        queryset=AcademicTerm.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    date_of_closing = forms.DateField(
        widget=DateInput(attrs={'type': 'date', 'class': 'datepicker form-control form-control-lg'})
    )
    date_of_opening = forms.DateField(
        widget=DateInput(attrs={'type': 'date', 'class': 'datepicker form-control form-control-lg'})
    )
    disprine = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    sports = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    care_of_property = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    academic_collaboration = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    community_collaboration = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    overall_collaboration = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    cooperation_with_peers = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    honesty = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    hygiene = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    willingness_to_work = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    respect = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    collaboration_in_work = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    love_for_work = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    behavior_improvement = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    effort = forms.ChoiceField(
        choices=BEHAVIOR_GRADES,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    head_comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
        required=False
    )
    academic_answers = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 3}),
        required=False
    )

    class Meta:
        model = StudentInfos
        fields = [
            'session', 'term', 'exam', 'disprine', 'sports', 'care_of_property',
            'academic_collaboration', 'community_collaboration', 'overall_collaboration',
            'cooperation_with_peers', 'honesty', 'hygiene', 'willingness_to_work',
            'respect', 'collaboration_in_work', 'love_for_work', 'behavior_improvement',
            'effort', 'date_of_closing', 'date_of_opening', 'head_comments', 'academic_answers'
        ]

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

class AcademicAnswersForm(forms.ModelForm):
    class Meta:
        model = StudentInfos
        fields = ['academic_answers']
        widgets = {
            'academic_answers': forms.Textarea(attrs={'rows': 4, 'cols': 30, 'class': 'form-control'}),
        }

class AcademicAnswerForm(forms.ModelForm):
    class Meta:
        model = AcademicAnswer
        fields = ['answer']
        widgets = {
            'answer': forms.Textarea(attrs={'rows': 4, 'cols': 40, 'class': 'form-control'}),
        }