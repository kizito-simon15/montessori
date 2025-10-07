from django.utils import timezone
from django.views.generic import  ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import Event
from django.forms import DateInput
from apps.corecode.models import AcademicSession, AcademicTerm

class EventCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Event
    template_name = 'event/event_form.html'
    fields = ['title', 'description', 'date', 'participants', 'location']
    success_url = reverse_lazy('event_list')
    permission_required = 'event.add_event'  # Adjust with the appropriate permission codename
    permission_denied_message = "Access Denied"

    def form_valid(self, form):
        # Get current session and term
        current_session = AcademicSession.objects.get(current=True)
        current_term = AcademicTerm.objects.get(current=True)

        # Set session and term for the event
        form.instance.session = current_session
        form.instance.term = current_term

        # Save the event
        form.instance.save()

        messages.success(self.request, 'Event created successfully')  # Add success message
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['css_file'] = 'css/event_form.css'  # Provide the CSS file path to the template
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name in form.fields:
            form.fields[field_name].widget.attrs['class'] = 'form-control'
        form.fields['date'].widget = DateInput(attrs={'type': 'date', 'class': 'form-control'})
        return form

class EventListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Event
    template_name = 'event/event_list.html'
    context_object_name = 'events'
    permission_required = 'event.view_event'
    permission_denied_message = 'Access Denied'

    def get_queryset(self):
        # Get the current session and term
        current_session = AcademicSession.objects.get(current=True)
        current_term = AcademicTerm.objects.get(current=True)

        # Filter events based on the current session and term
        queryset = super().get_queryset().filter(session=current_session, term=current_term)

        # Modify the queryset to order events by the creation date
        queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for event in context['events']:
            event.time_since_creation = self.get_time_since_creation(event.created_at)
        return context

    def get_time_since_creation(self, created_at):
        time_since = timezone.now() - created_at
        seconds = abs(time_since.total_seconds())
        if seconds < 60:
            return f"{int(seconds)} seconds"
        minutes = seconds / 60
        if minutes < 60:
            return f"{int(minutes)} minutes"
        hours = minutes / 60
        if hours < 24:
            return f"{int(hours)} hours"
        days = hours / 24
        if days < 365:
            return f"{int(days)} days"
        return "Over a year ago"

class EventDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Event
    template_name = 'event/event_detail.html'
    context_object_name = 'event'
    permission_required = 'event.view_event'
    permission_denied_message = 'Access Denied'


class EventDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Event
    template_name = 'event/event_delete.html'
    success_url = reverse_lazy('event_list')
    permission_required = 'event.delete_event'
    permission_denied_message = 'Access Denied'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Event deleted successfully')  # Add success message
        return super().delete(request, *args, **kwargs)
    
# views.py
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import UpdateView
from .models import Event
from .forms import EventForm

class EventUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Event
    template_name = 'event/event_form.html'
    form_class = EventForm
    permission_required = 'event.change_event'
    permission_denied_message = 'Access Denied'

    def get_success_url(self):
        messages.success(self.request, 'Event updated successfully')
        return reverse_lazy('event_list')
