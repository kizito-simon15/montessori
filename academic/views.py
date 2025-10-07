from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from accounts.models import AcademicUser
from apps.finance.models import Invoice, SalaryInvoice
from django.shortcuts import render, get_object_or_404
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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import ClassSelectionForm, ResultEntryForm, SessionTermExamSubjectForm
from apps.corecode.models import StudentClass, Subject, AcademicSession, AcademicTerm, ExamType
from apps.students.models import Student
from apps.result.models import Result, StudentInfos
from .forms import StudentInfosForm, AcademicAnswersForm
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from apps.result.models import Result, StudentInfos
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, StudentClass
from apps.students.models import Student
from parents.models import ParentComments, StudentComments, InvoiceComments
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import DetailView, ListView, CreateView, DeleteView, UpdateView, View
from apps.staffs.models import Staff
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import DetailView, ListView, View
from apps.corecode.models import AcademicSession, AcademicTerm,ExamType,SiteConfig, StudentClass, Subject
from apps.students.models import Student
from collections import defaultdict
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from apps.students.models import Student
from .forms import StudentInfosForm
from apps.corecode.models import StudentClass, AcademicSession, AcademicTerm, ExamType
from django.views.generic.base import TemplateView
from django.db.models import Sum, Avg, Count
from django.forms import formset_factory, modelformset_factory
from django.db.models import Q
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import logging
from decimal import Decimal
from school_properties.models import Property
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.forms import ProfilePictureForm
from event.models import Event
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import AcademicAnswer, Student, AcademicSession, AcademicTerm, ExamType
from .forms import AcademicAnswerForm
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
def academic_dashboard(request):
    staff = request.user.academicuser.staff

    # Determine whether to show the sign-in button
    show_sign_in_button = should_show_sign_in_button(request.user)

    # Retrieve all comments that have not been marked as read
    new_comments = ParentComments.objects.filter(mark_comment=False)

    context = {
        'staff': staff,
        'new_comments': new_comments,
        'show_sign_in_button': show_sign_in_button,  # Pass this to the template
    }
    return render(request, 'academic/academic_dashboard.html', context)

@login_required
def mark_academic_attendance(request):
    # Mark the attendance for the Academic staff
    staff_sign_in(request.user)
    messages.success(request, "Attendance marked successfully.")
    return redirect('academic_dashboard')

@login_required
def academic_profile(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('academic_dashboard')  # Replace 'academic_dashboard' with your actual dashboard URL name
    else:
        form = ProfilePictureForm(instance=request.user)
    return render(request, 'academic/academic_profile.html', {'form': form})


@login_required
def academic_logout(request):
    logout(request)
    return redirect('login')


@login_required
def academic_details(request):
    academic_user = get_object_or_404(AcademicUser, id=request.user.id)
    staff = academic_user.staff

    context = {
        'object': staff
    }

    return render(request, 'academic/academic_details.html', context)

@login_required
def academic_salary_invoices(request):
    academic_user = get_object_or_404(AcademicUser, id=request.user.id)
    staff = academic_user.staff

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

    return render(request, 'academic/academic_salary_invoices.html', context)

@login_required
def create_academic_results_view(request):
    if request.method == 'POST':
        step = request.POST.get('step')
        if step == 'class_selection':
            class_form = ClassSelectionForm(request.POST)
            if class_form.is_valid():
                selected_class = class_form.cleaned_data['class_choices']
                request.session['selected_class'] = selected_class.id
                students = Student.objects.filter(
                    current_class=selected_class, 
                    current_status='active', 
                    completed=False
                )
                session_term_exam_subject_form = SessionTermExamSubjectForm()
                return render(request, 'academic/create_academic_results.html', {
                    'step': 'student_selection',
                    'class_form': class_form,
                    'students': students,
                    'session_term_exam_subject_form': session_term_exam_subject_form,
                    'student_classes': StudentClass.objects.all(),
                    'subjects': Subject.objects.all(),
                })
        elif step == 'student_selection':
            session_term_exam_subject_form = SessionTermExamSubjectForm(request.POST)
            student_ids = request.POST.getlist('students')
            selected_students = Student.objects.filter(id__in=student_ids)

            if session_term_exam_subject_form.is_valid():
                session = session_term_exam_subject_form.cleaned_data['session']
                term = session_term_exam_subject_form.cleaned_data['term']
                exam = session_term_exam_subject_form.cleaned_data['exam']
                subjects = session_term_exam_subject_form.cleaned_data['subjects']

                results = []
                for student in selected_students:
                    for subject in subjects:
                        result, created = Result.objects.get_or_create(
                            student=student,
                            session=session,
                            term=term,
                            exam=exam,
                            current_class=student.current_class,
                            subject=subject,
                        )
                        results.append(result)

                request.session['results'] = [result.id for result in results]
                result_forms = [ResultEntryForm(instance=result, prefix=result.id) for result in results]
                return render(request, 'academic/create_academic_results.html', {
                    'step': 'result_entry',
                    'result_forms': result_forms,
                    'student_classes': StudentClass.objects.all(),
                    'subjects': Subject.objects.all(),
                })
        elif step == 'result_entry':
            results = Result.objects.filter(id__in=request.session.get('results', []))
            success = True
            for result in results:
                form = ResultEntryForm(request.POST, instance=result, prefix=result.id)
                if form.is_valid():
                    form.save()
                else:
                    success = False
            if success:
                messages.success(request, 'Results saved successfully.')
                request.session.pop('results', None)
                return redirect('create_academic_results_view')
            else:
                result_forms = [ResultEntryForm(instance=result, prefix=result.id) for result in results]
                return render(request, 'academic/create_academic_results.html', {
                    'step': 'result_entry',
                    'result_forms': result_forms,
                    'student_classes': StudentClass.objects.all(),
                    'subjects': Subject.objects.all(),
                })
    else:
        # Check for the query parameter to reset the session state
        step = request.GET.get('step', None)
        if step == 'class_selection':
            request.session.pop('results', None)

        class_form = ClassSelectionForm()

        # If there are results in the session, retrieve and display them
        results = Result.objects.filter(id__in=request.session.get('results', []))
        if results:
            result_forms = [ResultEntryForm(instance=result, prefix=result.id) for result in results]
            return render(request, 'academic/create_academic_results.html', {
                'step': 'result_entry',
                'result_forms': result_forms,
                'student_classes': StudentClass.objects.all(),
                'subjects': Subject.objects.all(),
            })

    return render(request, 'academic/create_academic_results.html', {
        'step': 'class_selection',
        'class_form': class_form,
        'student_classes': StudentClass.objects.all(),
        'subjects': Subject.objects.all(),
    })

@login_required
def edit_academic_results(request):
    if request.method == 'POST':
        result_ids = request.POST.getlist('result_ids')
        for result_id in result_ids:
            result = get_object_or_404(Result, id=result_id)
            form = ResultEntryForm(request.POST, instance=result, prefix=f'result_{result_id}')
            if form.is_valid():
                form.save()
        messages.success(request, 'Results updated successfully.')
        return redirect('edit_academic_results')

    else:
        results = Result.objects.all()
        result_forms = [(result, ResultEntryForm(instance=result, prefix=f'result_{result.id}')) for result in results]

    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam_type = ExamType.objects.filter(current=True).first()

    context = {
        'result_forms': result_forms,
        'sessions': AcademicSession.objects.all(),
        'terms': AcademicTerm.objects.all(),
        'exam_types': ExamType.objects.all(),
        'student_classes': StudentClass.objects.all(),
        'subjects': Subject.objects.all(),
        'current_session': current_session,
        'current_term': current_term,
        'current_exam_type': current_exam_type,
    }
    return render(request, 'academic/edit_academic_results.html', context)

@login_required
def academic_class_list(request):
    classes = StudentClass.objects.all()
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        return redirect('academic-single-results', class_id=class_id)
    
    context = {
        'classes': classes
    }
    return render(request, 'academic/academic_class_list.html', context)


from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, Subject
from apps.students.models import Student, StudentClass
from apps.result.models import Result

@login_required
def academic_class_results(request, class_id):
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

                    students = Student.objects.filter(
                        result__current_class=selected_class,
                        result__session=session,
                        result__term=term,
                        result__exam=exam
                    ).distinct()

                    for student in students:
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
                            subject_result = results.filter(student=student, subject=subject).first()
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

                        # Assign the same position for the tie group
                        average_position = round(sum(range(current_position, current_position + len(tie_group))) / len(tie_group), 1)
                        for student_data in tie_group:
                            student_data['position'] = average_position

                        # Update the current position for the next group
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
    return render(request, 'academic/academic_class_results.html', context)

@login_required
def academic_all_class_list(request):
    classes = StudentClass.objects.all()
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        return redirect('academic-class-results', class_id=class_id)
    
    context = {
        'classes': classes
    }
    return render(request, 'academic/academic_all_class_list.html', context)


@login_required
def academic_all_class_results(request, class_id):
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
                    
                    for student in Student.objects.filter(current_class=selected_class).distinct():
                        student_data = {
                            'student': student,
                            'student_class': selected_class,
                            'subjects': {},
                            'total': 0,
                            'overall_average': Decimal(0),
                            'overall_status': 'FAIL'
                        }
                        
                        total_score = Decimal(0)
                        total_subjects = 0
                        for subject in subjects:
                            subject_result = results.filter(student=student, subject=subject).first()
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
    return render(request, 'academic/academic_all_class_results.html', context)


@login_required
def student_infos_form_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # Try to retrieve the existing student info
    try:
        student_info = StudentInfos.objects.get(student=student)
    except StudentInfos.DoesNotExist:
        student_info = None

    if request.method == "POST":
        form = StudentInfosForm(request.POST, instance=student_info)
        if form.is_valid():
            student_info = form.save(commit=False)
            student_info.student = student
            student_info.save()
            messages.success(request, "Student information has been saved successfully.")
            return redirect('student_infos_form_view', student_id=student.id)
    else:
        form = StudentInfosForm(instance=student_info)

    context = {
        'form': form,
        'student': student,
    }

    return render(request, 'academic/student_infos_form.html', context)

@login_required
def academic_form_results_view(request, class_id):
    student_class = get_object_or_404(StudentClass, id=class_id)

    # Retrieve all students in the class
    students = Student.objects.filter(current_class=student_class)

    # Retrieve all sessions, terms, and exam types
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    exam_types = ExamType.objects.all()

    # Retrieve the current session, term, and exam type
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()

    # Retrieve all results and student information for the students in the class
    results = Result.objects.filter(student__in=students).select_related('student', 'subject', 'session', 'term', 'exam')
    student_infos = StudentInfos.objects.filter(student__in=students).select_related('student', 'session', 'term', 'exam')

    # Retrieve parent comments
    parent_comments = ParentComments.objects.filter(student__in=students, session=current_session, term=current_term, exam=current_exam)

    # Handle form submission
    if request.method == 'POST':
        student_info_id = request.POST.get('student_info_id')
        student_info = get_object_or_404(StudentInfos, id=student_info_id)
        form = AcademicAnswersForm(request.POST, instance=student_info)
        if form.is_valid():
            form.save()
            messages.success(request, 'Academic answers saved successfully.')
            return redirect('academic_form_results_view', class_id=class_id)
    else:
        form = AcademicAnswersForm()

    # Organize results and student info by session, term, and exam type
    grouped_data = {}
    for session in sessions:
        grouped_data[session] = {}
        for term in terms:
            grouped_data[session][term] = {}
            for exam_type in exam_types:
                grouped_data[session][term][exam_type] = {
                    'students_with_forms': students.prefetch_related(Prefetch('studentinfos_set', queryset=student_infos.filter(session=session, term=term, exam=exam_type))),
                    'student_results': [],
                    'parent_comments': parent_comments
                }
                student_averages = []
                for student in students:
                    student_result = {
                        'student': student,
                        'results': [],
                        'total_average': 0,
                        'total_marks': 0,
                        'overall_average': 0,
                        'overall_grade': '',
                        'position': 0,
                        'total_students': 0,
                        'total_possible_marks': 0,  # Initialize total possible marks
                    }

                    student_results_data = results.filter(student=student, session=session, term=term, exam=exam_type)
                    subject_count = student_results_data.count()
                    student_result['total_possible_marks'] = subject_count * 50  # Calculate total possible marks
                    for result in student_results_data:
                        student_result['results'].append(result)
                        student_result['total_average'] += result.average
                        student_result['total_marks'] += result.calculate_overall_total_marks()

                    if student_result['results']:
                        student_result['overall_average'] = student_result['total_average'] / subject_count if subject_count > 0 else 0
                        student_result['overall_grade'] = Result.calculate_overall_grade(student)
                        student_result['total_students'] = results.filter(session=session, term=term, exam=exam_type).values('student').distinct().count()
                        student_averages.append((student_result['overall_average'], student.id))
                        
                    grouped_data[session][term][exam_type]['student_results'].append(student_result)

                # Sort students by overall average to determine positions
                student_averages.sort(reverse=True, key=lambda x: x[0])
                for idx, (average, student_id) in enumerate(student_averages, start=1):
                    for student_result in grouped_data[session][term][exam_type]['student_results']:
                        if student_result['student'].id == student_id:
                            student_result['position'] = idx

    # Count completed forms
    completed_forms_count = sum(1 for student_info in student_infos if all([
        student_info.disprine,
        student_info.sports,
        student_info.care_of_property,
        student_info.collaborations,
        student_info.date_of_closing,
        student_info.date_of_opening,
        student_info.teacher_comments,
        student_info.head_comments
    ]))

    context = {
        'student_class': student_class,
        'grouped_data': grouped_data,
        'completed_forms_count': completed_forms_count,
        'current_session': current_session,
        'current_term': current_term,
        'current_exam': current_exam,
        'form': form,
        'student_infos': student_infos,  # Pass student_infos to the template
    }

    return render(request, 'academic/class_results_view.html', context)

class AcademicStudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "academic/academic_student_list.html"
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(current_status="active", completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        return context


class AcademicInactiveStudentsView(LoginRequiredMixin, ListView):
    model = Student
    context_object_name = "students"
    template_name = "academic/academic_inactive_students.html"

    def get_queryset(self):
        return Student.objects.filter(current_status="inactive", completed=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        context['staff_list'] = Staff.objects.filter(current_status="inactive")
        return context

class AcademicCompletedStudentsView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "academic/academic_completed_students.html"
    context_object_name = "students"

    def get_queryset(self):
        return Student.objects.filter(current_status="inactive", completed=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_classes'] = StudentClass.objects.all()
        return context

class AcademicCompletedStudentDetailView(DetailView):
    model = Student
    template_name = "academic/academic_completed_student_detail.html"
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

class AcademicStaffListView(LoginRequiredMixin, ListView):
    model = Staff
    template_name = 'academic/academic_staff_list.html'
    context_object_name = 'staff_list'

    def get_queryset(self):
        return Staff.objects.filter(current_status='active')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_male'] = Staff.objects.filter(gender='male').count()
        context['total_female'] = Staff.objects.filter(gender='female').count()
        context['overall_total'] = Staff.objects.count()
        return context

class AcademicSearchStudents(View):
    def get(self, request):
        term = request.GET.get('term')
        students = Student.objects.filter(name__icontains=term)
        data = [{'id': student.id, 'text': student.name} for student in students]
        return JsonResponse(data, safe=False)

class AcademicStudentResultsView(LoginRequiredMixin, View):
    template_name = 'academic/academic_student_results.html'

    def get(self, request, student_id):
        student = get_object_or_404(Student, pk=student_id)
        form = StudentInfosForm(instance=student.studentinfos_set.filter(
            session=AcademicSession.objects.filter(current=True).first(),
            term=AcademicTerm.objects.filter(current=True).first(),
            exam=ExamType.objects.filter(current=True).first(),
        ).last())  # Retrieve the last saved form instance for the current session, term, and exam
        session = AcademicSession.objects.filter(current=True).first()
        term = AcademicTerm.objects.filter(current=True).first()
        exam_type = ExamType.objects.filter(current=True).first()
        student_class = student.current_class

        return render(request, self.template_name, {
            'form': form,
            'session': session,
            'term': term,
            'exam_type': exam_type,
            'student_class': student_class,
            'student': student,
        })

    def post(self, request, student_id):
        student = get_object_or_404(Student, pk=student_id)
        session = AcademicSession.objects.filter(current=True).first()
        term = AcademicTerm.objects.filter(current=True).first()
        exam_type = ExamType.objects.filter(current=True).first()
        student_class = student.current_class

        form = StudentInfosForm(request.POST)
        if form.is_valid():
            student_info = form.save(commit=False)
            student_info.student = student
            student_info.session = session
            student_info.term = term
            student_info.exam = exam_type
            student_info.save()
            messages.success(request, 'The student information has been saved successfully.')
            return redirect('student-results', student_id=student_id)

        return render(request, self.template_name, {
            'form': form,
            'session': session,
            'term': term,
            'exam_type': exam_type,
            'student_class': student_class,
            'student': student,
        })

class AcademicSingleStudentResultsView(LoginRequiredMixin, TemplateView):
    template_name = 'academic/academic_single_student_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = kwargs.get('student_id')

        # Retrieve the student
        student = Student.objects.get(pk=student_id)

        # Get the current academic session, term, and exam
        current_session = AcademicSession.objects.get(current=True)
        current_term = AcademicTerm.objects.get(current=True)
        current_exam = ExamType.objects.get(current=True)

        # Retrieve results for the specified student, session, term, and exam
        student_results = Result.objects.filter(
            student_id=student_id,
            session=current_session,
            term=current_term,
            exam=current_exam
        )

        # Pass the student's name and registration number to the template
        context['student_name'] = f"{student.firstname} {student.middle_name} {student.surname}"
        context['registration_number'] = student.registration_number

        # Calculate total marks for each subject and their respective comments
        subjects = {}
        for result in student_results:
            subject_name = result.subject.name
            subjects[subject_name] = {
                'test_score': result.test_score or 0,
                'exam_score': result.exam_score or 0,
                'average': result.average or 0,
                'grade': result.calculate_grade(),
                'status': result.calculate_status(),
                'comments': result.calculate_comments(),  # Ensure each subject gets its correct comment
            }

        # Pass the calculated results to the template
        context['subjects'] = subjects

        # Calculate total marks, total marks of all subjects, overall average, overall grade,
        # position, and total students
        total = sum(result.total for result in student_results)
        total_marks = sum(result.calculate_overall_total_marks() for result in student_results)
        overall_average = sum(result.overall_average for result in student_results) / len(student_results) if student_results else None
        overall_grade = student_results[0].calculate_overall_grade(student) if student_results else None
        position = Result.calculate_position(overall_average)

        # Add these values to the context
        context.update({
            'total': total,
            'total_marks': total_marks,
            'overall_average': overall_average,
            'overall_grade': overall_grade,
            'position': position,
            'student_id': student_id,
        })

        return context

class AcademicSingleClassResultsView(LoginRequiredMixin, TemplateView):
    template_name = 'academic/academic_single_class_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        selected_class = StudentClass.objects.get(pk=class_id)

        session_id = self.request.GET.get('session', None)
        term_id = self.request.GET.get('term', None)
        exam_id = self.request.GET.get('exam', None)

        if session_id:
            session = AcademicSession.objects.get(id=session_id)
        else:
            session = AcademicSession.objects.get(current=True)

        if term_id:
            term = AcademicTerm.objects.get(id=term_id)
        else:
            term = AcademicTerm.objects.get(current=True)

        if exam_id:
            exam = ExamType.objects.get(id=exam_id)
        else:
            exam = ExamType.objects.get(current=True)

        context['class_id'] = class_id
        context['selected_class'] = selected_class
        context['sessions'] = AcademicSession.objects.all()
        context['terms'] = AcademicTerm.objects.all()
        context['exams'] = ExamType.objects.all()
        context['current_session'] = session
        context['current_term'] = term
        context['current_exam'] = exam

        # Retrieve results for the given session, term, exam, and class
        results = Result.objects.filter(
            current_class=selected_class,
            session=session,
            term=term,
            exam=exam
        ).select_related('student', 'subject')

        if not results.exists():
            context['no_results'] = True
            return context

        context['no_results'] = False

        students = Student.objects.filter(
            result__current_class=selected_class,
            result__session=session,
            result__term=term,
            result__exam=exam
        ).distinct()

        data = []
        subjects = set()

        for student in students:
            student_results = results.filter(student=student)

            if student_results.exists():
                student_data = {
                    'student': student,
                    'student_class': selected_class,  # Use the class from the Result model
                    'subjects': {},
                    'total': 0,
                    'overall_average': 0,
                    'overall_status': 'FAIL',
                }

                total_marks = 0
                subject_count = 0

                for result in student_results:
                    subjects.add(result.subject.name)
                    student_data['subjects'][result.subject.name] = {
                        'test_score': result.test_score,
                        'exam_score': result.exam_score,
                        'average': result.average
                    }
                    total_marks += result.average if result.average else 0
                    subject_count += 1

                if subject_count > 0:
                    student_data['total'] = total_marks
                    student_data['overall_average'] = total_marks / subject_count
                    student_data['overall_status'] = 'PASS' if student_data['overall_average'] >= 25 else 'FAIL'

                data.append(student_data)

        # Sort students by overall average in descending order
        sorted_data = sorted(data, key=lambda x: x['overall_average'], reverse=True)

        # Assign positions with tie handling
        current_position = 1
        i = 0

        while i < len(sorted_data):
            tie_group = [sorted_data[i]]
            j = i + 1

            while j < len(sorted_data) and sorted_data[j]['overall_average'] == sorted_data[i]['overall_average']:
                tie_group.append(sorted_data[j])
                j += 1

            # Calculate average position for the tie group
            if len(tie_group) > 1:
                average_position = current_position + 0.5
                for student_data in tie_group:
                    student_data['position'] = average_position
            else:
                tie_group[0]['position'] = current_position

            # Move to the next group
            current_position += len(tie_group)
            i = j

        context['data'] = sorted_data
        context['subjects'] = sorted(subjects)

        # Calculate subject averages, grades, and GPAs for the given class
        subject_data = []
        for subject_name in subjects:
            subject = Subject.objects.get(name=subject_name)
            subject_average = self.calculate_subject_average(selected_class, subject, session, term, exam)
            subject_grade = self.calculate_subject_grade(subject_average)
            subject_gpa = self.calculate_subject_gpa(selected_class, subject, session, term, exam)
            subject_data.append({
                'subject': subject_name,
                'average': subject_average,
                'grade': subject_grade,
                'gpa': subject_gpa
            })
        context['subject_data'] = sorted(subject_data, key=lambda x: x['average'], reverse=True)

        return context

    def calculate_subject_average(self, student_class, subject, session, term, exam):
        results = Result.objects.filter(
            current_class=student_class,
            subject=subject,
            session=session,
            term=term,
            exam=exam
        )

        total_average = results.aggregate(total_average=Sum('average'))['total_average'] or 0
        count = results.count()
        if count == 0:
            return 0.00
        else:
            return round(total_average / count, 2)

    def calculate_subject_grade(self, subject_average):
        if subject_average > 41:
            return "A"
        elif 31 <= subject_average < 41:
            return "B"
        elif 25 <= subject_average < 31:
            return "C"
        elif 15 <= subject_average < 25:
            return "D"
        else:
            return "F"

    def calculate_subject_gpa(self, student_class, subject, session, term, exam):
        results = Result.objects.filter(
            current_class=student_class,
            subject=subject,
            session=session,
            term=term,
            exam=exam
        )

        count = results.count()
        if count == 0:
            return 0.00

        total_average = results.aggregate(total_average=Sum('average'))['total_average'] or Decimal(0)
        subject_average = total_average / count
        max_score = Decimal(50)
        gpa = (subject_average / max_score) * Decimal(4.0)

        return round(gpa, 2)

class AcademicClassResultsView(LoginRequiredMixin, TemplateView):
    template_name = 'academic/academics_class_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        selected_class = StudentClass.objects.get(pk=class_id)

        session_id = self.request.GET.get('session', None)
        term_id = self.request.GET.get('term', None)
        exam_id = self.request.GET.get('exam', None)

        # Get current session, term, and exam if not provided
        session = AcademicSession.objects.get(id=session_id) if session_id else AcademicSession.objects.get(current=True)
        term = AcademicTerm.objects.get(id=term_id) if term_id else AcademicTerm.objects.get(current=True)
        exam = ExamType.objects.get(id=exam_id) if exam_id else ExamType.objects.get(current=True)

        context['class_id'] = class_id
        context['selected_class'] = selected_class
        context['sessions'] = AcademicSession.objects.all()
        context['terms'] = AcademicTerm.objects.all()
        context['exams'] = ExamType.objects.all()
        context['current_session'] = session
        context['current_term'] = term
        context['current_exam'] = exam

        # Retrieve results for the selected class, session, term, and exam
        results = Result.objects.filter(
            current_class=selected_class,
            session=session,
            term=term,
            exam=exam
        ).select_related('student', 'subject')

        if not results.exists():
            context['no_results'] = True
            return context

        context['no_results'] = False

        # Get students who have results in the selected class, session, term, and exam
        students = Student.objects.filter(
            result__current_class=selected_class,
            result__session=session,
            result__term=term,
            result__exam=exam
        ).distinct()

        data = []
        subjects = set()

        for student in students:
            student_results = results.filter(student=student)

            if student_results.exists():
                student_data = {
                    'student': student,
                    'student_class': selected_class,  # Use the class from the Result model
                    'subjects': {},
                    'total': 0,
                    'overall_average': 0,
                    'overall_status': 'FAIL',
                }

                total_marks = 0
                subject_count = 0

                for result in student_results:
                    subjects.add(result.subject.name)
                    student_data['subjects'][result.subject.name] = {
                        'test_score': result.test_score,
                        'exam_score': result.exam_score,
                        'average': result.average
                    }
                    total_marks += result.average if result.average else 0
                    subject_count += 1

                if subject_count > 0:
                    student_data['total'] = total_marks
                    student_data['overall_average'] = total_marks / subject_count
                    student_data['overall_status'] = 'PASS' if student_data['overall_average'] >= 25 else 'FAIL'

                data.append(student_data)

        # Sort students by overall average in descending order
        sorted_data = sorted(data, key=lambda x: x['overall_average'], reverse=True)

        # Calculate positions with tie handling
        current_position = 1
        i = 0

        while i < len(sorted_data):
            tie_group = [sorted_data[i]]
            j = i + 1

            while j < len(sorted_data) and sorted_data[j]['overall_average'] == sorted_data[i]['overall_average']:
                tie_group.append(sorted_data[j])
                j += 1

            # Calculate average position for the tie group
            if len(tie_group) > 1:
                average_position = current_position + 0.5
                for student_data in tie_group:
                    student_data['position'] = average_position
            else:
                tie_group[0]['position'] = current_position

            # Move to the next group
            current_position += len(tie_group)
            i = j

        context['data'] = sorted_data
        context['subjects'] = sorted(subjects)

        # Calculate subject averages, grades, and GPAs
        subject_data = []
        for subject_name in subjects:
            subject = Subject.objects.get(name=subject_name)
            subject_average = self.calculate_subject_average(selected_class, subject, session, term, exam)
            subject_grade = self.calculate_subject_grade(subject_average)
            subject_gpa = self.calculate_subject_gpa(selected_class, subject, session, term, exam)
            subject_data.append({
                'subject': subject_name,
                'average': subject_average,
                'grade': subject_grade,
                'gpa': subject_gpa
            })

        context['subject_data'] = sorted(subject_data, key=lambda x: x['average'], reverse=True)

        return context

    def calculate_subject_average(self, student_class, subject, session, term, exam):
        results = Result.objects.filter(
            current_class=student_class,
            subject=subject,
            session=session,
            term=term,
            exam=exam
        )

        total_average = results.aggregate(total_average=Sum('average'))['total_average'] or 0
        count = results.count()
        if count == 0:
            return 0.00
        else:
            return round(total_average / count, 2)

    def calculate_subject_grade(self, subject_average):
        if subject_average > 41:
            return "A"
        elif 31 <= subject_average < 41:
            return "B"
        elif 25 <= subject_average < 31:
            return "C"
        elif 15 <= subject_average < 25:
            return "D"
        else:
            return "F"

    def calculate_subject_gpa(self, student_class, subject, session, term, exam):
        results = Result.objects.filter(
            current_class=student_class,
            subject=subject,
            session=session,
            term=term,
            exam=exam
        )

        count = results.count()
        if count == 0:
            return 0.00

        total_average = results.aggregate(total_average=Sum('average'))['total_average'] or Decimal(0)
        subject_average = total_average / count
        max_score = Decimal(50)
        gpa = (subject_average / max_score) * Decimal(4.0)

        return round(gpa, 2)

from django.shortcuts import get_object_or_404, redirect
from django.views import View
from .models import AcademicAnswer, Student
from .forms import AcademicAnswerForm
from parents.models import ParentComments
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Sum, Avg, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import AcademicAnswerForm
from .models import AcademicAnswer
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, Signature
from apps.students.models import Student, StudentClass
from parents.models import ParentComments

class AcademicFormStatusView(LoginRequiredMixin, View):
    template_name = 'academic/academic_form_status.html'

    def calculate_overall_grade(self, overall_average):
        if overall_average >= 41:
            return "A"
        elif 30 <= overall_average < 41:
            return "B"
        elif 25 <= overall_average < 30:
            return "C"
        elif 15 <= overall_average < 25:
            return "D"
        else:
            return "F"

    def calculate_overall_total_marks(self, student):
        subject_count = student.result_set.values('subject').distinct().count()
        return subject_count * 50

    def get_total_active_students(self, class_id, current_session, current_term, current_exam_type):
        """
        Calculate the total number of active students who have not completed school
        in the given class, session, term, and exam.
        """
        return Student.objects.filter(
            result__current_class_id=class_id,
            result__session=current_session,
            result__term=current_term,
            result__exam=current_exam_type,
            current_status="active",
            completed=False
        ).distinct().count()

    def get(self, request, class_id):
        student_class = get_object_or_404(StudentClass, pk=class_id)

        current_session = request.GET.get('session', AcademicSession.objects.filter(current=True).first().id)
        current_term = request.GET.get('term', AcademicTerm.objects.filter(current=True).first().id)
        current_exam_type = request.GET.get('exam', ExamType.objects.filter(current=True).first().id)

        sessions = AcademicSession.objects.all()
        terms = AcademicTerm.objects.all()
        exams = ExamType.objects.all()

        # Calculate the total number of active students
        total_active_students = self.get_total_active_students(class_id, current_session, current_term, current_exam_type)

        students_with_forms = Student.objects.filter(
            result__current_class=student_class,
            result__session=current_session,
            result__term=current_term,
            result__exam=current_exam_type
        ).distinct()

        query = request.GET.get('q')
        if query:
            students_with_forms = students_with_forms.filter(
                Q(firstname__icontains=query) | Q(middle_name__icontains=query) | Q(surname__icontains=query) | Q(registration_number=query)
            )

        no_forms = not students_with_forms.exists()

        completed_forms_count = 0
        for student_info in students_with_forms:
            last_student_info = student_info.studentinfos_set.last()
            if last_student_info and all([
                last_student_info.disprine,
                last_student_info.sports,
                last_student_info.care_of_property,
                last_student_info.collaborations,
                last_student_info.date_of_closing,
                last_student_info.date_of_opening,
                last_student_info.teacher_comments,
                last_student_info.head_comments
            ]):
                completed_forms_count += 1

        student_results = []
        for student in students_with_forms:
            student_results_queryset = student.result_set.filter(
                current_class=student_class,
                session=current_session,
                term=current_term,
                exam=current_exam_type
            )

            total_average = student_results_queryset.aggregate(Sum('average'))['average__sum']
            overall_average = student_results_queryset.aggregate(Avg('average'))['average__avg']
            overall_grade = self.calculate_overall_grade(overall_average) if overall_average is not None else "No results available"
            overall_total_marks = self.calculate_overall_total_marks(student)

            student_results.append({
                'student': student,
                'total_average': total_average,
                'overall_average': overall_average,
                'overall_grade': overall_grade,
                'overall_total_marks': overall_total_marks,
                'results': student_results_queryset,
            })

        # Sort students by overall average in descending order
        sorted_results = sorted(student_results, key=lambda x: x['overall_average'] or 0, reverse=True)

        # Assign positions with tie handling
        current_position = 1
        i = 0

        while i < len(sorted_results):
            tie_group = [sorted_results[i]]
            j = i + 1

            while j < len(sorted_results) and sorted_results[j]['overall_average'] == sorted_results[i]['overall_average']:
                tie_group.append(sorted_results[j])
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

        headmaster_signature = Signature.objects.filter(name="Headmaster's signature").first()

        return render(request, self.template_name, {
            'student_class': student_class,
            'students_with_forms': students_with_forms,
            'student_results': sorted_results,
            'sessions': sessions,
            'terms': terms,
            'exams': exams,
            'current_session': AcademicSession.objects.get(id=current_session),
            'current_term': AcademicTerm.objects.get(id=current_term),
            'current_exam_type': ExamType.objects.get(id=current_exam_type),
            'completed_forms_count': completed_forms_count,
            'no_forms': no_forms,
            'total_active_students': total_active_students,  # Pass the total active students to the template
            'academic_answer_form': AcademicAnswerForm(),
            'headmaster_signature': headmaster_signature,
        })

    def post(self, request, class_id):
        form = AcademicAnswerForm(request.POST, request.FILES)
        if form.is_valid():
            current_session = request.POST.get('session')
            current_term = request.POST.get('term')
            current_exam_type = request.POST.get('exam')
            student_id = request.POST.get('student_id')

            student = get_object_or_404(Student, pk=student_id)
            session = get_object_or_404(AcademicSession, pk=current_session)
            term = get_object_or_404(AcademicTerm, pk=current_term)
            exam = get_object_or_404(ExamType, pk=current_exam_type)

            academic_answer, created = AcademicAnswer.objects.get_or_create(
                session=session,
                term=term,
                exam=exam,
                student=student
            )
            academic_answer.answer = form.cleaned_data['answer']
            if 'audio_answer' in request.FILES:
                academic_answer.audio_answer = request.FILES['audio_answer']
            academic_answer.save()

            messages.success(request, 'Academic answer saved successfully.')
            return redirect('academic_form_status', class_id=class_id)

        messages.error(request, 'There was an error saving the academic answer.')
        return redirect('academic_form_status', class_id=class_id)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View
from django.urls import reverse
from library.models import Book, IssuedBook, IssuedStaff, Stationery
from library.forms import BookForm, IssueBookForm, IssueStaffForm, StationeryForm
from apps.students.models import Student
from apps.staffs.models import Staff
from apps.corecode.models import AcademicSession, StudentClass
from django.shortcuts import render
from collections import defaultdict
from django.db.models import Sum
from itertools import groupby
from operator import attrgetter
from datetime import datetime

class AcademicLibraryActionView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, 'academic/library_actions.html')

class AcademicAddBookView(View):
    def get(self, request):
        form = BookForm()
        return render(request, 'academic/add_book.html', {'form': form})

    def post(self, request):
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            current_session = AcademicSession.objects.get(current=True)
            book.session = current_session
            book.save()
            messages.success(request, 'New book added successfully')
            return redirect('academic_add_book')
        return render(request, 'academic/add_book.html', {'form': form})

class AcademicViewAvailableBooksView(View):
    def get(self, request):
        books_by_class = Book.objects.all().order_by('student_class')
        grouped_books = {}
        for book in books_by_class:
            if book.student_class.name not in grouped_books:
                grouped_books[book.student_class.name] = []
            grouped_books[book.student_class.name].append(book)
        return render(request, 'academic/view_books.html', {'grouped_books': grouped_books})



class AcademicIssueNewBookView(View):
    def get(self, request):
        students = Student.objects.all()
        books = Book.objects.all()
        form = IssueBookForm()
        return render(request, 'academic/issue_book.html', {'form': form, 'students': students, 'books': books})

    def post(self, request):
        students = Student.objects.all()
        books = Book.objects.all()
        form = IssueBookForm(request.POST)
        if form.is_valid():
            issued_book = form.save(commit=False)
            issued_book.save()
            messages.success(request, 'The book was issued successfully')
            return redirect('academic_issue_new_book')
        return render(request, 'academic/issue_book.html', {'form': form, 'students': students, 'books': books})

class AcademicMarkBookReturnedView(View):
    def get(self, request, issued_book_id):
        issued_book = get_object_or_404(IssuedBook, id=issued_book_id)
        issued_book.returned = True
        issued_book.save()
        return redirect('academic_view_issued_books')

class AcademicIssuedStudentsView(View):
    def get(self, request):
        issued_once_students = Student.objects.filter(issuedbook__isnull=False).distinct()
        return render(request, 'academic_all_issued.html', {'issued_once_students': issued_once_students})

class AcademicViewIssuedBooksView(View):
    def get(self, request):
        student_id = request.GET.get('student_id')
        student_name = None
        if student_id:
            student = Student.objects.get(pk=student_id)
            student_name = student.firstname + ' ' + student.middle_name + ' ' + student.surname
            issued_books = IssuedBook.objects.filter(student=student)
        else:
            issued_books = IssuedBook.objects.all()
        return render(request, 'academic/issued_books.html', {'issued_books': issued_books, 'student_name': student_name})

def academic_delete_issued_book(request, issued_book_id):
    # Retrieve the issued book object or return 404 if not found
    issued_book = get_object_or_404(IssuedBook, id=issued_book_id)

    # Delete the issued book
    issued_book.delete()

    # Redirect to a success URL or any other page
    return redirect('academic_view_issued_books')  # Redirect to the view_issued_books page after deletion

def academic_delete_issued_staff(request, issued_book_id):
    # Retrieve the issued book object or return 404 if not found
    issued_books = get_object_or_404(IssuedStaff, id=issued_book_id)

    # Delete the issued book
    issued_books.delete()

    # Redirect to a success URL or any other page
    return redirect('academic_view_issued_staffs')  # Redirect to the view_issued_staffs page after deletion


class AcademicIssueStaffBookView(View):
    def get(self, request):
        staffs = Staff.objects.all()
        books = Book.objects.all()
        student_classes = StudentClass.objects.all()
        authors = Book.objects.values_list('author', flat=True).distinct()
        form = IssueStaffForm()
        return render(request, 'academic/issue_staff.html', {'form': form, 'staffs': staffs, 'books': books, 'student_classes': student_classes, 'authors': authors})

    def post(self, request):
        staffs = Staff.objects.all()
        student_classes = StudentClass.objects.all()
        book_name = request.POST.get('book_name')
        student_class_id = request.POST.get('student_class')
        author = request.POST.get('author')
        staff_name = request.POST.get('staff_name')
        books = Book.objects.all()
        authors = Book.objects.values_list('author', flat=True).distinct()

        if book_name:
            books = books.filter(book_name__icontains=book_name)
        if student_class_id:
            books = books.filter(student_class_id=student_class_id)
        if author:
            books = books.filter(author__icontains=author)
        if staff_name:
            staffs = staffs.filter(surname__icontains=staff_name) | staffs.filter(firstname__icontains=staff_name)

        form = IssueStaffForm(request.POST)
        if form.is_valid():
            issued_staff = form.save(commit=False)
            issued_staff.save()
            messages.success(request, 'The book was issued successfully')
            return redirect('academic_issue_new_staff')
        return render(request, 'academic/issue_staff.html', {'form': form, 'staffs': staffs, 'books': books, 'student_classes': student_classes, 'authors': authors})


class AcademicIssuedStaffsView(View):
    def get(self, request):
        issued_once_staffs = Staff.objects.filter(issuedstaff__isnull=False).distinct()
        return render(request, 'academic/all_staff.html', {'issued_once_staffs': issued_once_staffs})

class AcademicViewIssuedStaffsView(View):
    def get(self, request):
        staff_id = request.GET.get('staff_id')
        staff_name = None
        if staff_id:
            staff = Staff.objects.get(pk=staff_id)
            staff_name = staff.firstname + ' ' + staff.middle_name + ' ' + staff.surname
            issued_books = IssuedStaff.objects.filter(staff=staff)
        else:
            issued_books = IssuedStaff.objects.all()
        return render(request, 'academic/issued_staffs.html', {'issued_books': issued_books, 'staff_name': staff_name})

class AcademicMarkStaffReturnedView(View):
    def get(self, request, issued_book_id):
        issued_book = get_object_or_404(IssuedStaff, id=issued_book_id)
        issued_book.returned = True
        issued_book.save()
        return redirect('academic_view_issued_staffs')

class AcademicUpdateBookView(View):
    def get(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        student_classes = StudentClass.objects.all()
        return render(request, 'academic/update_book.html', {'book': book, 'student_classes': student_classes})

    def post(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        book.description = request.POST.get('description')
        book.quantity = request.POST.get('quantity')
        book.category = request.POST.get('category')
        book.date_buyed = request.POST.get('date_buyed')  # Add this line to handle date_buyed
        class_id = request.POST.get('class')
        if class_id:
            book.student_class = StudentClass.objects.get(pk=class_id)
        book.save()
        student_classes = StudentClass.objects.all()
        return render(request, 'academic/update_book.html', {'book': book, 'student_classes': student_classes, 'message': 'Book updated successfully'})

class AcademicBookDetailView(View):
    def get(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        return render(request, 'academic/book_details.html', {'book': book})

class AcademicDeleteBookView(View):
    def get(self, request, book_id):
        book = get_object_or_404(Book, pk=book_id)
        return render(request, 'academic/delete_book.html', {'book': book})

    def post(self, request, book_id):
        book = get_object_or_404(Book, pk=book_id)
        book.delete()
        messages.success(request, 'Book deleted successfully')
        return redirect('academic_library_action')

class AcademicAddStationeryView(View):
    def get(self, request):
        form = StationeryForm()
        return render(request, 'academic/add_stationery.html', {'form': form})

    def post(self, request):
        form = StationeryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'New stationery added successfully')
            return redirect('academic_add_stationery')
        return render(request, 'academic/add_stationery.html', {'form': form})

class AcademicStationeryListView(View, LoginRequiredMixin):

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

        return render(request, 'academic/stationery_list.html', {
            'grouped_stationeries': sorted_grouped_stationeries,
            'total_quantity': total_quantity
        })

class AcademicStationeryDetailView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        return render(request, 'academic/stationery_details.html', {'stationery': stationery})

class AcademicStationeryUpdateView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        form = StationeryForm(instance=stationery)
        return render(request, 'academic/stationery_update.html', {'form': form, 'stationery': stationery})

    def post(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        form = StationeryForm(request.POST, instance=stationery)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stationery updated successfully')
            return redirect('academic_stationery_detail', stationery_id=stationery.id)
        return render(request, 'academic/stationery_update.html', {'form': form, 'stationery': stationery})


class AcademicStationeryDeleteView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        return render(request, 'academic/stationery_delete.html', {'stationery': stationery})

    def post(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        stationery.delete()
        return redirect('academic_stationery_list')


@login_required
def academic_property_list(request):
    current_session = AcademicSession.objects.filter(current=True).first()
    properties = Property.objects.filter(session=current_session)
    return render(request, 'academic/property_list.html', {'properties': properties})

@login_required
def academic_property_detail(request, pk):
    property = get_object_or_404(Property, pk=pk)
    return render(request, 'academic/property_details.html', {'property': property})


class AcademicEventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = 'academic/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        queryset = super().get_queryset()

        # Get the current session and term
        current_session = AcademicSession.objects.get(current=True)
        current_term = AcademicTerm.objects.get(current=True)

        # Get the session and term from the request parameters, if available
        session_id = self.request.GET.get('session', current_session.id)
        term_id = self.request.GET.get('term', current_term.id)

        queryset = queryset.filter(session_id=session_id, term_id=term_id)

        # Modify the queryset to order events by the creation date
        queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_session = AcademicSession.objects.get(current=True)
        current_term = AcademicTerm.objects.get(current=True)

        selected_session_id = self.request.GET.get('session', current_session.id)
        selected_term_id = self.request.GET.get('term', current_term.id)

        selected_session = AcademicSession.objects.filter(id=selected_session_id).first()
        selected_term = AcademicTerm.objects.filter(id=selected_term_id).first()

        context['current_session'] = current_session
        context['current_term'] = current_term
        context['sessions'] = AcademicSession.objects.all()
        context['terms'] = AcademicTerm.objects.all()
        context['selected_session'] = selected_session
        context['selected_term'] = selected_term

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

def academicpick(request):
    return render(request, 'academic/result.html')

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType
from apps.students.models import Student
from .models import AcademicAnswer
from .forms import AcademicAnswerForm
from parents.models import ParentComments

@login_required
def academic_answer_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    current_session = AcademicSession.objects.get(current=True)
    current_term = AcademicTerm.objects.get(current=True)
    current_exam_type = ExamType.objects.get(current=True)

    answer, created = AcademicAnswer.objects.get_or_create(
        student=student,
        session=current_session,
        term=current_term,
        exam=current_exam_type
    )

    if request.method == 'POST':
        form = AcademicAnswerForm(request.POST, request.FILES, instance=answer)
        if form.is_valid():
            if 'audio_answer' in request.FILES:
                answer.audio_answer = request.FILES['audio_answer']
            form.save()
            messages.success(request, "Answer saved successfully.")
            return redirect('academic_answer_view', student_id=student.id)
        else:
            messages.error(request, "Error saving the answer.")
    else:
        form = AcademicAnswerForm(instance=answer)

    context = {
        'form': form,
        'student': student,
        'current_session': current_session,
        'current_term': current_term,
        'current_exam_type': current_exam_type,
        'answer': answer
    }
    return render(request, 'academic/academic_answer.html', context)

@login_required
def academic_parent_comments_view(request):
    session_id = request.GET.get('session_id')
    term_id = request.GET.get('term_id')
    exam_id = request.GET.get('exam_id')

    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()

    if session_id:
        current_session = get_object_or_404(AcademicSession, id=session_id)
    if term_id:
        current_term = get_object_or_404(AcademicTerm, id=term_id)
    if exam_id:
        current_exam = get_object_or_404(ExamType, id=exam_id)

    parent_comments = ParentComments.objects.filter(
        session=current_session,
        term=current_term,
        exam=current_exam
    ).select_related('student', 'parent')

    for comment in parent_comments:
        academic_answer = AcademicAnswer.objects.filter(
            session=comment.session,
            term=comment.term,
            exam=comment.exam,
            student=comment.student
        ).first()
        comment.academic_answer = academic_answer

    context = {
        'parent_comments': parent_comments,
        'current_session': current_session,
        'current_term': current_term,
        'current_exam': current_exam,
        'sessions': AcademicSession.objects.all(),
        'terms': AcademicTerm.objects.all(),
        'exams': ExamType.objects.all(),
        'academic_answer_form': AcademicAnswerForm(),
    }
    return render(request, 'academic/parent_comments.html', context)

@login_required
def mark_parent_comment_as_read(request, comment_id):
    comment = get_object_or_404(ParentComments, id=comment_id)
    comment.mark_comment = True
    comment.save()
    messages.success(request, "Comment marked as read.")
    return redirect('academic_parent_comments_view')

@login_required
def save_academic_answer(request):
    if request.method == "POST":
        comment_id = request.POST.get('comment_id')
        comment = get_object_or_404(ParentComments, id=comment_id)
        form = AcademicAnswerForm(request.POST, request.FILES)

        if form.is_valid():
            academic_answer, created = AcademicAnswer.objects.get_or_create(
                session=comment.session,
                term=comment.term,
                exam=comment.exam,
                student=comment.student,
            )
            academic_answer.answer = form.cleaned_data['answer']
            if 'audio_answer' in request.FILES:
                academic_answer.audio_answer = request.FILES['audio_answer']
            academic_answer.save()
            messages.success(request, "Academic answer saved successfully.")
        else:
            messages.error(request, "Error saving the academic answer.")
            print("Form errors:", form.errors)

        return redirect(reverse('academic_parent_comments_view') + f'?session_id={comment.session.id}&term_id={comment.term.id}&exam_id={comment.exam.id}')

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AcademicAnswer
from .forms import AcademicAnswerForm
from apps.students.models import Student

@login_required
def edit_academic_answer(request, answer_id):
    # Retrieve the academic answer object
    academic_answer = get_object_or_404(AcademicAnswer, id=answer_id)
    
    # Ensure the related student is an instance of the Student model
    if not isinstance(academic_answer.student, Student):
        raise ValueError("Expected a Student instance for academic_answer.student")
    
    if request.method == 'POST':
        form = AcademicAnswerForm(request.POST, request.FILES, instance=academic_answer)
        if form.is_valid():
            form.save()
            messages.success(request, 'The academic answer has been updated successfully.')
            # Redirect to the academic form status page
            return redirect('academic_form_status', class_id=academic_answer.student.current_class.id)
    else:
        form = AcademicAnswerForm(instance=academic_answer)

    return render(request, 'academic/edit_academic_answer.html', {'form': form, 'academic_answer': academic_answer})
