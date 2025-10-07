from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .forms import MoveStudentsForm, DeleteStudentsForm
from apps.students.models import Student
from django.shortcuts import render, redirect
from .forms import MoveStudentsForm, DeleteStudentsForm
from apps.students.models import Student
from django.shortcuts import render, redirect
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import CopyResultsForm
from apps.result.models import Result
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

@login_required
def move_students(request):
    if request.method == 'POST':
        form = MoveStudentsForm(request.POST)
        if form.is_valid():
            from_class_id = form.cleaned_data['from_class'].id
            to_class_id = form.cleaned_data['to_class'].id
            # Move students from one class to another
            Student.objects.filter(current_class_id=from_class_id).update(current_class_id=to_class_id)
            return redirect('move_students_success')
    else:
        form = MoveStudentsForm()
    return render(request, 'move_students.html', {'form': form})

@login_required
def delete_students(request):
    if request.method == 'POST':
        form = DeleteStudentsForm(request.POST)
        if form.is_valid():
            class_id = form.cleaned_data['class_to_delete'].id
            # Delete students from the given class
            Student.objects.filter(current_class_id=class_id).delete()
            return redirect('delete_students_success')
    else:
        form = DeleteStudentsForm()
    return render(request, 'delete_students.html', {'form': form})

@login_required
def move_students_success(request):
    return render(request, 'move_students_success.html')

@login_required
def delete_students_success(request):
    return render(request, 'delete_students_success.html')


@login_required
def copy_results(request):
    if request.method == 'POST':
        form = CopyResultsForm(request.POST)
        if form.is_valid():
            source_session = form.cleaned_data['source_session']
            source_term = form.cleaned_data['source_term']
            source_exam_type = form.cleaned_data['source_exam_type']
            destination_session = form.cleaned_data['destination_session']
            destination_term = form.cleaned_data['destination_term']
            destination_exam_type = form.cleaned_data['destination_exam_type']

            # Copy results from source to destination
            try:
                results_to_copy = Result.objects.filter(
                    session=source_session,
                    term=source_term,
                    exam=source_exam_type
                )

                copied_results = []
                for result in results_to_copy:
                    copied_result = Result(
                        session=destination_session,
                        term=destination_term,
                        exam=destination_exam_type,
                        current_class=result.current_class,
                        subject=result.subject,
                        student=result.student,
                        test_score=result.test_score,
                        exam_score=result.exam_score
                    )
                    copied_results.append(copied_result)

                Result.objects.bulk_create(copied_results)

                messages.success(request, 'Results copied successfully.')
                return redirect('copy_results')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
    else:
        form = CopyResultsForm()

    return render(request, 'copy_results.html', {'form': form})



@login_required
def delete_results(request):
    # Fetch all available sessions, terms, and exam types for rendering in the form
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    exams = ExamType.objects.all()

    # Get the current session, term, and exam type
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()

    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        term_id = request.POST.get('term_id')
        exam_id = request.POST.get('exam_id')

        # Check if session, term, and exam type IDs are provided
        if session_id and term_id and exam_id:
            try:
                # Get the session, term, and exam type objects
                session_obj = AcademicSession.objects.get(id=session_id)
                term_obj = AcademicTerm.objects.get(id=term_id)
                exam_obj = ExamType.objects.get(id=exam_id)

                # Delete results for the specified session, term, and exam type
                Result.objects.filter(session=session_obj, term=term_obj, exam=exam_obj).delete()

                messages.success(request, 'Results deleted successfully.')
            except (AcademicSession.DoesNotExist, AcademicTerm.DoesNotExist, ExamType.DoesNotExist):
                messages.error(request, 'Invalid session, term, or exam type.')
        else:
            messages.error(request, 'Session, term, and exam type IDs are required.')

        return redirect('edit-results')

    return render(request, 'delete_results.html', {
        'sessions': sessions,
        'terms': terms,
        'exams': exams,
        'current_session': current_session,
        'current_term': current_term,
        'current_exam': current_exam,
    })

