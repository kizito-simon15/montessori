from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from apps.students.models import Student, StudentTermAssignment
from apps.students.forms import StudentForm
from apps.corecode.models import StudentClass, AcademicSession, AcademicTerm
from apps.finance.models import Invoice
from apps.staffs.models import Staff
from sms.models import SentSMS
import logging

logger = logging.getLogger(__name__)

class HeadteacherDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "headteacher/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = {
            "Students": {"total": Student.objects.filter(current_status="active", completed=False).count()},
            "Staff": {"total": Staff.objects.filter(current_status="active").count()},
            "SMS": {"total": SentSMS.objects.count()},
        }
        return context

class HeadteacherStudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "headteacher/students/student_list.html"
    context_object_name = "students"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

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

        if current_term and current_session:
            term_assignments = StudentTermAssignment.objects.filter(
                academic_term=current_term,
                academic_session=current_session,
                student__in=context['students']
            ).select_related('student')
            context['student_term_assignments'] = {
                student.id: any(ta.student.id == student.id for ta in term_assignments)
                for student in context['students']
            }
            logger.debug(f"Student Term Assignments: {context['student_term_assignments']}")
        else:
            context['student_term_assignments'] = {}
            logger.warning("No current term or session set; term assignments empty.")

        return context

class HeadteacherStudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "headteacher/students/student_detail.html"
    context_object_name = "student"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_session = AcademicSession.objects.filter(current=True).first()
        context["payments"] = Invoice.objects.filter(student=self.object)
        context["term_assignments"] = StudentTermAssignment.objects.filter(
            student=self.object,
            academic_session=current_session
        ) if current_session else StudentTermAssignment.objects.none()
        return context

class HeadteacherStudentCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "headteacher/students/student_form.html"
    success_message = "New student successfully added."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student_classes"] = StudentClass.objects.all()
        return context

    def get_success_url(self):
        return reverse_lazy('headteacher_student_list')

class HeadteacherStudentUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "headteacher/students/student_form.html"
    success_message = "Student record successfully updated."

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["student_classes"] = StudentClass.objects.all()
        return context

    def get_success_url(self):
        return reverse_lazy('headteacher_student_list')

class HeadteacherStudentDeleteView(LoginRequiredMixin, DeleteView):
    model = Student
    template_name = "headteacher/students/student_confirm_delete.html"
    success_url = reverse_lazy("headteacher_student_list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

class HeadteacherAssignStudentsToTermView(LoginRequiredMixin, View):
    template_name = 'headteacher/students/assign_term.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_session = AcademicSession.objects.filter(current=True).first()
        if not current_term or not current_session:
            messages.error(request, "No current academic term or session set.")
            return redirect('headteacher_student_list')
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
            return redirect('headteacher_student_list')
        if not selected_student_ids:
            messages.error(request, "No students selected.")
            return redirect('headteacher_assign_term')
        for student_id in selected_student_ids:
            student = get_object_or_404(Student, id=student_id)
            StudentTermAssignment.objects.get_or_create(
                student=student,
                academic_term=current_term,
                academic_session=current_session,
                defaults={'assigned_date': timezone.now()}
            )
        messages.success(request, f"Assigned {len(selected_student_ids)} students to {current_term} ({current_session}).")
        return redirect('headteacher_student_list')
    

class HeadteacherHistoricalTermAssignmentsView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "headteacher/students/historical_term_assignments.html"
    context_object_name = 'student'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'headteacheruser'):
            raise PermissionDenied("Access Denied: Only headteachers are allowed.")
        return super().dispatch(request, *args, **kwargs)

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