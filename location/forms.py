from django import forms
from .models import SchoolLocation, DAYS_OF_WEEK

class SchoolLocationForm(forms.ModelForm):
    start_day = forms.ChoiceField(
        choices=DAYS_OF_WEEK,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    end_day = forms.ChoiceField(
        choices=DAYS_OF_WEEK,
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M', attrs={'class': 'form-control form-control-lg', 'value': '07:00'})
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M', attrs={'class': 'form-control form-control-lg', 'value': '19:00'})
    )

    class Meta:
        model = SchoolLocation
        fields = ['name', 'latitude', 'longitude', 'start_day', 'end_day', 'start_time', 'end_time', 'distance']  # Include distance field
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': 'any'}),
            'distance': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': 'any'}),  # Widget for distance
        }

    def __init__(self, *args, **kwargs):
        super(SchoolLocationForm, self).__init__(*args, **kwargs)
        # Ensure that the form shows the initial values if they exist
        if self.instance and self.instance.pk:
            self.fields['start_time'].initial = self.instance.start_time.strftime('%H:%M')
            self.fields['end_time'].initial = self.instance.end_time.strftime('%H:%M')
        else:
            self.fields['start_time'].initial = '07:00'
            self.fields['end_time'].initial = '19:00'
