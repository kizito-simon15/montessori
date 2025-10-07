from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.forms import widgets
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .models import NonStaff

class NonStaffListView(ListView):
    model = NonStaff
    template_name = "non_staffs/non_staff_list.html"

class NonStaffDetailView(DetailView):
    model = NonStaff
    template_name = "non_staffs/non_staff_detail.html"



class NonStaffCreateView(SuccessMessageMixin, CreateView):
    model = NonStaff
    template_name = "non_staffs/non_staff_form.html"
    fields = ['current_status', 'firstname', 'other_name', 'surname', 'gender', 'date_of_birth', 'date_of_admission', 'mobile_number', 'address', 'others', 'salary']  # Include all fields except the user field
    success_message = "New non teaching staff successfully added"
    success_url = reverse_lazy('non-staff-list')  # Redirect URL after successful form submission

    def get_form(self):
        """Add date picker in forms"""
        form = super().get_form()
        form.fields["date_of_birth"].widget = widgets.DateInput(attrs={"type": "date"})
        form.fields["date_of_admission"].widget = widgets.DateInput(attrs={"type": "date"})
        form.fields["address"].widget = widgets.Textarea(attrs={"rows": 1})
        form.fields["others"].widget = widgets.Textarea(attrs={"rows": 1})
        return form

    def form_valid(self, form):
        """Override form_valid method to handle NonStaff creation"""
        non_staff = form.save(commit=False)  # Don't save the form yet
        
        # Perform any additional processing before saving the staff object
        
        non_staff.save()  # Save the staff object
        
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
        
class NonStaffUpdateView(SuccessMessageMixin, UpdateView):
    model = NonStaff
    fields = "__all__"
    success_message = "Record successfully updated."

    def get_form(self):
        """Add date picker in forms"""
        form = super().get_form()
        form.fields["date_of_birth"].widget = widgets.DateInput(attrs={"type": "date"})
        form.fields["date_of_admission"].widget = widgets.DateInput(attrs={"type": "date"})
        form.fields["address"].widget = widgets.Textarea(attrs={"rows": 1})
        form.fields["others"].widget = widgets.Textarea(attrs={"rows": 1})
        return form


class NonStaffDeleteView(DeleteView):
    model = NonStaff
    template_name = "non_staffs/non_staff_confirm_delete.html"
    success_url = reverse_lazy("non-staff-list")

