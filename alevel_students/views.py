import csv
import logging
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from .models import ALevelStudent, ALevelStudentBulkUpload
from .forms import ALevelStudentForm
from apps.corecode.models import StudentClass
from apps.finance.models import Invoice
from apps.result.models import Result, StudentInfos

# Set up logging
logger = logging.getLogger(__name__)

class ALevelStudentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ALevelStudent
    template_name = "students/alevel_student_list.html"  # Fixed template path
    permission_required = 'alevel_students.view_alevelstudent'
    context_object_name = "students"
    paginate_by = 10

    def get_queryset(self):
        """Fetch non-completed students, ordered by surname."""
        try:
            return ALevelStudent.objects.filter(completed=False).select_related('current_class').order_by('surname')
        except Exception as e:
            logger.error(f"Error fetching A-Level student list: {str(e)}")
            messages.error(self.request, _("Failed to load student list. Please try again."))
            return ALevelStudent.objects.none()

    def get_context_data(self, **kwargs):
        """Group students by class and add stats to context."""
        context = super().get_context_data(**kwargs)
        try:
            # Get the students from the queryset
            students = self.get_queryset()

            # Group students by class
            grouped_students = {}
            for student in students:
                class_name = student.current_class.name if student.current_class else "Unclassified"
                if class_name not in grouped_students:
                    grouped_students[class_name] = []
                grouped_students[class_name].append(student)

            # Add grouped students and stats to context
            context.update({
                'grouped_students': grouped_students,
                'student_classes': StudentClass.objects.all(),
                'total_male': students.filter(gender='male').count(),
                'total_female': students.filter(gender='female').count(),
                'overall_total': students.count(),
            })
        except Exception as e:
            logger.error(f"Error preparing context data: {str(e)}")
            messages.error(self.request, _("Failed to load additional data."))
            context['grouped_students'] = {}  # Ensure template doesn't break
        return context

class ActiveALevelStudentListView(ALevelStudentListView):
    def get_queryset(self):
        try:
            return ALevelStudent.objects.filter(current_status="active", completed=False).select_related('current_class').order_by('surname')
        except Exception as e:
            logger.error(f"Error fetching active A-Level student list: {str(e)}")
            messages.error(self.request, _("Failed to load active students."))
            return ALevelStudent.objects.none()

class InactiveALevelStudentsView(ALevelStudentListView):
    template_name = "students/inactive_student_list.html"  # Updated path

    def get_queryset(self):
        try:
            return ALevelStudent.objects.filter(current_status="inactive", completed=False).select_related('current_class').order_by('surname')
        except Exception as e:
            logger.error(f"Error fetching inactive A-Level student list: {str(e)}")
            messages.error(self.request, _("Failed to load inactive students."))
            return ALevelStudent.objects.none()

class SelectALevelClassView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'alevel_students.change_alevelstudent'
    template_name = 'alevel_students/select_allui_class.html'  # Updated path

    def get(self, request, *args, **kwargs):
        try:
            classes = StudentClass.objects.all().order_by('name')
            return render(request, self.template_name, {'classes': classes})
        except Exception as e:
            logger.error(f"Error rendering class selection page: {str(e)}")
            messages.error(request, _("Failed to load class selection page."))
            return redirect('alevel_students:alevel-student-list')

    def post(self, request, *args, **kwargs):
        selected_class = request.POST.get('selected_class')
        if not selected_class:
            logger.warning("No class selected in SelectALevelClassView.")
            messages.error(request, _("Please select a class."))
            return redirect('alevel_students:select-alevel-class')

        try:
            with transaction.atomic():
                updated_count = ALevelStudent.objects.filter(current_class__name=selected_class).update(
                    current_status="inactive", completed=True
                )
                logger.info(f"Marked {updated_count} students in class {selected_class} as completed.")
                messages.success(request, _(f"{updated_count} students in {selected_class.upper()} marked as completed."))
        except Exception as e:
            logger.error(f"Error updating students in class {selected_class}: {str(e)}")
            messages.error(request, _("Failed to mark students as completed."))
        return redirect('alevel_students:completed-alevel-students')

class CompletedALevelStudentsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ALevelStudent
    template_name = "students/completed_student_list.html"  # Updated path
    permission_required = 'alevel_students.view_alevelstudent'
    context_object_name = "students"
    paginate_by = 10

    def get_queryset(self):
        try:
            return ALevelStudent.objects.filter(completed=True).select_related('current_class').order_by('surname')
        except Exception as e:
            logger.error(f"Error fetching completed A-Level student list: {str(e)}")
            messages.error(self.request, _("Failed to load completed students."))
            return ALevelStudent.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['student_classes'] = StudentClass.objects.all()
        except Exception as e:
            logger.error(f"Error preparing context data: {str(e)}")
            messages.error(self.request, _("Failed to load class data."))
        return context

class CompletedALevelStudentDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = ALevelStudent
    template_name = "students/completed_student_detail.html"  # Updated path
    permission_required = 'alevel_students.view_alevelstudent'
    context_object_name = "student"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        try:
            # Fetch related data
            context['payments'] = Invoice.objects.filter(student=student).select_related('student')
            results = Result.objects.filter(student=student).select_related('session', 'term', 'exam').order_by('session', 'term', 'exam')
            student_infos = StudentInfos.objects.filter(student=student).select_related('session', 'term', 'exam').order_by('session', 'term', 'exam', '-id')

            # Group results and infos
            grouped_data = {}
            for result in results:
                key = (result.session.name, result.term.name, result.exam.name)
                if key not in grouped_data:
                    grouped_data[key] = {'results': [], 'infos': []}
                grouped_data[key]['results'].append(result)

            for info in student_infos:
                key = (info.session.name, info.term.name, info.exam.name)
                if key not in grouped_data:
                    grouped_data[key] = {'results': [], 'infos': []}
                grouped_data[key]['infos'].append(info)

            # Calculate aggregates
            for (session, term, exam), data in grouped_data.items():
                try:
                    total = sum(result.average for result in data['results'])
                    subject_count = len(data['results'])
                    total_marks = subject_count * 50
                    student_average = total / subject_count if subject_count > 0 else 0

                    students_in_class = Result.objects.filter(
                        current_class=student.current_class, session__name=session, term__name=term, exam__name=exam
                    ).values('student').distinct()
                    total_students = students_in_class.count()

                    all_averages = [
                        sum(Result.objects.filter(
                            student=s['student'], session__name=session, term__name=term, exam__name=exam
                        ).values_list('average', flat=True)) for s in students_in_class
                    ]
                    all_averages.sort(reverse=True)
                    student_position = all_averages.index(total) + 1 if total in all_averages else None

                    data.update({
                        'total': total,
                        'total_marks': total_marks,
                        'student_average': student_average,
                        'student_position': student_position,
                        'total_students': total_students,
                    })
                except Exception as e:
                    logger.error(f"Error calculating results for {session}/{term}/{exam}: {str(e)}")
                    data['error'] = _("Calculation error.")

            context['grouped_data'] = grouped_data
        except Exception as e:
            logger.error(f"Error preparing student detail context for {student.id}: {str(e)}")
            messages.error(self.request, _("Failed to load student details."))
        return context

class ALevelStudentDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = ALevelStudent
    template_name = "students/student_detail.html"  # Updated path
    permission_required = 'alevel_students.view_alevelstudent'
    context_object_name = "student"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["payments"] = Invoice.objects.filter(student=self.object).select_related('student')
        except Exception as e:
            logger.error(f"Error fetching payments for student {self.object.id}: {str(e)}")
            messages.error(self.request, _("Failed to load payment details."))
        return context

class ALevelStudentCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = ALevelStudent
    form_class = ALevelStudentForm
    template_name = "students/student_form.html"  # Updated path
    success_message = "New A-Level student added successfully."
    permission_required = 'alevel_students.add_alevelstudent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["student_classes"] = StudentClass.objects.all()
        except Exception as e:
            logger.error(f"Error fetching student classes: {str(e)}")
            messages.error(self.request, _("Failed to load class options."))
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                logger.debug("Form is valid", extra={'data': form.cleaned_data})
                return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error creating A-Level student: {str(e)}")
            messages.error(self.request, _("Failed to create student. Please try again."))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.debug("Form is invalid", extra={'errors': form.errors})
        messages.error(self.request, _("Please correct the form errors."))
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('alevel_students:alevel-student-list')

class ALevelStudentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ALevelStudent
    form_class = ALevelStudentForm
    template_name = "students/student_form.html"  # Updated path
    success_message = "A-Level student updated successfully."
    permission_required = 'alevel_students.change_alevelstudent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["student_classes"] = StudentClass.objects.all()
        except Exception as e:
            logger.error(f"Error fetching student classes: {str(e)}")
            messages.error(self.request, _("Failed to load class options."))
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                logger.debug("Form is valid", extra={'data': form.cleaned_data})
                return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error updating student {self.object.id}: {str(e)}")
            messages.error(self.request, _("Failed to update student."))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.debug("Form is invalid", extra={'errors': form.errors})
        messages.error(self.request, _("Please correct the form errors."))
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('alevel_students:alevel-student-list')

class ALevelStudentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ALevelStudent
    template_name = "students/student_confirm_delete.html"  # Updated path
    success_url = reverse_lazy("alevel_students:alevel-student-list")
    permission_required = 'alevel_students.delete_alevelstudent'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            logger.info(f"Deleting student: {self.object.registration_number}")
            messages.success(request, _(f"Student {self.object.registration_number} deleted successfully."))
            return super().post(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting student {self.object.id}: {str(e)}")
            messages.error(request, _("Failed to delete student."))
            return redirect('alevel_students:alevel-student-list')

class ALevelStudentBulkUploadView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = ALevelStudentBulkUpload
    template_name = "students/students_upload.html"  # Updated path
    fields = ["csv_file"]
    success_url = reverse_lazy("alevel_students:alevel-student-list")
    success_message = "A-Level students uploaded successfully."
    permission_required = 'alevel_students.add_alevelstudent'

    def form_valid(self, form):
        try:
            with transaction.atomic():
                instance = form.save()
                logger.info(f"Processing bulk upload: {instance.csv_file.name}")
                return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error processing bulk upload: {str(e)}")
            messages.error(self.request, _("Failed to process bulk upload."))
            return self.form_invalid(form)

class ALevelDownloadCSVView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'alevel_students.view_alevelstudent'  # Fixed permission

    def get(self, request, *args, **kwargs):
        try:
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="alevel_student_template.csv"'
            writer = csv.writer(response)
            writer.writerow([
                "registration_number", "surname", "firstname", "middle_name",
                "gender", "father_mobile_number", "mother_mobile_number",
                "address", "current_class",
            ])
            logger.info("Downloaded A-Level student CSV template.")
            return response
        except Exception as e:
            logger.error(f"Error generating CSV template: {str(e)}")
            messages.error(request, _("Failed to generate CSV template."))
            return redirect('alevel_students:alevel-student-list')