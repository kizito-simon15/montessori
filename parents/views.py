from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.result.models import Result, StudentInfos
from apps.students.models import Student
from apps.finance.models import Invoice, InvoiceItem, Receipt
from accounts.models import ParentUser
from apps.corecode.models import AcademicSession, AcademicTerm, Installment, StudentClass, ExamType
from .models import ParentComments, StudentComments, InvoiceComments
from .forms import ParentCommentsForm, StudentCommentsForm, InvoiceCommentsForm
from academic.models import AcademicAnswer
from apps.finance.models import Uniform, UniformType, StudentUniform
from decimal import Decimal
from django.urls import reverse

def is_parent(user):
    return hasattr(user, 'parentuser')

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.result.models import Result
from apps.corecode.models import Subject
from apps.students.models import Student
from academic.models import AcademicAnswer
from accounts.models import ParentUser
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from django.db import models
import numpy as np

@login_required
def parent_dashboard(request):
    parent_user = get_object_or_404(ParentUser, id=request.user.id)
    student = Student.objects.filter(parentuser=parent_user).first()

    # Retrieve academic answers and other data
    academic_answers = AcademicAnswer.objects.filter(student=student, mark_comment=False)
    secretary_answers = SecretaryAnswers.objects.filter(student=student, mark_secretary_answer=False)
    bursor_answers = BursorAnswer.objects.filter(student=student, satisfied=False)

    # Overall Performance (Stem and Line Graph)
    overall_averages = Result.objects.filter(student=student).values(
        'session__name', 'term__name', 'exam__name'
    ).annotate(
        overall_avg=models.Avg('average')
    ).order_by('session__name', 'term__name', 'exam__name')

    labels = [f"{entry['session__name']} {entry['term__name']} {entry['exam__name']}" for entry in overall_averages]
    averages = [entry['overall_avg'] for entry in overall_averages]

    overall_analysis = ""
    stem_analysis = ""
    if averages:
        overall_trend = "increasing" if averages[-1] > averages[0] else "decreasing"
        estimated_next_avg = round(sum(averages[-3:]) / 3, 2) if len(averages) >= 3 else averages[-1]
        overall_grade = get_grade(estimated_next_avg)

        # Flexible feedback based on the estimated grade
        overall_advice = get_advice(overall_grade)

        overall_analysis = (
            f"The overall average is {'increasing' if overall_trend == 'increasing' else 'decreasing'}. "
            f"Estimated next overall average: {estimated_next_avg} (Grade {overall_grade}). {overall_advice}"
        )
        stem_analysis = (
            "Positive trend, keep up the good work!" if overall_trend == "increasing"
            else "Negative trend, take steps to improve consistency."
        )

    # Create Stem and Line Graph with Decorations
    plt.figure(figsize=(18, 10))
    plt.subplot(2, 1, 1)
    markerline, stemlines, baseline = plt.stem(labels, averages, basefmt=" ")
    plt.title('Student Overall Average Performance (Stem Graph)')
    plt.xlabel('Session-Term-Exam Type')
    plt.ylabel('Overall Average')
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Highlight the highest and lowest points with special markers
    max_idx = np.argmax(averages)
    min_idx = np.argmin(averages)
    plt.annotate('👑', xy=(labels[max_idx], averages[max_idx]), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='gold')
    plt.annotate('🌵', xy=(labels[min_idx], averages[min_idx]), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='brown')

    plt.subplot(2, 1, 2)
    plt.plot(labels, averages, marker='o', linestyle='-', color='b')
    plt.fill_between(range(len(averages)), averages, color='lightblue', alpha=0.4)
    plt.title('Student Overall Average Performance (Line Graph)')
    plt.xlabel('Session-Term-Exam Type')
    plt.ylabel('Overall Average')
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Highlight the highest and lowest points with special markers in the line graph
    plt.annotate('👑', xy=(labels[max_idx], averages[max_idx]), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='gold')
    plt.annotate('🌵', xy=(labels[min_idx], averages[min_idx]), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='brown')

    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    performance_graph = base64.b64encode(image_png).decode('utf-8')

    # Histogram for Subject Performance Analysis with Decorations
    subject_averages = Result.objects.filter(student=student).values(
        'subject__name'
    ).annotate(
        subject_avg=models.Avg('average')
    ).order_by('subject__name')

    subject_labels = [entry['subject__name'] for entry in subject_averages]
    subject_data = [entry['subject_avg'] for entry in subject_averages]

    subject_hist_analysis = ""
    if subject_data:
        highest_avg = max(subject_data)
        lowest_avg = min(subject_data)
        best_subject = subject_labels[subject_data.index(highest_avg)]
        worst_subject = subject_labels[subject_data.index(lowest_avg)]

        best_grade = get_grade(highest_avg)
        worst_grade = get_grade(lowest_avg)

        subject_hist_analysis = (
            f"Best subject: {best_subject} with an average of {highest_avg:.2f} (Grade {best_grade}). "
            f"Weakest subject: {worst_subject} with an average of {lowest_avg:.2f} (Grade {worst_grade}). "
            f"{get_advice(best_grade)} Ensure continuous effort to improve weaker subjects like {worst_subject}."
        )

    plt.figure(figsize=(12, 6))
    plt.bar(subject_labels, subject_data, color='skyblue')
    plt.title('Subject Performance Analysis')
    plt.xlabel('Subjects')
    plt.ylabel('Average Performance')
    plt.xticks(rotation=45, ha='right')

    # Highlight the highest and lowest points with special markers in the histogram
    plt.annotate('👑', xy=(best_subject, highest_avg), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='gold')
    plt.annotate('🌵', xy=(worst_subject, lowest_avg), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='brown')

    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    hist_image_png = buffer.getvalue()
    buffer.close()
    hist_graph = base64.b64encode(hist_image_png).decode('utf-8')

    # Individual Subject Histograms with Analysis and Decorations
    subject_graphs = {}
    subject_analyses = {}
    subjects = Subject.objects.all()

    for subject in subjects:
        subject_results = Result.objects.filter(student=student, subject=subject).values(
            'session__name', 'term__name', 'exam__name'
        ).annotate(
            subject_avg=models.Avg('average')
        ).order_by('session__name', 'term__name', 'exam__name')

        if subject_results.exists():
            subject_labels = [f"{entry['session__name']} {entry['term__name']} {entry['exam__name']}" for entry in subject_results]
            subject_averages = [entry['subject_avg'] for entry in subject_results]

            plt.figure(figsize=(12, 6))
            plt.bar(subject_labels, subject_averages, color='lightgreen')
            plt.plot(subject_labels, subject_averages, color='green', marker='o', linestyle='-')
            plt.title(f'Performance Variation in {subject.name}')
            plt.xlabel('Session-Term-Exam Type')
            plt.ylabel('Average Performance')
            plt.xticks(rotation=45, ha='right')

            # Highlight the highest and lowest points with special markers
            max_idx = np.argmax(subject_averages)
            min_idx = np.argmin(subject_averages)
            plt.annotate('👑', xy=(subject_labels[max_idx], subject_averages[max_idx]), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='gold')
            plt.annotate('🌵', xy=(subject_labels[min_idx], subject_averages[min_idx]), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=15, color='brown')

            plt.tight_layout()

            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            subject_image_png = buffer.getvalue()
            buffer.close()
            subject_graphs[subject.name] = base64.b64encode(subject_image_png).decode('utf-8')

            # Analysis for individual subject performance
            if subject_averages:
                trend = "increasing" if subject_averages[-1] > subject_averages[0] else "decreasing"
                estimated_next = round(sum(subject_averages[-3:]) / 3, 2) if len(subject_averages) >= 3 else subject_averages[-1]
                subject_grade = get_grade(estimated_next)
                advice = get_advice(subject_grade)

                subject_analyses[subject.name] = (
                    f"The performance in {subject.name} is {'improving' if trend == 'increasing' else 'declining'}. "
                    f"Estimated next average: {estimated_next} (Grade {subject_grade}). {advice}"
                )

    # Prepare a list of tuples to pass to the template
    subject_graphs_and_analyses = [
        (subject_name, subject_graphs[subject_name], subject_analyses[subject_name])
        for subject_name in subject_graphs
    ]

    context = {
        'student': student,
        'academic_answers_count': academic_answers.count(),
        'secretary_answers_count': len(secretary_answers),
        'bursor_answers_count': len(bursor_answers),
        'performance_graph': performance_graph,
        'overall_analysis': overall_analysis,
        'stem_analysis': stem_analysis,
        'hist_graph': hist_graph,
        'subject_hist_analysis': subject_hist_analysis,
        'subject_graphs_and_analyses': subject_graphs_and_analyses,
    }

    return render(request, 'parents/parent_dashboard.html', context)

def get_grade(score):
    """Return the grade based on the score."""
    if score >= 41:
        return "A"
    elif 31 <= score < 41:
        return "B"
    elif 25 <= score < 31:
        return "C"
    elif 15 <= score < 25:
        return "D"
    else:
        return "F"

def get_advice(grade):
    """Return advice based on the grade."""
    if grade == "A":
        return "Excellent work! Maintain your strategies to continue excelling."
    elif grade == "B":
        return "Good job! Keep pushing to reach the top level."
    elif grade == "C":
        return "You're doing okay, but there's room for improvement. Aim higher!"
    elif grade == "D":
        return "There's significant room for improvement. Focus on weaker areas and seek help if needed."
    else:
        return "Critical improvement needed. Consider revising strategies and seeking additional support."


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import StudentCommentsForm
from .models import StudentComments
from accounts.models import ParentUser
from apps.students.models import Student
from apps.finance.models import Invoice

@login_required
def parent_student_details(request, student_id):
    parent_user = get_object_or_404(ParentUser, id=request.user.id)
    student = get_object_or_404(Student, id=student_id)
    payments = Invoice.objects.filter(student=student)
    comments = StudentComments.objects.filter(student=student, parent=parent_user)

    if request.method == 'POST':
        form = StudentCommentsForm(request.POST, request.FILES)
        if form.is_valid():
            student_comment = form.save(commit=False)
            student_comment.student = student
            student_comment.parent = parent_user
            if 'audio_comment' in request.FILES:
                student_comment.audio_comment = request.FILES['audio_comment']
            student_comment.save()
            messages.success(request, 'Comments saved successfully.')
            return redirect('parent_student_details', student_id=student_id)
    else:
        form = StudentCommentsForm()

    context = {
        'student': student,
        'payments': payments,
        'comments': comments,
        'form': form,
    }
    return render(request, 'parents/parent_student_details.html', context)

@login_required
def update_details_comment(request, comment_id):
    comment = get_object_or_404(StudentComments, id=comment_id, parent=request.user)

    if request.method == 'POST':
        form = StudentCommentsForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Comments updated successfully.')
            return redirect('parent_student_details', student_id=comment.student.id)
    else:
        form = StudentCommentsForm(instance=comment)

    context = {
        'form': form,
        'comment': comment,
    }
    return render(request, 'parents/update_details_comment.html', context)

@login_required
def delete_details_comment(request, comment_id):
    comment = get_object_or_404(StudentComments, id=comment_id, parent=request.user)

    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted successfully.')
        return redirect('parent_student_details', student_id=comment.student.id)

    return render(request, 'parents/delete_details_comment.html', {'comment': comment})


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import ParentUser
from apps.students.models import Student
from apps.finance.models import Invoice
from apps.corecode.models import AcademicSession, Installment, StudentClass
from .models import InvoiceComments

@login_required
def parent_student_invoices(request):
    parent_user = get_object_or_404(ParentUser, id=request.user.id)
    student = parent_user.student
    invoices = Invoice.objects.filter(student=student).order_by('session', 'installment')
    sessions = AcademicSession.objects.all()
    installments = Installment.objects.all()
    classes = StudentClass.objects.all()

    if request.method == "POST":
        comments = request.POST.getlist('comments[]')
        audio_files = request.FILES.getlist('audio_comments[]')  # Allow multiple audio files
        invoice_id = request.POST.get('invoice_id')
        invoice = get_object_or_404(Invoice, id=invoice_id)

        # Save each comment and corresponding audio file
        for index, comment_text in enumerate(comments):
            audio_file = audio_files[index] if index < len(audio_files) else None
            # Save if there is a comment or an audio file
            if comment_text.strip() or audio_file:
                comment = InvoiceComments(
                    student=student,
                    invoice=invoice,
                    session=invoice.session,
                    installment=invoice.installment,
                    parent=parent_user,
                    comment=comment_text.strip() if comment_text.strip() else '',
                    audio_comment=audio_file
                )
                comment.save()

        messages.success(request, 'Comments and audio files successfully saved!')
        return redirect('parent_student_invoices')

    # Retrieve existing comments including audio files
    existing_comments = InvoiceComments.objects.filter(parent=parent_user, invoice__student=student).order_by('-id')

    context = {
        'student': student,
        'invoices': invoices,
        'sessions': sessions,
        'installments': installments,
        'classes': classes,
        'existing_comments': existing_comments,
    }
    return render(request, 'parents/parent_student_invoices.html', context)

@login_required
def update_invoice_comment(request, comment_id):
    comment = get_object_or_404(InvoiceComments, id=comment_id, parent=request.user)

    if request.method == 'POST':
        form = InvoiceCommentsForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Comment updated successfully.')
            return redirect('parent_student_invoices')
    else:
        form = InvoiceCommentsForm(instance=comment)

    context = {
        'form': form,
        'comment': comment,
    }
    return render(request, 'parents/update_invoice_comment.html', context)

@login_required
def delete_invoice_comment(request, comment_id):
    comment = get_object_or_404(InvoiceComments, id=comment_id, parent=request.user)

    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted successfully.')
        return redirect('parent_student_invoices')

    return render(request, 'parents/delete_invoice_comment.html', {'comment': comment})

@login_required
def parent_invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = InvoiceItem.objects.filter(invoice=invoice)
    receipts = Receipt.objects.filter(invoice=invoice)

    context = {
        'object': invoice,
        'items': items,
        'receipts': receipts
    }
    return render(request, 'parents/parent_invoice_detail.html', context)


from apps.corecode.models import Signature
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ParentCommentsForm
from itertools import groupby  # Add this import
from collections import defaultdict

@login_required
def parent_student_details_all(request):
    parent_user = get_object_or_404(ParentUser, id=request.user.id)
    student = parent_user.student

    # Get the Headmaster's signature
    headmaster_signature = Signature.objects.filter(name__iexact="Headmaster's signature").first()

    # Fetch data
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    exam_types = ExamType.objects.all()
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()

    organized_results = {}

    for session in sessions:
        organized_results[session] = {}
        for term in terms:
            organized_results[session][term] = {}
            for exam_type in exam_types:
                results = Result.objects.filter(student=student, session=session, term=term, exam=exam_type)
                if results.exists():
                    total_average = sum(result.average for result in results)
                    subject_count = results.count()
                    total_marks = subject_count * 50
                    overall_average = total_average / subject_count if subject_count else 0

                    # Determine overall grade
                    if overall_average >= 41:
                        overall_grade = 'A'
                    elif overall_average >= 30:
                        overall_grade = 'B'
                    elif overall_average >= 25:
                        overall_grade = 'C'
                    elif overall_average >= 15:
                        overall_grade = 'D'
                    else:
                        overall_grade = 'F'

                    # Calculate positions using tie-breaking logic
                    all_results = list(Result.objects.filter(
                        session=session, term=term, exam=exam_type, current_class=student.current_class
                    ).values('student').annotate(overall_avg=models.Avg('average')).order_by('-overall_avg'))

                    position_map = {}
                    current_position = 1
                    i = 0

                    while i < len(all_results):
                        tie_group = [all_results[i]]
                        j = i + 1
                        while j < len(all_results) and all_results[j]['overall_avg'] == all_results[i]['overall_avg']:
                            tie_group.append(all_results[j])
                            j += 1

                        # Calculate the average position for the tie group
                        if len(tie_group) > 1:
                            average_position = current_position + 0.5
                            for student_result in tie_group:
                                position_map[student_result['student']] = average_position
                        else:
                            position_map[all_results[i]['student']] = current_position

                        # Skip past the tie group
                        current_position += len(tie_group)
                        i = j

                    # Assign the position for the current student
                    position = position_map.get(student.id, None)

                    # Calculate total students for the session, term, and exam
                    total_students = Student.objects.filter(
                        current_class=student.current_class,
                        current_status="active",
                        completed=False,
                        result__session=session,
                        result__term=term,
                        result__exam=exam_type
                    ).distinct().count()

                    parent_comment = ParentComments.objects.filter(
                        student=student, parent=parent_user, session=session, term=term, exam=exam_type
                    ).first()

                    organized_results[session][term][exam_type] = {
                        'results': results,
                        'total_average': total_average,
                        'total_marks': total_marks,
                        'overall_average': overall_average,
                        'overall_grade': overall_grade,
                        'position': position,
                        'total_students': total_students,
                        'parent_comment': parent_comment,
                    }

    # Handle form submission for parent comments
    if request.method == "POST":
        form = ParentCommentsForm(request.POST, request.FILES)
        if form.is_valid():
            session = get_object_or_404(AcademicSession, id=request.POST.get('session'))
            term = get_object_or_404(AcademicTerm, id=request.POST.get('term'))
            exam = get_object_or_404(ExamType, id=request.POST.get('exam'))

            audio_file = request.FILES.get('audio_comment')

            parent_comment, created = ParentComments.objects.get_or_create(
                student=student,
                parent=parent_user,
                session=session,
                term=term,
                exam=exam,
                defaults={
                    'comment': form.cleaned_data['comment'],
                    'audio_comment': audio_file
                }
            )
            if not created:
                parent_comment.comment = form.cleaned_data['comment']
                parent_comment.audio_comment = audio_file if audio_file else parent_comment.audio_comment
                parent_comment.save()

            messages.success(request, "Your comment has been saved successfully.")
            return redirect('parent_student_details_all')
    else:
        form = ParentCommentsForm()

    context = {
        'student': student,
        'student_name': f"{student.firstname} {student.middle_name} {student.surname}",
        'registration_number': student.registration_number,
        'student_class': student.current_class,
        'organized_results': organized_results,
        'sessions': sessions,
        'terms': terms,
        'exam_types': exam_types,
        'current_session': current_session,
        'current_term': current_term,
        'current_exam': current_exam,
        'form': form,
        'headmaster_signature': headmaster_signature,
    }

    return render(request, 'parents/parent_student_details_all.html', context)

@login_required
def update_comment(request, comment_id):
    comment = get_object_or_404(InvoiceComments, id=comment_id)

    if request.method == "POST":
        form = InvoiceCommentsForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Comment successfully updated!')
            return redirect('parent_student_invoices')
    else:
        form = InvoiceCommentsForm(instance=comment)

    context = {
        'form': form,
        'comment': comment,
    }
    return render(request, 'parents/update_comment.html', context)


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(InvoiceComments, id=comment_id)
    comment.delete()
    messages.success(request, 'Comment successfully deleted!')
    return redirect('parent_student_invoices')


@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(ParentComments, id=comment_id, parent=request.user.parentuser)
    if request.method == 'POST':
        form = ParentCommentsForm(request.POST, request.FILES, instance=comment)
        if form.is_valid():
            # Handle updating the audio file if provided
            if 'audio_comment' in request.FILES:
                comment.audio_comment = request.FILES['audio_comment']
            form.save()
            messages.success(request, 'Your comment has been updated successfully.')
            return redirect('parent_student_details_all')
    else:
        form = ParentCommentsForm(instance=comment)

    return render(request, 'parents/edit_comment.html', {'form': form, 'comment': comment})

@login_required
def delete_result_comment(request, comment_id):
    comment = get_object_or_404(ParentComments, id=comment_id, parent=request.user.parentuser)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Your comment has been deleted successfully.')
        return redirect('parent_student_details_all')

    return render(request, 'parents/delete_comment.html', {'comment': comment})


@login_required
def edit_student_comment(request, comment_id):
    comment = get_object_or_404(StudentComments, id=comment_id)
    if request.method == 'POST':
        form = StudentCommentsForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Comment updated successfully.')
            return redirect('parent_student_details', student_id=comment.student.id)
    else:
        form = StudentCommentsForm(instance=comment)
    context = {
        'form': form,
        'comment': comment
    }
    return render(request, 'parents/edit_student_comment.html', context)


@login_required
def delete_student_comment(request, comment_id):
    comment = get_object_or_404(StudentComments, id=comment_id)
    student_id = comment.student.id
    comment.delete()
    messages.success(request, 'Comment deleted successfully.')
    return redirect('parent_student_details', student_id=student_id)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.students.models import Student
from academic.models import AcademicAnswer 
from secretary.models import SecretaryAnswers 
from bursor.models import BursorAnswer
from parents.models import ParentComments, StudentComments, InvoiceComments
from apps.corecode.models import AcademicSession

@login_required
def all_comments_view(request, student_id):
    parent_user = get_object_or_404(ParentUser, id=request.user.id)
    student = get_object_or_404(Student, id=student_id)
    current_session = AcademicSession.objects.filter(current=True).first()
    sessions = AcademicSession.objects.all()

    session_id = request.GET.get('session_id')
    if session_id:
        current_session = get_object_or_404(AcademicSession, id=session_id)

    parent_comments = ParentComments.objects.filter(student=student, session=current_session)
    student_comments = StudentComments.objects.filter(student=student)
    invoice_comments = InvoiceComments.objects.filter(student=student, session=current_session)

    # Mark all parent comments and associated academic answers as read
    for comment in parent_comments:
        if not comment.mark_comment:
            comment.mark_comment = True
            comment.save()
        academic_answer = AcademicAnswer.objects.filter(
            session=comment.session,
            term=comment.term,
            exam=comment.exam,
            student=comment.student
        ).first()
        if academic_answer and not academic_answer.mark_comment:
            academic_answer.mark_comment = True
            academic_answer.save()
        comment.academic_answer = academic_answer

    # Mark all student comments and associated secretary answers as read
    for comment in student_comments:
        if not comment.mark_student_comment:
            comment.mark_student_comment = True
            comment.save()
        secretary_answer = SecretaryAnswers.objects.filter(comment=comment).first()
        if secretary_answer and not secretary_answer.mark_secretary_answer:
            secretary_answer.mark_secretary_answer = True
            secretary_answer.save()
        comment.secretaryanswers = secretary_answer

    # Mark all invoice comments and associated bursor answers as read
    for comment in invoice_comments:
        if not comment.satisfied:
            comment.satisfied = True
            comment.save()
        bursor_answer = BursorAnswer.objects.filter(comment=comment).first()
        if bursor_answer and not bursor_answer.satisfied:
            bursor_answer.satisfied = True
            bursor_answer.save()
        comment.bursoranswer = bursor_answer

    context = {
        'student': student,
        'parent_comments': parent_comments,
        'student_comments': student_comments,
        'invoice_comments': invoice_comments,
        'sessions': sessions,
        'current_session': current_session,
    }
    return render(request, 'parents/all_comments.html', context)


"""
def all_parents_comments_view(request):
    student_comments = StudentComments.objects.all().order_by('-date_commented')
    invoice_comments = InvoiceComments.objects.all().order_by('-date_commented')
    parent_comments = ParentComments.objects.all().order_by('-date_commented')
    student_classes = StudentClass.objects.all()

    context = {
        'student_comments': student_comments,
        'invoice_comments': invoice_comments,
        'parent_comments': parent_comments,
        'student_classes' : student_classes
    }
    return render(request, 'parents/parent_comments.html', context)
"""

from bursor.models import BursorAnswer
from secretary.models import SecretaryAnswers

from bursor.models import BursorAnswer
from secretary.models import SecretaryAnswers

def all_parents_comments_view(request):
    student_comments = StudentComments.objects.all().order_by('-date_commented')
    invoice_comments = InvoiceComments.objects.all().order_by('-date_commented')
    parent_comments = ParentComments.objects.all().order_by('-date_commented')
    student_classes = StudentClass.objects.all()

    # Add logic to retrieve related answers
    for comment in parent_comments:
        academic_answer = AcademicAnswer.objects.filter(
            session=comment.session,
            term=comment.term,
            exam=comment.exam,
            student=comment.student
        ).first()
        comment.academic_answer = academic_answer

    for comment in invoice_comments:
        bursor_answer = BursorAnswer.objects.filter(
            student=comment.student,
            invoice=comment.invoice,
            session=comment.session,
            installment=comment.installment,
            parent=comment.parent
        ).first()
        comment.bursor_answer = bursor_answer

    for comment in student_comments:
        secretary_answer = SecretaryAnswers.objects.filter(
            student=comment.student,
            parent=comment.parent,
            comment=comment,
        ).first()
        comment.secretary_answer = secretary_answer

    context = {
        'student_comments': student_comments,
        'invoice_comments': invoice_comments,
        'parent_comments': parent_comments,
        'student_classes': student_classes,
    }
    return render(request, 'parents/parent_comments.html', context)

@login_required
def parent_uniform_list(request):
    # Get the parent user and associated student
    parent_user = get_object_or_404(ParentUser, id=request.user.id)
    student = parent_user.student

    # Get the current session or selected session
    current_session = AcademicSession.objects.filter(current=True).first()
    selected_session_id = request.GET.get('session', current_session.id)
    selected_session = AcademicSession.objects.get(id=selected_session_id)

    # Retrieve all uniforms associated with the student across all classes
    uniforms = Uniform.objects.filter(student=student, session=selected_session).order_by('student_class')

    uniform_data = {}

    for uniform in uniforms:
        student_class_name = uniform.student_class.name
        key = f"{student.id}_{student_class_name}"

        if key not in uniform_data:
            student_uniform = StudentUniform.objects.filter(
                student=student, session=selected_session, student_class=uniform.student_class
            ).first()
            
            total_paid = student_uniform.amount if student_uniform else Decimal('0.00')

            types_bought = []
            total_payable = Decimal('0.00')

            # Process each uniform item
            uniform_items = Uniform.objects.filter(
                student=student, session=selected_session, student_class=uniform.student_class
            )

            for item in uniform_items:
                payable = item.uniform_type.price * (2 if item.quantity == "Jozi 2" else 1)
                total_payable += payable

                types_bought.append({
                    'uniform_type': item.uniform_type.name,
                    'quantity': item.quantity,
                    'uniform_id': item.pk
                })

            balance = total_paid - total_payable

            uniform_data[key] = {
                'student': student,
                'student_class': student_class_name,
                'total_paid': total_paid,
                'total_payable': total_payable,
                'balance': balance,
                'types_bought': types_bought,
                'uniform_id': uniform.pk,
                'student_id': student.pk,
                'student_uniform_id': student_uniform.pk if student_uniform else None,
                'student_class_id': uniform.student_class.pk
            }

    return render(request, 'parents/uniform_list.html', {
        'uniform_data': uniform_data,
        'sessions': AcademicSession.objects.all(),
        'selected_session': selected_session,
        'student_classes': StudentClass.objects.filter(student__id=student.id).distinct(),  # All classes the student has been associated with
    })


@login_required
def mark_secretary_comment_as_read(request, comment_id):
    secretary_answer = get_object_or_404(SecretaryAnswers, id=comment_id)
    secretary_answer.mark_secretary_answer = True
    secretary_answer.save()
    return redirect(reverse('all_comments_view', args=[secretary_answer.comment.student.id]))

@login_required
def mark_academic_comment_as_read(request, comment_id):
    academic_answer = get_object_or_404(AcademicAnswer, id=comment_id)
    academic_answer.mark_comment = True
    academic_answer.save()
    return redirect(reverse('all_comments_view', args=[academic_answer.student.id]))

@login_required
def mark_invoice_comment_as_read(request, comment_id):
    bursor_answer = get_object_or_404(BursorAnswer, id=comment_id)
    bursor_answer.satisfied = True
    bursor_answer.save()
    return redirect(reverse('all_comments_view', args=[bursor_answer.student.id]))

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import ParentUser
from apps.students.models import Student

@login_required
def help_view(request):
    parent_user = get_object_or_404(ParentUser, id=request.user.id)
    student = Student.objects.filter(parentuser=parent_user).first()

    context = {
        'student': student,
        'user_guide': [
            {
                'title': 'Viewing Student Information',
                'description': 'To view the details of your child, click on the "Student Info" box on the main dashboard. This section provides personal details and academic history.',
            },
            {
                'title': 'Viewing Payment Information',
                'description': 'Click on the "Payments" box to see detailed information about payments made and those pending. This helps you keep track of tuition and other fees.',
            },
            {
                'title': 'Viewing Contributions',
                'description': 'Touch the "Contributions" box to view details about additional contributions made for school activities, such as field trips or special events.',
            },
            {
                'title': 'Checking Results',
                'description': 'Click on the "Results" box to view the academic results of your child. This section includes subject-wise scores and overall performance graphs.',
            },
            {
                'title': 'Reading and Responding to Comments',
                'description': 'Use the "Comments" section to read comments made by teachers, bursars, and secretaries. You can also check feedback or notes about your child\'s behavior, performance, or outstanding payments.',
            },
            {
                'title': 'Responding to Academic Comments',
                'description': 'When viewing academic comments, you can mark comments as read or provide feedback if needed. Ensure that you carefully review each comment to stay updated on your child’s academic progress.',
            },
            {
                'title': 'Viewing Bursar Comments',
                'description': 'Bursar comments relate to financial matters such as fees and payments. If there are questions or clarifications needed, follow up with the bursar directly or through the provided communication link.',
            },
            {
                'title': 'Reviewing Secretary Comments',
                'description': 'Secretary comments may include updates on school policies or administrative notices. Make sure to read these comments to stay informed about school rules and deadlines.',
            },
            {
                'title': 'Saving and Responding to Comments',
                'description': 'To save comments or mark them as seen, click the appropriate button next to the comment. This action indicates that you have read the comment. You may also reply if the system allows for responses.',
            },
            {
                'title': 'Navigation Tips',
                'description': 'Use the navigation bar at the top to move between different sections easily. Each section provides specific details, so ensure you explore them regularly to stay updated.',
            },
            {
                'title': 'Accessing the Help Guide',
                'description': 'If you need further assistance or clarification, click on the "Help" box located on your dashboard. This guide provides step-by-step instructions for using the system efficiently.',
            },
        ],
    }
    return render(request, 'parents/help_view.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import InvoiceComments
from .forms import InvoiceCommentsForm
from apps.finance.models import Invoice

@login_required
def update_invoice_comment(request, comment_id):
    # Fetch the existing comment
    invoice_comment = get_object_or_404(InvoiceComments, id=comment_id, parent=request.user)

    if request.method == 'POST':
        form = InvoiceCommentsForm(request.POST, request.FILES, instance=invoice_comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your comment has been successfully updated.')
            return redirect('parent_student_invoices')
        else:
            messages.error(request, 'There was an error updating your comment. Please try again.')
    else:
        form = InvoiceCommentsForm(instance=invoice_comment)

    context = {
        'form': form,
        'invoice_comment': invoice_comment,
    }
    return render(request, 'parents/update_previous_invoice_comment.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import StudentComments
from .forms import StudentCommentsForm
from django.contrib.auth.decorators import login_required

@login_required
def update_student_comment(request, comment_id):
    student_comment = get_object_or_404(StudentComments, id=comment_id, parent=request.user)
    if request.method == 'POST':
        form = StudentCommentsForm(request.POST, request.FILES, instance=student_comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student comment updated successfully.')
            return redirect('parent_student_details', student_comment.student.id)
        else:
            messages.error(request, 'There was an error updating the student comment.')
    else:
        form = StudentCommentsForm(instance=student_comment)
    
    return render(request, 'parents/update_previous_student_comment.html', {
        'form': form,
        'student_comment': student_comment,
    })

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from .models import StudentComments

def delete_text_comment(request, comment_id):
    comment = get_object_or_404(StudentComments, id=comment_id)
    if comment.comment:
        comment.comment = None
        comment.save()
        messages.success(request, "Text comment deleted successfully.")
    else:
        messages.warning(request, "No text comment to delete.")
    return redirect(reverse('update_student_comment', args=[comment_id]))

def delete_audio_comment(request, comment_id):
    comment = get_object_or_404(StudentComments, id=comment_id)
    if comment.audio_comment:
        comment.audio_comment.delete()
        comment.audio_comment = None
        comment.save()
        messages.success(request, "Audio comment deleted successfully.")
    else:
        messages.warning(request, "No audio comment to delete.")
    return redirect(reverse('update_student_comment', args=[comment_id]))
