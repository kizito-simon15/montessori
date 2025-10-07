from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
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
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.staffs.models import Staff
from event.models import Event
from django.utils import timezone
from library.models import Book
from django.views import View
from django.views.generic import ListView
from accounts.forms import ProfilePictureForm
from apps.staffs.models import StaffAttendance
from django.contrib import messages

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
def teacher_dashboard(request):
    teacher_user = request.user.teacheruser
    staff_name = f"{teacher_user.staff.firstname} {teacher_user.staff.middle_name} {teacher_user.staff.surname}"

    # Determine whether to show the sign-in button
    show_sign_in_button = should_show_sign_in_button(request.user)

    context = {
        'staff_name': staff_name,
        'show_sign_in_button': show_sign_in_button,  # Pass this to the template
    }
    return render(request, 'teachers/teacher_dashboard.html', context)

@login_required
def mark_teacher_attendance(request):
    # Mark the attendance for the Teacher
    staff_sign_in(request.user)
    messages.success(request, "Attendance marked successfully.")
    return redirect('teacher_dashboard')

@login_required
def teacher_logout(request):
    logout(request)
    return redirect('login')

@login_required
def teacher_details(request):
    teacher_user = get_object_or_404(TeacherUser, id=request.user.id)
    staff = teacher_user.staff

    context = {
        'object': staff
    }

    return render(request, 'teachers/teacher_details.html', context)

@login_required
def teacher_salary_invoices(request):
    teacher_user = get_object_or_404(TeacherUser, id=request.user.id)
    staff = teacher_user.staff

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

    return render(request, 'teachers/teacher_salary_invoices.html', context)

@login_required
def teacher_class_list(request):
    classes = StudentClass.objects.all()
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        return redirect('teacher_class_results', class_id=class_id)
    
    context = {
        'classes': classes
    }
    return render(request, 'teachers/teacher_class_list.html', context)

@login_required
def teacher_class_results(request, class_id):
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
    return render(request, 'teachers/teacher_class_results.html', context)

@login_required
def all_class_list(request):
    classes = StudentClass.objects.all()
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        return redirect('all_class_results', class_id=class_id)
    
    context = {
        'classes': classes
    }
    return render(request, 'teachers/all_class_list.html', context)


@login_required
def all_class_results(request, class_id):
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
    return render(request, 'teachers/all_class_results.html', context)

class TeachersStudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "teachers/student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(current_status="active", completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        return context
    
class TeachersStaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'teachers/staff_list.html'
    context_object_name = 'staff_list'

    def get_queryset(self):
        return Staff.objects.filter(current_status='active')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_male'] = Staff.objects.filter(gender='male').count()
        context['total_female'] = Staff.objects.filter(gender='female').count()
        context['overall_total'] = Staff.objects.count()
        return context
    
class TeachersEventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'teachers/event_list.html'
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

class TeachersViewAvailableBooksView(View):
    def get(self, request):
        books_by_class = Book.objects.all().order_by('student_class')
        grouped_books = {}
        for book in books_by_class:
            if book.student_class.name not in grouped_books:
                grouped_books[book.student_class.name] = []
            grouped_books[book.student_class.name].append(book)
        return render(request, 'teachers/view_books.html', {'grouped_books': grouped_books})
    
class TeachersBookDetailView(View):
    def get(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        return render(request, 'teachers/book_details.html', {'book': book})

@login_required
def teacher_profile(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('teacher_dashboard')  # Replace 'academic_dashboard' with your actual dashboard URL name
    else:
        form = ProfilePictureForm(instance=request.user)
    return render(request, 'teachers/teachers_profile.html', {'form': form})

class TeacherStudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "teachers/student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(current_status="active", completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        return context

class TeacherInactiveStudentsView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "teachers/inactive_student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(current_status="inactive", completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        context['staff_list'] = Staff.objects.filter(current_status="inactive")
        return context

from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

class TeacherCompletedStudentsView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "teachers/completed_student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        # Retrieve students who are either inactive and completed or active and completed
        return Student.objects.filter(completed=True).filter(
            Q(current_status="inactive") | Q(current_status="active")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add student classes to the context for filtering in the template
        context['student_classes'] = StudentClass.objects.all()
        return context

class TeacherStaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'teachers/staff_list.html'
    context_object_name = 'staff_list'

    def get_queryset(self):
        return Staff.objects.filter(current_status='active')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_male'] = Staff.objects.filter(gender='male').count()
        context['total_female'] = Staff.objects.filter(gender='female').count()
        context['overall_total'] = Staff.objects.count()
        return context
