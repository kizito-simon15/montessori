from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import SecretaryUser
from accounts.models import TeacherUser
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from apps.finance.models import SalaryInvoice
from accounts.models import TeacherUser
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from accounts.models import TeacherUser
from django.db.models.functions import TruncMonth
from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, ExtractYear, ExtractMonth
from apps.finance.models import SalaryInvoice
from accounts.models import TeacherUser
from apps.corecode.models import StudentClass, Subject
from apps.result.models import Result
from collections import defaultdict
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, StudentClass, Subject
from apps.students.models import Student
from apps.result.models import Result
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import  ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from event.models import Event
from django.forms import DateInput
from apps.corecode.models import AcademicSession, AcademicTerm
import csv
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.forms import widgets
from django.http import HttpResponse
from django.urls import reverse_lazy
import csv
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from apps.students.models import Student, StudentBulkUpload
from apps.corecode.models import StudentClass
from apps.finance.models import Invoice
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.views.generic.edit import DeleteView
from apps.staffs.models import Staff
from apps.result.models import Result, StudentInfos
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.db import transaction
from sms.beem_service import send_sms, check_balance
from apps.students.models import Student
from apps.staffs.models import Staff
from sms.models import SentSMS    
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect, get_object_or_404
from school_properties.forms import PropertyForm, UpdatePropertyForm
from school_properties.models import Property
from apps.corecode.models import AcademicSession
from django.contrib import messages
from accounts.forms import ProfilePictureForm
from parents.models import StudentComments
from library.models import Stationery
from library.forms import StationeryForm
from itertools import groupby
from operator import attrgetter
from datetime import datetime
from .forms import SecretaryAnswerForm
from .models import SecretaryAnswers
from django.urls import reverse

from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
#from parents.models import StudentComments
from apps.staffs.models import StaffAttendance

from django.utils import timezone
from apps.staffs.models import StaffAttendance

def staff_sign_in(user):
    # Get the current date in the user's timezone
    today = timezone.localtime().date()

    # Set the start and end of the day based on the timezone
    start_of_day = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()), timezone.get_current_timezone())
    end_of_day = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()), timezone.get_current_timezone())

    # Check if there's already an attendance record for today
    attendance, created = StaffAttendance.objects.get_or_create(
        user=user,
        date=today  # Use date to ensure it checks by day and not time
    )
    
    # If the attendance was just created or the user wasn't marked present yet, update it
    if created or not attendance.is_present:
        attendance.is_present = True
        attendance.time_of_arrival = timezone.localtime()  # Use localtime to ensure it's in the correct timezone
        attendance.save()
    
    return attendance

from django.utils import timezone
from apps.staffs.models import StaffAttendance
"""
def should_show_sign_in_button(user):
    
    This function checks if the sign-in button should be shown.
    The button is shown if the current time is after 4:00 AM
    and the user has not signed in for the current day.
    
    current_time = timezone.localtime().time()  # Use localtime to ensure it's in the correct timezone
    sign_in_time_limit = timezone.datetime.strptime("04:00", "%H:%M").time()

    # Get today's attendance record based on the correct date and time
    today = timezone.localtime().date()
    attendance = StaffAttendance.objects.filter(user=user, date=today).first()

    # Show the sign-in button if the user hasn't signed in today and it's after 4:00 AM
    return not attendance or not attendance.is_present and current_time >= sign_in_time_limit
"""

from django.utils import timezone
from apps.staffs.models import StaffAttendance

def should_show_sign_in_button(user):
    """
    This function checks if the sign-in button should be shown.
    The button is shown if the current date has started 
    and the user has not signed in for the current day.
    """
    today = timezone.localtime().date()

    # Get today's attendance record based on the correct date
    attendance = StaffAttendance.objects.filter(user=user, date=today).first()

    # Show the sign-in button if it's a new day and the user hasn't signed in yet
    return not attendance or not attendance.is_present

@login_required
def secretary_dashboard(request):
    # Fetch the new comments (not marked as reviewed)
    new_comments = StudentComments.objects.filter(mark_student_comment=False)

    # Count of new comments
    new_comments_count = new_comments.count()

    # Get the full names of students with new comments
    student_names = new_comments.values_list(
        'student__firstname',
        'student__middle_name',
        'student__surname'
    )

    # Format the student names as a list of full names
    formatted_names = [f"{first} {middle} {last}" for first, middle, last in student_names]

    secretary_user = request.user.secretaryuser
    staff_name = f"{secretary_user.staff.firstname} {secretary_user.staff.middle_name} {secretary_user.staff.surname}"

    # Determine whether to show the sign-in button
    show_sign_in_button = should_show_sign_in_button(request.user)

    context = {
        'staff_name': staff_name,
        'new_comments_count': new_comments_count,
        'student_names': formatted_names,  # Pass the formatted names to the template
        'show_sign_in_button': show_sign_in_button,  # Pass this to the template
    }
    return render(request, 'secretary/secretary_dashboard.html', context)

@login_required
def mark_secretary_attendance(request):
    # Mark the attendance for the Secretary
    staff_sign_in(request.user)
    messages.success(request, "Attendance marked successfully.")
    return redirect('secretary_dashboard')


@login_required
def secretary_profile(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('secretary_dashboard')  # Replace 'academic_dashboard' with your actual dashboard URL name
    else:
        form = ProfilePictureForm(instance=request.user)
    return render(request, 'secretary/secretary_profile.html', {'form': form})


@login_required
def secretary_logout(request):
    logout(request)
    return redirect('login')

@login_required
def secretary_details(request):
    secretary_user = get_object_or_404(SecretaryUser, id=request.user.id)
    staff = secretary_user.staff

    context = {
        'object': staff
    }

    return render(request, 'secretary/secretary_details.html', context)

@login_required
def secretary_salary_invoices(request):
    secretary_user = get_object_or_404(SecretaryUser, id=request.user.id)
    staff = secretary_user.staff

    # Retrieve all salary invoices for the given staff
    invoices = SalaryInvoice.objects.filter(staff=staff).order_by('month')

    # Organize invoices by month and year
    invoices_by_month_year = invoices.annotate(month_year=TruncMonth('month')).values('month_year').annotate(
        total_gross_salary=Sum('gross_salary'),
        total_deductions=Sum('deductions'),
        total_net_salary=Sum('net_salary'),
        count=Count('id')
    ).order_by('-month_year')

    # Get unique years for the filter dropdown
    invoice_years = invoices.annotate(year=ExtractYear('month')).values_list('year', flat=True).distinct().order_by('year')

    context = {
        'invoices': invoices,
        'invoices_by_month_year': invoices_by_month_year,
        'invoice_years': invoice_years,
        'teacher_name': f"{staff.firstname} {staff.middle_name} {staff.surname}",
    }

    return render(request, 'secretary/secretary_salary_invoices.html', context)

@login_required
def secretary_class_list(request):
    classes = StudentClass.objects.all()
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        return redirect('secretary_class_results', class_id=class_id)
    
    context = {
        'classes': classes
    }
    return render(request, 'secretary/secretary_class_list.html', context)

@login_required
def secretary_class_results(request, class_id):
    selected_class = get_object_or_404(StudentClass, id=class_id)
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    exams = ExamType.objects.all()
    subjects = Subject.objects.all()

    # Get the current session, term, and exam
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()

    data = []

    for session in sessions:
        for term in terms:
            for exam in exams:
                # Retrieve results for the given class, session, term, and exam
                results = Result.objects.filter(
                    current_class=selected_class,
                    session=session,
                    term=term,
                    exam=exam
                ).select_related('student', 'subject')

                if results.exists():
                    session_term_exam_data = {
                        'session': session,
                        'term': term,
                        'exam': exam,
                        'results': [],
                        'subject_data': []
                    }

                    # Retrieve students who have results in this session, term, and exam
                    students = Student.objects.filter(
                        result__current_class=selected_class,
                        result__session=session,
                        result__term=term,
                        result__exam=exam
                    ).distinct()

                    for student in students:
                        student_results = results.filter(student=student)

                        if student_results.exists():
                            student_data = {
                                'student': student,
                                'student_class': selected_class,
                                'subjects': {},
                                'total': Decimal(0),
                                'overall_average': Decimal(0),
                                'overall_status': 'FAIL',
                                'position': None  # Position will be calculated later
                            }

                            total_score = Decimal(0)
                            total_subjects = 0

                            for subject in subjects:
                                subject_result = student_results.filter(subject=subject).first()
                                if subject_result:
                                    student_data['subjects'][subject] = {
                                        'test_score': subject_result.test_score,
                                        'exam_score': subject_result.exam_score,
                                        'average': subject_result.average
                                    }
                                    total_score += subject_result.average if subject_result.average else Decimal(0)
                                    total_subjects += 1
                                else:
                                    student_data['subjects'][subject] = {
                                        'test_score': None,
                                        'exam_score': None,
                                        'average': None
                                    }

                            if total_subjects > 0:
                                student_data['total'] = total_score
                                student_data['overall_average'] = total_score / total_subjects
                                student_data['overall_status'] = 'PASS' if student_data['overall_average'] >= Decimal(25) else 'FAIL'

                            session_term_exam_data['results'].append(student_data)

                    # Sort the results by overall average in descending order
                    session_term_exam_data['results'].sort(key=lambda x: x['overall_average'], reverse=True)

                    # Calculate positions with tie handling
                    current_position = 1
                    i = 0

                    while i < len(session_term_exam_data['results']):
                        tie_group = [session_term_exam_data['results'][i]]
                        j = i + 1

                        while j < len(session_term_exam_data['results']) and session_term_exam_data['results'][j]['overall_average'] == session_term_exam_data['results'][i]['overall_average']:
                            tie_group.append(session_term_exam_data['results'][j])
                            j += 1

                        # Calculate average position for the tie group
                        if len(tie_group) > 1:
                            average_position = current_position + 0.5
                            for result in tie_group:
                                result['position'] = average_position
                        else:
                            tie_group[0]['position'] = current_position

                        # Move to the next group
                        current_position += len(tie_group)
                        i = j

                    # Calculate subject data
                    for subject in subjects:
                        subject_results = results.filter(subject=subject)
                        if subject_results.exists():
                            total_subject_average = sum(result.average for result in subject_results)
                            total_students = subject_results.count()
                            subject_average = total_subject_average / total_students

                            if subject_average >= Decimal(41):
                                subject_grade = 'A'
                            elif subject_average >= Decimal(30):
                                subject_grade = 'B'
                            elif subject_average >= Decimal(25):
                                subject_grade = 'C'
                            elif subject_average >= Decimal(15):
                                subject_grade = 'D'
                            else:
                                subject_grade = 'F'

                            subject_gpa = (subject_average / Decimal(50)) * Decimal(4.0)

                            session_term_exam_data['subject_data'].append({
                                'subject': subject,
                                'average': subject_average,
                                'grade': subject_grade,
                                'gpa': round(subject_gpa, 3)  # Round to 3 decimal places
                            })

                    # Sort the subjects by average in descending order
                    session_term_exam_data['subject_data'].sort(key=lambda x: x['average'], reverse=True)

                    data.append(session_term_exam_data)

    context = {
        'selected_class': selected_class,
        'data': data,
        'subjects': subjects,
        'sessions': sessions,
        'terms': terms,
        'exams': exams,
        'current_session': current_session,
        'current_term': current_term,
        'current_exam': current_exam,
    }
    return render(request, 'secretary/secretary_class_results.html', context)

@login_required
def secretary_all_class_list(request):
    classes = StudentClass.objects.all()
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        return redirect('secretary_all_class_results', class_id=class_id)
    
    context = {
        'classes': classes
    }
    return render(request, 'secretary/all_class_list.html', context)


@login_required
def secretary_all_class_results(request, class_id):
    selected_class = get_object_or_404(StudentClass, id=class_id)
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    exams = ExamType.objects.all()
    subjects = Subject.objects.all()

    # Get the current session, term, and exam
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()

    data = []

    for session in sessions:
        for term in terms:
            for exam in exams:
                # Retrieve results for the given class, session, term, and exam
                results = Result.objects.filter(
                    current_class=selected_class,
                    session=session,
                    term=term,
                    exam=exam
                ).select_related('student', 'subject')

                if results.exists():
                    session_term_exam_data = {
                        'session': session,
                        'term': term,
                        'exam': exam,
                        'results': [],
                        'subject_data': []
                    }

                    # Retrieve students who have results in this session, term, and exam
                    students = Student.objects.filter(
                        result__current_class=selected_class,
                        result__session=session,
                        result__term=term,
                        result__exam=exam
                    ).distinct()

                    for student in students:
                        student_results = results.filter(student=student)

                        if student_results.exists():
                            student_data = {
                                'student': student,
                                'student_class': selected_class,
                                'subjects': {},
                                'total': Decimal(0),
                                'overall_average': Decimal(0),
                                'overall_status': 'FAIL',
                                'position': None  # Position will be calculated later
                            }

                            total_score = Decimal(0)
                            total_subjects = 0

                            for subject in subjects:
                                subject_result = student_results.filter(subject=subject).first()
                                if subject_result:
                                    student_data['subjects'][subject] = {
                                        'test_score': subject_result.test_score,
                                        'exam_score': subject_result.exam_score,
                                        'average': subject_result.average
                                    }
                                    total_score += subject_result.average if subject_result.average else Decimal(0)
                                    total_subjects += 1
                                else:
                                    student_data['subjects'][subject] = {
                                        'test_score': None,
                                        'exam_score': None,
                                        'average': None
                                    }

                            if total_subjects > 0:
                                student_data['total'] = total_score
                                student_data['overall_average'] = total_score / total_subjects
                                student_data['overall_status'] = 'PASS' if student_data['overall_average'] >= Decimal(25) else 'FAIL'

                            session_term_exam_data['results'].append(student_data)

                    # Sort the results by overall average in descending order
                    session_term_exam_data['results'].sort(key=lambda x: x['overall_average'], reverse=True)

                    # Calculate positions with tie handling
                    current_position = 1
                    i = 0

                    while i < len(session_term_exam_data['results']):
                        tie_group = [session_term_exam_data['results'][i]]
                        j = i + 1

                        while j < len(session_term_exam_data['results']) and session_term_exam_data['results'][j]['overall_average'] == session_term_exam_data['results'][i]['overall_average']:
                            tie_group.append(session_term_exam_data['results'][j])
                            j += 1

                        # Calculate average position for the tie group
                        if len(tie_group) > 1:
                            average_position = current_position + 0.5
                            for result in tie_group:
                                result['position'] = average_position
                        else:
                            tie_group[0]['position'] = current_position

                        # Move to the next group
                        current_position += len(tie_group)
                        i = j

                    # Calculate subject data
                    for subject in subjects:
                        subject_results = results.filter(subject=subject)
                        if subject_results.exists():
                            total_subject_average = sum(result.average for result in subject_results)
                            total_students = subject_results.count()
                            subject_average = total_subject_average / total_students

                            if subject_average >= Decimal(41):
                                subject_grade = 'A'
                            elif subject_average >= Decimal(30):
                                subject_grade = 'B'
                            elif subject_average >= Decimal(25):
                                subject_grade = 'C'
                            elif subject_average >= Decimal(15):
                                subject_grade = 'D'
                            else:
                                subject_grade = 'F'

                            subject_gpa = (subject_average / Decimal(50)) * Decimal(4.0)

                            session_term_exam_data['subject_data'].append({
                                'subject': subject,
                                'average': subject_average,
                                'grade': subject_grade,
                                'gpa': round(subject_gpa, 3)  # Round to 3 decimal places
                            })

                    # Sort the subjects by average in descending order
                    session_term_exam_data['subject_data'].sort(key=lambda x: x['average'], reverse=True)

                    data.append(session_term_exam_data)

    context = {
        'selected_class': selected_class,
        'data': data,
        'subjects': subjects,
        'sessions': sessions,
        'terms': terms,
        'exams': exams,
        'current_session': current_session,
        'current_term': current_term,
        'current_exam': current_exam,
    }
    return render(request, 'secretary/all_class_results.html', context)

class SecretaryEventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    template_name = 'secretary/secretary_event_form.html'
    fields = ['title', 'description', 'date', 'participants', 'location']
    success_url = reverse_lazy('secretary_event_list')

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
        context['css_file'] = 'css/secretary_event_form.css'  # Provide the CSS file path to the template
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name in form.fields:
            form.fields[field_name].widget.attrs['class'] = 'form-control'
        form.fields['date'].widget = DateInput(attrs={'type': 'date', 'class': 'form-control'})
        return form

class SecretaryEventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'secretary/secretary_event_list.html'
    context_object_name = 'events'

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

class SecretaryEventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'secretary/secretary_event_detail.html'
    context_object_name = 'event'

class SecretaryEventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    template_name = 'secretary/secretary_event_form.html'
    fields = ['title', 'description', 'date', 'participants', 'location']

    def get_success_url(self):
        messages.success(self.request, 'Event updated successfully')  # Add success message
        return reverse_lazy('secretary_event_list')


class SecretaryEventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = 'secretary/secretary_event_delete.html'
    success_url = reverse_lazy('secretary_event_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Event deleted successfully')  # Add success message
        return super().delete(request, *args, **kwargs)
    

class SecretaryStudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "secretary/secretary_student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(current_status="active", completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        return context

class SecretaryInactiveStudentsView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "secretary/secretary_inactive_student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(current_status="inactive", completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        context['staff_list'] = Staff.objects.filter(current_status="inactive")
        return context

class SecretarySelectAlluiClassView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        classes = StudentClass.objects.all().order_by('name')
        return render(request, 'secretary/secretary_select_allui_class.html', {'classes': classes})

    def post(self, request, *args, **kwargs):
        selected_class = request.POST.get('selected_class')
        if selected_class:
            Student.objects.filter(current_class__name=selected_class).update(current_status="inactive", completed=True)
            messages.success(request, f"All students in class {selected_class.upper()} have been marked as completed.")
        else:
            messages.error(request, "No class selected.")
        return redirect('secretary-completed-students')

from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

class SecretaryCompletedStudentsView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "secretary/secretary_completed_student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        # Filter students who are inactive and completed or active and completed
        return Student.objects.filter(completed=True).filter(
            Q(current_status="inactive") | Q(current_status="active")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add student classes to the context for filtering options
        context['student_classes'] = StudentClass.objects.all()
        return context

class SecretaryCompletedStudentDetailView(DetailView):
    model = Student
    template_name = "secretary/secretary_completed_student_detail.html"
    context_object_name = "object"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = Invoice.objects.filter(student=self.object)

        # Group results and student infos by session, term, and exam type
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
            # Only add the latest info for each session, term, and exam
            if not grouped_data[session][term][exam]['infos']:
                grouped_data[session][term][exam]['infos'].append(info)

        # Calculate totals and averages
        for session, terms in grouped_data.items():
            for term, exams in terms.items():
                for exam, data in exams.items():
                    total = sum(result.average for result in data['results'])
                    subject_count = len(data['results'])
                    total_marks = subject_count * 50
                    student_average = total / subject_count if subject_count > 0 else 0
                    
                    # Calculate position
                    student_class = self.object.current_class
                    students_in_class = Result.objects.filter(current_class=student_class, session__name=session, term__name=term, exam__name=exam).values('student').distinct()
                    total_students = students_in_class.count()
                    
                    all_averages = [sum(Result.objects.filter(student=student['student'], session__name=session, term__name=term, exam__name=exam).values_list('average', flat=True)) for student in students_in_class]
                    all_averages.sort(reverse=True)
                    student_position = all_averages.index(total) + 1 if total in all_averages else None

                    data['total'] = total
                    data['total_marks'] = total_marks
                    data['student_average'] = student_average
                    data['student_position'] = student_position
                    data['total_students'] = total_students

        context['grouped_data'] = grouped_data
        return context

class SecretaryStudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = "students/student_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payments"] = Invoice.objects.filter(student=self.object)
        return context

class SecretaryStudentCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Student
    fields = "__all__"
    template_name = "secretary/secretary_student_form.html"
    success_message = "New student successfully added."

    def get_form(self):
        form = super(SecretaryStudentCreateView, self).get_form()
        form.fields["date_of_birth"].widget = widgets.DateInput(attrs={"type": "date"})
        form.fields["address"].widget = widgets.Textarea(attrs={"rows": 2})
        form.fields["others"].widget = widgets.Textarea(attrs={"rows": 2})
        return form

    def get_success_url(self):
        return reverse_lazy('secretary-student-list')

class SecretaryStudentUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Student
    fields = "__all__"
    template_name = "secretary/secretary_student_update.html"
    success_message = "Record successfully updated."

    def get_form(self):
        form = super(SecretaryStudentUpdateView, self).get_form()
        form.fields["date_of_birth"].widget = widgets.DateInput(attrs={"type": "date"})
        form.fields["date_of_admission"].widget = widgets.DateInput(
            attrs={"type": "date"}
        )
        form.fields["address"].widget = widgets.Textarea(attrs={"rows": 2})
        form.fields["others"].widget = widgets.Textarea(attrs={"rows": 2})
        return form


class SecretaryStudentDeleteView(LoginRequiredMixin, DeleteView):
    model = Student
    success_url = reverse_lazy("secretary-student-list")

class SecretaryStudentBulkUploadView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = StudentBulkUpload
    template_name = "secretary/secretary_students_upload.html"
    fields = ["csv_file"]
    success_url = reverse_lazy("secretary-student-list")
    success_message = "Successfully uploaded students"

class SecretaryDownloadCSVViewdownloadcsv(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="secretary_student_template.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "registration_number",
                "surname",
                "firstname",
                "middle_name",
                "gender",
                "parent_number",
                "address",
                "current_class",
            ]
        )

        return response
    
class SecretaryStaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'secretary/staff_list.html'
    context_object_name = 'staff_list'

    def get_queryset(self):
        return Staff.objects.filter(current_status='active')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_male'] = Staff.objects.filter(gender='male').count()
        context['total_female'] = Staff.objects.filter(gender='female').count()
        context['overall_total'] = Staff.objects.count()
        return context

class SecretarySendSMSFormView(LoginRequiredMixin, View):

    def get(self, request):
        students = Student.objects.filter(current_status="active", completed=False)
        staff = Staff.objects.filter(current_status="active")
        classes = StudentClass.objects.all()  # Fetch all classes
        return render(request, 'secretary/send_sms.html', {
            'students': students,
            'staff': staff,
            'classes': classes
        })

    def post(self, request):
        message = request.POST.get('message')
        recipient_type = request.POST.get('recipient_type')
        recipients = []

        if recipient_type == 'students':
            student_recipients = request.POST.getlist('student_recipients')
            for student_id in student_recipients:
                student = Student.objects.get(id=student_id)
                if student.father_mobile_number:
                    recipients.append({
                        "dest_addr": student.father_mobile_number,
                        "first_name": student.firstname,
                        "last_name": student.surname
                    })
                if student.mother_mobile_number:
                    recipients.append({
                        "dest_addr": student.mother_mobile_number,
                        "first_name": student.firstname,
                        "last_name": student.surname
                    })
        elif recipient_type == 'staff':
            staff_recipients = request.POST.getlist('staff_recipients')
            recipients = [
                {
                    "dest_addr": staff_member.mobile_number,
                    "first_name": staff_member.firstname,
                    "last_name": staff_member.surname
                } for staff_member in Staff.objects.filter(mobile_number__in=staff_recipients)
            ]

        if not recipients:
            messages.error(request, 'No recipients selected.')
            # Ensure only active and non-completed students and active staff are reloaded in the form
            return render(request, 'secretary/send_sms.html', {
                'students': Student.objects.filter(current_status="active", completed=False),
                'staff': Staff.objects.filter(current_status="active"),
                'classes': StudentClass.objects.all()
            })

        try:
            response = send_sms(message, recipients)
            if response.get('error'):
                messages.error(request, 'Failed to send SMS: ' + response['error'])
            else:
                messages.success(request, 'SMS sent successfully!')
            return redirect('secretary_send_sms_form')
        except Exception as e:
            messages.error(request, f'An error occurred: {e}')
            return redirect('secretary_send_sms_form')
        
class SecretarySMSHistoryView(LoginRequiredMixin, View):

    def get(self, request):
        # Filter to get only sent messages
        messages_query = SentSMS.objects.filter(status='Sent').order_by('-sent_date')

        # Use a set to track unique messages and filter out duplicates
        seen = set()
        unique_messages = []
        for message in messages_query:
            identifier = (
                message.status,
                message.sent_date,
                message.first_name,
                message.last_name,
                message.dest_addr,
                message.message
            )
            if identifier not in seen:
                seen.add(identifier)
                unique_messages.append(message)

        total_sms = len(unique_messages)

        context = {
            'messages': unique_messages,
            'total_sms': total_sms
        }
        return render(request, 'secretary/sms_history.html', context)

    def post(self, request):
        sms_ids = request.POST.getlist('sms_ids')
        if sms_ids:
            with transaction.atomic():
                deleted_count, _ = SentSMS.objects.filter(id__in=sms_ids).delete()
                messages.success(request, f'Successfully deleted {deleted_count} messages.')
        else:
            messages.error(request, 'No messages selected for deletion.')
        return redirect('secretary_sms_history')

class SecretaryCheckBalanceView(View):
    def get(self, request):
        try:
            response = check_balance()
            if "error" in response:
                return render(request, 'secretary/check_balance.html', {'error': response['error']})
            return render(request, 'secretary/check_balance.html', {'balance': response.get('data', {}).get('credit_balance', 'N/A')})
        except Exception as e:
            return render(request, 'secretary/check_balance.html', {'error': str(e)})

@method_decorator(require_POST, name='dispatch')
class SecretaryDeleteSMSView(View):
    def post(self, request):
        sms_ids = request.POST.getlist('sms_ids')
        if sms_ids:
            with transaction.atomic():
                deleted_count, _ = SentSMS.objects.filter(id__in=sms_ids).delete()
                messages.success(request, f'Successfully deleted {deleted_count} messages.')
        else:
            messages.error(request, 'No messages selected for deletion.')
        return redirect('secretary_sms_history')

@login_required
def secretary_property_list(request):
    current_session = AcademicSession.objects.filter(current=True).first()
    properties = Property.objects.filter(session=current_session)
    return render(request, 'secretary/property_list.html', {'properties': properties})



@login_required
def secretary_add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            # Set the session for the property
            current_session = AcademicSession.objects.filter(current=True).first()
            if current_session:
                form.instance.session = current_session
                form.save()
                # Add a success message
                messages.success(request, 'Property added successfully!')
                return redirect('secretary_property_list')
            else:
                form.add_error(None, "No active session found.")
        else:
            print(form.errors)  # Log form errors for debugging
    else:
        form = PropertyForm()
    return render(request, 'secretary/add_property.html', {'form': form})

@login_required
def secretary_property_detail(request, pk):
    property = get_object_or_404(Property, pk=pk)
    return render(request, 'secretary/property_details.html', {'property': property})

@login_required
def secretary_update_property(request, pk):
    property = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        form = UpdatePropertyForm(request.POST, instance=property)
        if form.is_valid():
            form.save()
            return redirect('secretary_property_list')
    else:
        form = UpdatePropertyForm(instance=property)
    return render(request, 'secretary/update_property.html', {'form': form})


@login_required
def secretary_delete_property(request, pk):
    property = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        property.delete()
        return redirect('secretary_property_list')
    return render(request, 'secretary_delete_property.html', {'property': property})

"""
class StudentCommentsListView(LoginRequiredMixin, ListView):
    model = StudentComments
    template_name = 'secretary/student_comments_list.html'
    context_object_name = 'student_comments'

    def get_queryset(self):
        student_comments = StudentComments.objects.select_related('student', 'parent')

        # Annotate each comment with its corresponding Secretary answer if it exists
        for comment in student_comments:
            secretary_answer = SecretaryAnswers.objects.filter(
                student=comment.student,
                parent=comment.parent,
                comment=comment
            ).first()
            comment.secretary_answer = secretary_answer

        return student_comments

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secretary_answer_form'] = SecretaryAnswerForm()
        return context

    def post(self, request, *args, **kwargs):
        form = SecretaryAnswerForm(request.POST)
        if form.is_valid():
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(StudentComments, id=comment_id)
            answer_text = form.cleaned_data['answer']

            try:
                with transaction.atomic():
                    secretary_answer, created = SecretaryAnswers.objects.get_or_create(
                        student=comment.student,
                        parent=comment.parent,
                        comment=comment,
                        defaults={'answer': answer_text}
                    )

                    # Update the answer if it already exists
                    if not created:
                        secretary_answer.answer = answer_text
                        secretary_answer.save()

                    messages.success(request, "Answer saved successfully.")
            except Exception as e:
                messages.error(request, f"There was an error saving the answer: {str(e)}")
        else:
            messages.error(request, "Invalid form submission.")

        return redirect(reverse('student_comments'))
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

from .models import StudentComments, SecretaryAnswers
from .forms import SecretaryAnswerForm

class StudentCommentsListView(LoginRequiredMixin, ListView):
    model = StudentComments
    template_name = 'secretary/student_comments_list.html'
    context_object_name = 'student_comments'

    def get_queryset(self):
        student_comments = StudentComments.objects.select_related('student', 'parent')

        for comment in student_comments:
            secretary_answer = SecretaryAnswers.objects.filter(
                student=comment.student,
                parent=comment.parent,
                comment=comment
            ).first()
            comment.secretary_answer = secretary_answer

        return student_comments

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secretary_answer_form'] = SecretaryAnswerForm()
        return context

    def post(self, request, *args, **kwargs):
        form = SecretaryAnswerForm(request.POST, request.FILES)
        if form.is_valid():
            comment_id = request.POST.get('comment_id')
            comment = get_object_or_404(StudentComments, id=comment_id)

            try:
                with transaction.atomic():
                    secretary_answer, created = SecretaryAnswers.objects.get_or_create(
                        student=comment.student,
                        parent=comment.parent,
                        comment=comment,
                        defaults={
                            'answer': form.cleaned_data['answer'],
                            'audio_answer': request.FILES.get('audio_answer')
                        }
                    )

                    if not created:
                        # Update existing answer
                        secretary_answer.answer = form.cleaned_data['answer']
                        if 'audio_answer' in request.FILES:
                            secretary_answer.audio_answer = request.FILES['audio_answer']
                        secretary_answer.save()

                    messages.success(request, "Answer saved successfully.")
            except Exception as e:
                messages.error(request, f"There was an error saving the answer: {str(e)}")
        else:
            messages.error(request, "Invalid form submission.")
            print("Form errors:", form.errors)

        return redirect(reverse('student_comments'))

def mark_comment_as_read(request, comment_id):
    comment = get_object_or_404(StudentComments, id=comment_id)
    comment.mark_student_comment = True
    comment.save()
    messages.success(request, "Comment marked as read.")
    return redirect(reverse('student_comments'))

def save_secretary_answer(request):
    if request.method == "POST":
        comment_id = request.POST.get('comment_id')
        comment = get_object_or_404(StudentComments, id=comment_id)

        form = SecretaryAnswerForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                with transaction.atomic():
                    secretary_answer, created = SecretaryAnswers.objects.get_or_create(
                        comment=comment,
                        defaults={
                            'student': comment.student,
                            'parent': comment.parent,
                            'answer': form.cleaned_data['answer'],
                            'audio_answer': request.FILES.get('audio_answer')
                        }
                    )

                    # Update the answer if it already exists
                    if not created:
                        secretary_answer.answer = form.cleaned_data['answer']
                        if 'audio_answer' in request.FILES:
                            secretary_answer.audio_answer = request.FILES['audio_answer']
                        secretary_answer.save()

                    messages.success(request, "Secretary answer saved successfully.")
            except Exception as e:
                messages.error(request, f"There was an error saving the answer: {str(e)}")
        else:
            messages.error(request, "Invalid form submission.")
            print("Form errors:", form.errors)

        return redirect(reverse('student_comments'))

    return redirect(reverse('student_comments'))

class SecretaryAddStationeryView(View):
    def get(self, request):
        form = StationeryForm()
        return render(request, 'secretary/add_stationery.html', {'form': form})

    def post(self, request):
        form = StationeryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'New stationery added successfully')
            return redirect('secretary_add_stationery')
        return render(request, 'secretary/add_stationery.html', {'form': form})

class SecretaryStationeryListView(View, LoginRequiredMixin):

    def get(self, request):
        stationeries = Stationery.objects.all().order_by('-date_buyed')  # Order by date_buyed descending
        total_quantity = stationeries.aggregate(total_quantity=Sum('quantity'))['total_quantity']

        # Group stationeries by month and year, handling None date_buyed
        grouped_stationeries = {}
        for key, group in groupby(stationeries, key=lambda x: x.date_buyed.strftime('%Y-%m') if x.date_buyed else 'No Date'):
            if key != 'No Date':
                year_month = datetime.strptime(key, '%Y-%m')
            else:
                year_month = key
            grouped_stationeries[year_month] = list(group)

        # Sort grouped stationeries by month in descending order
        sorted_grouped_stationeries = dict(sorted(grouped_stationeries.items(), key=lambda x: (x[0] != 'No Date', x[0]), reverse=True))

        return render(request, 'secretary/stationery_list.html', {
            'grouped_stationeries': sorted_grouped_stationeries,
            'total_quantity': total_quantity
        })

class SecretaryStationeryDetailView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        return render(request, 'secretary/stationery_details.html', {'stationery': stationery})

class SecretaryStationeryUpdateView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        form = StationeryForm(instance=stationery)
        return render(request, 'secretary/stationery_update.html', {'form': form, 'stationery': stationery})

    def post(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        form = StationeryForm(request.POST, instance=stationery)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stationery updated successfully')
            return redirect('secretary_stationery_detail', stationery_id=stationery.id)
        return render(request, 'secretary/stationery_update.html', {'form': form, 'stationery': stationery})


class SecretaryStationeryDeleteView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        return render(request, 'secretary/stationery_delete.html', {'stationery': stationery})

    def post(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        stationery.delete()
        return redirect('secretary_stationery_list')


from accounts.models import ParentUser
from accounts.forms import ParentUserCreationForm

@login_required
def secretary_create_parent_user(request):
    if request.method == 'POST':
        form = ParentUserCreationForm(request.POST)
        if form.is_valid():
            parent_user = form.save()
            # Send SMS
            student = parent_user.student
            message = (
                f"Habari ndugu mzazi wa {student.firstname} {student.middle_name} {student.surname}, "
                f"pokea taarifa hizi za kukuwezesha kuingia kwenye mfumo wa shule, "
                f"username: {parent_user.username}, password: {request.POST.get('password1')}, "
                "usifute meseji hii kwa msaada piga 0744394080."
            )
            recipients = []

            # Add father's mobile number if it exists
            if student.father_mobile_number:
                recipients.append({
                    "dest_addr": student.father_mobile_number,
                    "first_name": parent_user.parent_first_name,
                    "last_name": parent_user.parent_last_name
                })

            # Add mother's mobile number if it exists
            if student.mother_mobile_number:
                recipients.append({
                    "dest_addr": student.mother_mobile_number,
                    "first_name": parent_user.parent_first_name,
                    "last_name": parent_user.parent_last_name
                })

            try:
                send_sms(message, recipients)
                messages.success(request, 'Parent user created successfully, and SMS has been sent.')
            except Exception as e:
                messages.error(request, f'Parent user created, but SMS sending failed: {e}')

            return redirect('secretary_parent_user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ParentUserCreationForm()
    return render(request, 'secretary/create_parent_user.html', {'form': form})

@login_required
def secretary_parent_user_list(request):
    parent_users = ParentUser.objects.all()
    return render(request, 'secretary/parent_user_list.html', {'parent_users': parent_users})

@login_required
def secretary_update_parent_user(request, pk):
    user = get_object_or_404(ParentUser, pk=pk)
    if request.method == 'POST':
        form = ParentUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parent user updated successfully.')
            return redirect('secretary_parent_user_list')
    else:
        form = ParentUserCreationForm(instance=user)
    return render(request, 'secretary/update_parent_user.html', {'form': form, 'user_type': 'Parent'})

@login_required
def secretary_delete_parent_user(request, pk):
    user = get_object_or_404(ParentUser, pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'Parent user deleted successfully.')
        return redirect('parent_user_list')
    return render(request, 'secretary/delete_parent_user.html', {'user': user})
