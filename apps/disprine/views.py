# apps/disprine/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import DisciplineIssue, Action
from apps.students.models import Student
from .forms import DisciplineIssueForm, ActionForm

def discipline_issue_list(request):
    students_with_issues = Student.objects.filter(disciplineissue__isnull=False).distinct()
    return render(request, 'disprine/discipline_issue_list.html', {'students': students_with_issues})

def discipline_issue_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    issues = DisciplineIssue.objects.filter(student=student).order_by('date_reported')
    return render(request, 'disprine/discipline_issue_detail.html', {'student': student, 'issues': issues})

def discipline_issue_create(request):
    if request.method == 'POST':
        form = DisciplineIssueForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Discipline issue reported successfully.')
            return redirect('discipline_issue_list')
    else:
        form = DisciplineIssueForm()
    return render(request, 'disprine/discipline_issue_form.html', {'form': form})

def discipline_issue_update(request, pk):
    issue = get_object_or_404(DisciplineIssue, pk=pk)
    if request.method == 'POST':
        form = DisciplineIssueForm(request.POST, request.FILES, instance=issue)
        if form.is_valid():
            form.save()
            messages.success(request, 'Discipline issue updated successfully.')
            return redirect('discipline_issue_detail', student_id=issue.student.id)
    else:
        form = DisciplineIssueForm(instance=issue)
    return render(request, 'disprine/discipline_issue_form.html', {'form': form})

def discipline_issue_delete(request, pk):
    issue = get_object_or_404(DisciplineIssue, pk=pk)
    student_id = issue.student.id
    issue.delete()
    messages.success(request, 'Discipline issue deleted successfully.')
    return redirect('discipline_issue_detail', student_id=student_id)

def action_create(request, issue_id):
    issue = get_object_or_404(DisciplineIssue, pk=issue_id)
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.save()
            messages.success(request, 'Action taken successfully.')
            return redirect('discipline_issue_detail', student_id=issue.student.id)
    else:
        form = ActionForm()
    return render(request, 'disprine/action_form.html', {'form': form, 'issue': issue})
