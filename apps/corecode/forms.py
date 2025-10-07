from django import forms
from django.forms import ModelForm, modelformset_factory

from .models import (
    AcademicSession,
    AcademicTerm,
    ExamType,
    Installment,
    SiteConfig,
    StudentClass,
    Subject,
    Signature
)

SiteConfigForm = modelformset_factory(
    SiteConfig,
    fields=(
        "key",
        "value",
    ),
    extra=0,
)


class AcademicSessionForm(ModelForm):
    prefix = "Academic Session"

    class Meta:
        model = AcademicSession
        fields = ["name", "current"]


class AcademicTermForm(ModelForm):
    prefix = "Academic Term"

    class Meta:
        model = AcademicTerm
        fields = ["name", "current"]

class ExamTypeForm(ModelForm):
    prefix = "Exam Type"

    class Meta:
        model = ExamType
        fields = ["name", "current"]

class InstallmentForm(ModelForm):
    prefix = "Installment"

    class Meta:
        model = Installment
        fields = ["name", "current"]


class SubjectForm(ModelForm):
    prefix = "Subject"

    class Meta:
        model = Subject
        fields = ["name"]


class StudentClassForm(ModelForm):
    prefix = "Class"

    class Meta:
        model = StudentClass
        fields = ["name"]


class CurrentSessionForm(forms.Form):
    current_session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.all(),
        help_text='Click <a href="/session/create/?next=current-session/">here</a> to add new session',
    )
    current_term = forms.ModelChoiceField(
        queryset=AcademicTerm.objects.all(),
        help_text='Click <a href="/term/create/?next=current-session/">here</a> to add new term',
    )
    current_exam = forms.ModelChoiceField(
        queryset=ExamType.objects.all(),
        help_text='Click <a href="/exam/create/?next=current-session/">here</a> to add new exam',
    )

    current_install = forms.ModelChoiceField(
        queryset=Installment.objects.all(),
        help_text='Click <a href="/install/create/?next=current-session/">here</a> to add new installment',
    )

class SignatureForm(forms.ModelForm):
    class Meta:
        model = Signature
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Enter your name',
                'style': 'font-size: 1.2em; padding: 10px;'
            }),
        }