import csv
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from .forms import StudentForm
from .models import Student, StudentBulkUpload, StudentTermAssignment
from apps.corecode.models import StudentClass, AcademicTerm, AcademicSession
from apps.finance.models import Invoice
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class StudentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Student
    template_name = "students/student_list.html"
    permission_required = 'students.view_student_list'
    permission_denied_message = 'Access Denied'
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        context['total_male'] = Student.objects.filter(gender='male', completed=False).count()
        context['total_female'] = Student.objects.filter(gender='female', completed=False).count()
        context['overall_total'] = Student.objects.filter(completed=False).count()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_session = AcademicSession.objects.filter(current=True).first()
        context['current_term'] = current_term
        context['current_session'] = current_session

        # Debug current term and session
        logger.debug(f"Current Term: {current_term.name if current_term else 'None'}")
        logger.debug(f"Current Session: {current_session.name if current_session else 'None'}")

        # Add term assignments for current term and session
        if current_term and current_session:
            term_assignments = StudentTermAssignment.objects.filter(
                academic_term=current_term,
                academic_session=current_session,
                student__in=context['students']
            ).select_related('student')
            # Debug term assignments
            for ta in term_assignments:
                logger.debug(f"Term Assignment: Student ID {ta.student.id}, Term {ta.academic_term.name}, Session {ta.academic_session.name}")
            # Map student IDs to a boolean indicating if they are assigned to the current term
            context['student_term_assignments'] = {
                student.id: any(ta.student.id == student.id for ta in term_assignments)
                for student in context['students']
            }
            logger.debug(f"Student Term Assignments: {context['student_term_assignments']}")
        else:
            context['student_term_assignments'] = {}
            logger.warning("No current term or session set; term assignments empty.")

        return context

class ActiveStudentListView(StudentListView):
    def get_queryset(self):
        return Student.objects.filter(current_status="active", completed=False)

class InactiveStudentsView(StudentListView):
    def get_queryset(self):
        return Student.objects.filter(current_status="inactive", completed=False)

class AssignStudentsToTermView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'students.change_student'
    permission_denied_message = 'Access Denied'
    template_name = 'students/assign_term.html'

    def get(self, request, *args, **kwargs):
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_session = AcademicSession.objects.filter(current=True).first()
        if not current_term or not current_session:
            messages.error(request, "No current academic term or session set.")
            return redirect('student-list')
        assigned_student_ids = StudentTermAssignment.objects.filter(
            academic_term=current_term,
            academic_session=current_session
        ).values_list('student_id', flat=True)
        students = Student.objects.filter(
            current_status='active',
            completed=False
        ).exclude(id__in=assigned_student_ids)
        context = {
            'students': students,
            'current_term': current_term,
            'current_session': current_session,
            'student_classes': StudentClass.objects.all(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        selected_student_ids = request.POST.getlist('students')
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_session = AcademicSession.objects.filter(current=True).first()
        if not current_term or not current_session:
            messages.error(request, "No current academic term or session set.")
            return redirect('student-list')
        if not selected_student_ids:
            messages.error(request, "No students selected.")
            return redirect('assign-term')
        for student_id in selected_student_ids:
            student = get_object_or_404(Student, id=student_id)
            StudentTermAssignment.objects.get_or_create(
                student=student,
                academic_term=current_term,
                academic_session=current_session,
                defaults={'assigned_date': timezone.now()}
            )
        messages.success(request, f"Assigned {len(selected_student_ids)} students to {current_term} ({current_session}).")
        return redirect('student-list')

class PromoteStudentsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'students.change_student'
    permission_denied_message = 'Access Denied'
    template_name = 'students/promote_students.html'

    def get(self, request, *args, **kwargs):
        # Group students by current class
        student_classes = StudentClass.objects.all()
        students_by_class = {}
        for student_class in student_classes:
            students = Student.objects.filter(
                current_class=student_class,
                current_status='active',
                completed=False
            )
            if students.exists():
                students_by_class[student_class.name] = students
        context = {
            'students_by_class': students_by_class,
            'student_classes': student_classes,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        selected_student_ids = request.POST.getlist('students')
        target_class_id = request.POST.get('target_class')
        current_session = AcademicSession.objects.filter(current=True).first()

        if not selected_student_ids:
            messages.error(request, "No students selected for promotion.")
            return redirect('promote-students')
        
        if not target_class_id:
            messages.error(request, "No target class selected.")
            return redirect('promote-students')

        try:
            target_class = StudentClass.objects.get(id=target_class_id)
        except StudentClass.DoesNotExist:
            messages.error(request, "Selected target class does not exist.")
            return redirect('promote-students')

        # Define highest class for alumni assignment
        highest_class = "Standard 7"

        for student_id in selected_student_ids:
            student = get_object_or_404(Student, id=student_id)
            current_class_name = student.current_class.name if student.current_class else "None"

            # Check if promoting to the highest class
            if target_class.name == highest_class:
                student.current_status = 'inactive'
                student.completed = True
                student.alumni_session = current_session
                student.current_class = None
                student.save()
                logger.info(f"Marked {student} as alumni for session {current_session.name}")
            else:
                student.current_class = target_class
                student.save()
                logger.info(f"Promoted {student} from {current_class_name} to {target_class.name}")

        messages.success(request, f"Promoted {len(selected_student_ids)} students to {target_class.name}.")
        return redirect('student-list')

class SelectAlluiClassView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'students.change_student'
    permission_denied_message = 'Access Denied'

    def get(self, request, *args, **kwargs):
        classes = StudentClass.objects.all().order_by('name')
        return render(request, 'students/select_allui_class.html', {'classes': classes})

    def post(self, request, *args, **kwargs):
        selected_class = request.POST.get('selected_class')
        current_session = AcademicSession.objects.filter(current=True).first()
        if selected_class:
            students = Student.objects.filter(current_class__name=selected_class)
            for student in students:
                student.current_status = "inactive"
                student.completed = True
                if selected_class == "Standard 7" and current_session:
                    student.alumni_session = current_session
                student.save()
            messages.success(request, f"All students in class {selected_class.upper()} have been marked as completed.")
        else:
            messages.error(request, "No class selected.")
        return redirect('completed-students')

class CompletedStudentsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Student
    template_name = "students/completed_student_list.html"
    permission_required = 'students.view_student_list'
    permission_denied_message = 'Access Denied'
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(
            Q(current_status="inactive", completed=True) |
            Q(current_status="active", completed=True)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        context['total_male'] = self.get_queryset().filter(gender='male').count()
        context['total_female'] = self.get_queryset().filter(gender='female').count()
        context['overall_total'] = self.get_queryset().count()
        return context

class AlumniListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Student
    template_name = "students/alumni_list.html"
    permission_required = 'students.view_student_list'
    permission_denied_message = 'Access Denied'
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(completed=True, alumni_session__isnull=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        students = self.get_queryset()
        alumni_by_year = {}
        for student in students:
            session_name = student.alumni_session.name if student.alumni_session else "Unknown"
            if session_name not in alumni_by_year:
                alumni_by_year[session_name] = []
            alumni_by_year[session_name].append(student)
        context['alumni_by_year'] = alumni_by_year
        context['total_alumni'] = students.count()
        context['total_male'] = students.filter(gender='male').count()
        context['total_female'] = students.filter(gender='female').count()
        return context

class CompletedStudentDetailView(DetailView):
    model = Student
    template_name = "students/completed_student_detail.html"
    context_object_name = "object"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = Invoice.objects.filter(student=self.object)
        try:
            from apps.result.models import Result, StudentInfos
            results = Result.objects.filter(student=self.object).order_by('session', 'term', 'exam')
            student_infos = StudentInfos.objects.filter(student=self.object).order_by('session', 'term', 'exam', '-id')
            grouped_data = {}
            for result in results:
                session = result.session.name
                term = result.term.name
                exam = result.exam.name
                if session not in grouped_data:
                    grouped_data[session] = {}
                if term not in grouped_data[session]:
                    grouped_data[session][term] = {}
                if exam not in grouped_data[session][term]:
                    grouped_data[session][term][exam] = {'results': [], 'infos': []}
                grouped_data[session][term][exam]['results'].append(result)
            for info in student_infos:
                session = info.session.name
                term = info.term.name
                exam = info.exam.name
                if session not in grouped_data:
                    grouped_data[session] = {}
                if term not in grouped_data[session]:
                    grouped_data[session][term] = {}
                if exam not in grouped_data[session][term]:
                    grouped_data[session][term][exam] = {'results': [], 'infos': []}
                if not grouped_data[session][term][exam]['infos']:
                    grouped_data[session][term][exam]['infos'].append(info)
            for session, terms in grouped_data.items():
                for term, exams in terms.items():
                    for exam, data in exams.items():
                        total = sum(result.average for result in data['results'])
                        subject_count = len(data['results'])
                        total_marks = subject_count * 50
                        student_average = total / subject_count if subject_count > 0 else 0
                        student_class = self.object.current_class
                        students_in_class = Result.objects.filter(
                            current_class=student_class,
                            session__name=session,
                            term__name=term,
                            exam__name=exam
                        ).values('student').distinct()
                        total_students = students_in_class.count()
                        all_averages = [
                            sum(Result.objects.filter(
                                student=student['student'],
                                session__name=session,
                                term__name=term,
                                exam__name=exam
                            ).values_list('average', flat=True))
                            for student in students_in_class
                        ]
                        all_averages.sort(reverse=True)
                        student_position = all_averages.index(total) + 1 if total in all_averages else None
                        data['total'] = total
                        data['total_marks'] = total_marks
                        data['student_average'] = student_average
                        data['student_position'] = student_position
                        data['total_students'] = total_students
            context['grouped_data'] = grouped_data
        except ImportError:
            context['grouped_data'] = {}
        return context

class StudentDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Student
    template_name = "students/student_detail.html"
    permission_required = 'students.view_student_detail'
    permission_denied_message = 'Access Denied'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_session = AcademicSession.objects.filter(current=True).first()
        context["payments"] = Invoice.objects.filter(student=self.object)
        context["term_assignments"] = StudentTermAssignment.objects.filter(
            student=self.object,
            academic_session=current_session
        ) if current_session else StudentTermAssignment.objects.none()
        return context

class HistoricalTermAssignmentsView(DetailView):
    model = Student
    template_name = "students/historical_term_assignments.html"
    permission_required = 'students.view_student_detail'
    permission_denied_message = 'Access Denied'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = self.request.GET.get('session_id')
        if session_id:
            try:
                session = AcademicSession.objects.get(id=session_id)
                context['term_assignments'] = StudentTermAssignment.objects.filter(
                    student=self.object,
                    academic_session=session
                )
                context['selected_session'] = session
            except AcademicSession.DoesNotExist:
                context['term_assignments'] = StudentTermAssignment.objects.none()
        else:
            context['term_assignments'] = StudentTermAssignment.objects.filter(student=self.object)
        context['academic_sessions'] = AcademicSession.objects.all().order_by('-name')
        return context

class StudentCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Student
    form_class = StudentForm
    success_message = "New student successfully added."
    permission_required = 'students.add_student'
    permission_denied_message = 'Access Denied'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student_classes"] = StudentClass.objects.all()
        return context

    def form_valid(self, form):
        self.log_debug_info("Form is valid", form.cleaned_data)
        return super().form_valid(form)

    def form_invalid(self, form):
        self.log_debug_info("Form is invalid", form.errors)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('student-list')

    def log_debug_info(self, message, data):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"DEBUG: {message}")
        logger.debug(f"DEBUG: Data = {data}")

class StudentUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Student
    form_class = StudentForm
    success_message = "Record successfully updated."
    permission_required = 'students.change_student'
    permission_denied_message = 'Access Denied'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student_classes"] = StudentClass.objects.all()
        return context

    def form_valid(self, form):
        self.log_debug_info("Form is valid", form.cleaned_data)
        return super().form_valid(form)

    def form_invalid(self, form):
        self.log_debug_info("Form is invalid", form.errors)
        return super().form_invalid(form)

    def log_debug_info(self, message, data):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"DEBUG: {message}")
        logger.debug(f"DEBUG: Data = {data}")

class StudentDeleteView(LoginRequiredMixin, DeleteView):
    model = Student
    success_url = reverse_lazy("student-list")
    permission_required = 'students.delete_student'

class StudentBulkUploadView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = StudentBulkUpload
    template_name = "students/students_upload.html"
    fields = ["csv_file"]
    success_url = reverse_lazy("student-list")
    success_message = "Successfully uploaded students"
    permission_required = 'students.add_student'

class DownloadCSVView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="student_template.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "registration_number",
                "surname",
                "firstname",
                "middle_name",
                "gender",
                "category",
                "guardian1_mobile_number",
                "guardian2_mobile_number",
                "has_nhif",
                "nhif_source",
                "nhif_number",
                "address",
                "current_class",
                "alumni_session",
            ]
        )
        return response