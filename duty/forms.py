# apps/staffs/forms.py

from django import forms
from .models import StaffRoles
from apps.staffs.models import Staff
from apps.corecode.models import StudentClass, Subject

class StaffRolesForm(forms.Form):
    staff = forms.ModelChoiceField(queryset=Staff.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    is_class_teacher = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    # Dynamic fields for multiple class-subject pairs
    classes_subjects = forms.CharField(widget=forms.HiddenInput(), required=False)  # Holds the dynamic fields data

    # Optional field to select the class if marked as Class Teacher
    class_teacher_class = forms.ModelChoiceField(queryset=StudentClass.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        is_class_teacher = cleaned_data.get('is_class_teacher')
        assigned_class = cleaned_data.get('assigned_class')
        staff = cleaned_data.get('staff')

        # Check if another staff is already set as a class teacher for the same class
        if is_class_teacher and StaffRoles.objects.filter(assigned_class=assigned_class, is_class_teacher=True).exclude(staff=staff).exists():
            self.add_error('is_class_teacher', f"There is already a class teacher assigned for {assigned_class}.")

        return cleaned_data


# apps/staffs/forms.py

from django import forms
from .models import StaffRoles
from apps.staffs.models import Staff
from apps.corecode.models import StudentClass, Subject

class StaffRolesForming(forms.ModelForm):
    class Meta:
        model = StaffRoles
        fields = ['staff', 'assigned_class', 'subject', 'is_class_teacher', 'on_duty']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'assigned_class': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'is_class_teacher': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'on_duty': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_class_teacher = cleaned_data.get('is_class_teacher')
        assigned_class = cleaned_data.get('assigned_class')
        staff = cleaned_data.get('staff')

        # Check if another staff is already set as a class teacher for the same class
        if is_class_teacher and StaffRoles.objects.filter(assigned_class=assigned_class, is_class_teacher=True).exclude(staff=staff).exists():
            self.add_error('is_class_teacher', f"There is already a class teacher assigned for {assigned_class}.")

        return cleaned_data

# apps/staffs/forms.py

from django import forms
from .models import StaffRoles
from apps.staffs.models import Staff
from apps.corecode.models import StudentClass

class UpdateClassTeacherForm(forms.ModelForm):
    class Meta:
        model = StaffRoles
        fields = ['staff', 'assigned_class', 'is_class_teacher']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'assigned_class': forms.Select(attrs={'class': 'form-control'}),
            'is_class_teacher': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_class_teacher = cleaned_data.get('is_class_teacher')
        assigned_class = cleaned_data.get('assigned_class')
        staff = cleaned_data.get('staff')

        # Check if another staff is already set as a class teacher for the same class
        if is_class_teacher and StaffRoles.objects.filter(assigned_class=assigned_class, is_class_teacher=True).exclude(staff=staff).exists():
            self.add_error('is_class_teacher', f"There is already a class teacher assigned for {assigned_class}.")

        return cleaned_data

from django import forms
from django.forms import inlineformset_factory
from .models import DailySchedule, ClassSchedule
from apps.corecode.models import StudentClass

class DailyScheduleForm(forms.ModelForm):
    class Meta:
        model = DailySchedule
        fields = ['day', 'start_time', 'end_time']
        widgets = {
            'day': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

class ClassScheduleForm(forms.ModelForm):
    class Meta:
        model = ClassSchedule
        fields = ['start_time', 'end_time', 'activity_type', 'subject', 'staff', 'description']
        widgets = {
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'activity_type': forms.Select(attrs={'class': 'form-control activity-select'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional description'}),
        }

# Inline formset for managing multiple ClassSchedule forms for each StudentClass
ClassScheduleFormSet = inlineformset_factory(
    DailySchedule,
    ClassSchedule,
    form=ClassScheduleForm,
    extra=1,  # Default to one extra blank form for each class
    can_delete=True  # Allows the user to delete schedule entries
)
