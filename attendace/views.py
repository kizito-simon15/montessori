from django.shortcuts import render, redirect
from .forms import AttendanceForm
from apps.corecode.models import StudentClass, AcademicSession, AcademicTerm
from apps.students.models import Student
from .models import Attendance
from django.shortcuts import render, get_object_or_404

def select_class(request):
    student_classes = StudentClass.objects.all()

    if request.method == 'POST':
        selected_class_id = request.POST.get('class')
        if selected_class_id:
            return redirect('take_attendance', class_id=selected_class_id)

    return render(request, 'select_class.html', {'student_classes': student_classes})

from django.shortcuts import render, redirect
from .models import Attendance
from .forms import AttendanceForm
from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from apps.students.models import Student

def take_attendance(request, class_id):
    student_class = StudentClass.objects.get(id=class_id)
    # Retrieve students and order them alphabetically by surname, firstname, and other_name
    students = Student.objects.filter(current_class=student_class).order_by('surname', 'firstname', 'middle_name')
    success = False
    saved_attendance = None

    # Default form
    initial_data = {
        'session': AcademicSession.objects.filter(current=True).first().id,
        'term': AcademicTerm.objects.filter(current=True).first().id,
    }
    form = AttendanceForm(initial=initial_data)

    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            session_id = form.cleaned_data['session'].id
            term_id = form.cleaned_data['term'].id
            attendance_date = form.cleaned_data['attendance_date']

            # Check if there's already attendance data for the given date
            saved_attendance = Attendance.objects.filter(class_group=student_class, attendance_date=attendance_date)

            # If there's existing data, we want to update it, otherwise, we create new records
            if saved_attendance.exists():
                # Update existing records
                for attendance in saved_attendance:
                    student_id = attendance.student_id
                    attendance.present = request.POST.get(f'present_{student_id}') == 'on'
                    attendance.absent = request.POST.get(f'absent_{student_id}') == 'on'
                    attendance.permission = request.POST.get(f'permission_{student_id}') == 'on'
                    attendance.save()
            else:
                # Save new attendance for each student
                for student in students:
                    present = request.POST.get(f'present_{student.id}') == 'on'
                    absent = request.POST.get(f'absent_{student.id}') == 'on'
                    permission = request.POST.get(f'permission_{student.id}') == 'on'

                    attendance = Attendance(
                        session_id=session_id,
                        term_id=term_id,
                        class_group=student_class,
                        student=student,
                        attendance_date=attendance_date,
                        present=present,
                        absent=absent,
                        permission=permission
                    )
                    attendance.save()

            success = True
            saved_attendance = Attendance.objects.filter(class_group=student_class, attendance_date=attendance_date)
            return redirect('select_class')

    elif request.method == 'GET' and 'attendance_date' in request.GET:
        form = AttendanceForm(request.GET)
        if form.is_valid():
            attendance_date = form.cleaned_data['attendance_date']
            saved_attendance = Attendance.objects.filter(class_group=student_class, attendance_date=attendance_date)
            success = saved_attendance.exists()
        if 'success' in request.GET:
            success = True

    return render(request, 'take_attendance.html', {
        'form': form,
        'student_class': student_class,
        'students': students,
        'success': success,
        'saved_attendance': saved_attendance,
    })



from django.shortcuts import render, redirect
from apps.corecode.models import StudentClass, AcademicSession, AcademicTerm
from .models import Attendance

def selecting_class(request):
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        if class_id:
            return redirect('class_attendance', class_id=class_id)  # Redirect to class_attendance view with class_id
        else:
            error_message = "Please select a class."
            classes = StudentClass.objects.all()
            return render(request, 'selecting_class.html', {'classes': classes, 'error_message': error_message})
    else:
        classes = StudentClass.objects.all()
        return render(request, 'selecting_class.html', {'classes': classes})

# views.py

def class_attendance(request, class_id):
    selected_class = StudentClass.objects.get(id=class_id)
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    
    if current_session and current_term:
        attendances = Attendance.objects.filter(
            class_group=selected_class,
            session=current_session,
            term=current_term
        ).values('attendance_date').distinct()
    else:
        attendances = []

    context = {
        'class_name': selected_class.name,
        'attendances': attendances,
        'current_session': current_session.name if current_session else 'No current session',
        'current_term': current_term.name if current_term else 'No current term',
        'selected_class': selected_class  # Ensure this is passed to the template
    }

    return render(request, 'class_attendance.html', context)

# views.py

# views.py

def view_attendance(request, class_id, attendance_date):
    selected_class = get_object_or_404(StudentClass, id=class_id)
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()

    attendances = Attendance.objects.filter(
        student__current_class=selected_class,
        attendance_date=attendance_date,
        session=current_session,
        term=current_term
    ).order_by('student__firstname', 'student__middle_name', 'student__surname')

    total_present = attendances.filter(present=True).count()
    total_absent = attendances.filter(absent=True).count()
    total_permission = attendances.filter(permission=True).count()

    context = {
        'attendance_date': attendance_date,
        'current_session': current_session.name if current_session else 'No current session',
        'current_term': current_term.name if current_term else 'No current term',
        'attendances': attendances,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_permission': total_permission,
    }

    return render(request, 'view_attendance.html', context)


# views.py

from django.shortcuts import render, get_object_or_404
from .models import StudentClass, Student, Attendance
from apps.corecode.models import AcademicSession, AcademicTerm

def pick_class(request):
    classes = StudentClass.objects.all()
    return render(request, 'pick_class.html', {'classes': classes})

from django.shortcuts import render, get_object_or_404
from .models import Student, StudentClass

def all_students(request, class_id):
    # Your view logic to retrieve students for the specified class
    selected_class = get_object_or_404(StudentClass, id=class_id)
    class_instance = StudentClass.objects.get(id=class_id)
    students = class_instance.student_set.all()
    
    context = {
        'selected_class': selected_class,
        'students': students,
        'class_id': class_id,
    }
    return render(request, 'all_students.html', context)



def single_student(request, class_id, student_id):
    selected_class = get_object_or_404(StudentClass, id=class_id)
    student = get_object_or_404(Student, id=student_id)
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()

    attendances = Attendance.objects.filter(
        student=student,
        session=current_session,
        term=current_term
    ).order_by('attendance_date')

    context = {
        'student': student,
        'current_session': current_session.name if current_session else 'No current session',
        'current_term': current_term.name if current_term else 'No current term',
        'attendances': attendances,
    }

    return render(request, 'single_student.html', context)


