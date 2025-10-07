from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import DetailView, ListView, View, TemplateView
from django.db.models import Sum, Avg, Count, Q, Case, When, Value, IntegerField
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.forms import formset_factory, modelformset_factory
from decimal import Decimal
import logging
from collections import defaultdict
from itertools import groupby
import math

from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, SiteConfig, StudentClass, Subject, Signature
from apps.students.models import Student
from apps.result.models import Result, StudentInfos
from apps.result.forms import (
    ClassSelectionForm, SessionTermExamSubjectForm, ResultEntryForm, StudentInfosForm,
    CreateResults, EditResults, ViewResultsForm, ViewResultsFormSet
)

logger = logging.getLogger(__name__)

# View to create results for students
@login_required
@permission_required('result.add_result', raise_exception=True)
def create_result(request):
    students = Student.objects.filter(current_status__iexact="active", completed=False)
    logger.debug(f"Active students count: {students.count()}")
    for student in students:
        logger.debug(f"Student: {student}, Class: {student.current_class}, Gender: {student.gender}")
    
    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()
    if not current_session or not current_term or not current_exam:
        messages.warning(request, "Please ensure an Academic Session, Term, and Exam Type are set as current.")
        return render(request, "result/create_result.html", {"students": students, "students_by_class": {}})
    
    request.session['current_session'] = current_session.id if current_session else None
    request.session['current_term'] = current_term.id if current_term else None
    request.session['current_exam'] = current_exam.id if current_exam else None
    
    if not StudentClass.objects.exists():
        messages.warning(request, "No student classes found. Please create a class first.")
        return render(request, "result/create_result.html", {"students": students, "students_by_class": {}})
    if not students.exists():
        messages.warning(request, "No active, non-completed students found. Please add or update students.")
        return render(request, "result/create_result.html", {"students": students, "students_by_class": {}})
    
    try:
        students = students.annotate(
            gender_order=Case(
                When(gender="female", then=Value(0)),
                When(gender="male", then=Value(1)),
                default=Value(2),
                output_field=IntegerField()
            )
        ).order_by('gender_order', 'firstname', 'surname')
    except Exception as e:
        logger.error(f"Failed to sort students by gender: {e}")
        students = students.order_by('firstname', 'surname')
    
    students_by_class = defaultdict(list)
    students_without_class = []
    for student in students:
        if student.current_class:
            students_by_class[student.current_class].append(student)
        else:
            students_without_class.append(student)
    
    if students_without_class:
        logger.debug(f"Students without class: {students_without_class}")
        messages.info(request, f"{len(students_without_class)} student(s) lack a current class and are not displayed.")
    if not students_by_class:
        messages.warning(request, "All students lack a current class. Please assign classes to students.")
        return render(request, "result/create_result.html", {"students": students, "students_by_class": {}})
    
    if request.method == "POST":
        if "finish" in request.POST:
            form = CreateResults(request.POST)
            if form.is_valid():
                subjects = form.cleaned_data["subjects"]
                session = form.cleaned_data["session"]
                term = form.cleaned_data["term"]
                exam = form.cleaned_data["exam"]
                students_str = request.POST.get("students")
                if students_str:
                    results = []
                    for student_id in students_str.split(","):
                        stu = Student.objects.get(pk=student_id)
                        if stu.current_class:
                            for subject in subjects:
                                check = Result.objects.filter(
                                    session=session,
                                    term=term,
                                    exam=exam,
                                    current_class=stu.current_class,
                                    subject=subject,
                                    student=stu,
                                ).first()
                                if not check:
                                    results.append(
                                        Result(
                                            session=session,
                                            term=term,
                                            exam=exam,
                                            current_class=stu.current_class,
                                            subject=subject,
                                            student=stu,
                                        )
                                    )
                    Result.objects.bulk_create(results)
                    request.session['selected_students'] = students_str
                    selected_student_names = ', '.join([
                        f"{Student.objects.get(pk=sid).firstname} "
                        f"{Student.objects.get(pk=sid).middle_name} "
                        f"{Student.objects.get(pk=sid).surname}"
                        for sid in students_str.split(",")
                    ])
                    request.session['selected_student_name'] = selected_student_names
                    return redirect("edit-results")
                else:
                    messages.warning(request, "You didn't select any student.")
            return render(request, "result/create_result.html", {"students": students, "students_by_class": dict(students_by_class)})
        else:
            id_list = request.POST.getlist("students")
            if id_list:
                request.session['selected_students'] = ','.join(id_list)
                form = CreateResults(
                    initial={
                        "session": request.session.get('current_session'),
                        "term": request.session.get('current_term'),
                        "exam": request.session.get('current_exam'),
                    }
                )
                studentlist = ",".join(id_list)
                return render(
                    request,
                    "result/create_result_page2.html",
                    {"students": studentlist, "form": form, "count": len(id_list), "students_by_class": students_by_class},
                )
            else:
                messages.warning(request, "You didn't select any student.")
                return render(request, "result/create_result.html", {"students": students, "students_by_class": dict(students_by_class)})
    return render(request, "result/create_result.html", {"students": students, "students_by_class": dict(students_by_class)})

# View to edit results
@login_required
@permission_required('result.change_result', raise_exception=True)
def edit_results(request):
    logger.debug("Entering the edit_results view")
    student_classes = StudentClass.objects.all()
    subjects = Subject.objects.all()
    logger.debug("Fetched student classes and subjects: %s, %s", student_classes, subjects)
    
    if request.method == "POST":
        logger.debug("Handling POST request")
        formset = EditResults(request.POST)
        if formset.is_valid():
            logger.debug("Formset is valid. Processing forms...")
            for form in formset:
                if form.cleaned_data.get('DELETE', False):
                    logger.debug("Processing deletion for form: %s", form.instance)
                    instance = form.instance
                    if instance.pk:
                        instance.delete()
                        logger.debug("Deleted instance: %s", instance)
                else:
                    instance = form.save(commit=False)
                    logger.debug("Saving instance: %s", instance)
                    instance.save()
            messages.success(request, "Results successfully updated.")
            return redirect("edit-results")
        else:
            logger.error("Formset is invalid. Errors: %s", formset.errors)
            messages.error(request, "There was an error updating the results. Please fix the errors and try again.")
    else:
        logger.debug("Handling GET request")
        class_select = request.GET.get('class_select')
        subject_select = request.GET.get('subject_select')
        student_name = request.GET.get('student_name', '').strip()  # Strip whitespace
        logger.debug("Filters: class_select=%s, subject_select=%s, student_name=%s", class_select, subject_select, student_name)
        
        current_session = request.session.get('current_session')
        current_term = request.session.get('current_term')
        current_exam = request.session.get('current_exam')
        if not all([current_session, current_term, current_exam]):
            messages.warning(request, "Session, term, or exam not set in session. Please create results first.")
            return redirect("create-result")
        
        results = Result.objects.filter(
            session_id=current_session,
            term_id=current_term,
            exam_id=current_exam
        )
        if class_select:
            results = results.filter(current_class_id=class_select)
            logger.debug("Filtered results by class_select: %s", results)
        if subject_select:
            results = results.filter(subject_id=subject_select)
            logger.debug("Filtered results by subject_select: %s", results)
        if student_name:
            name_parts = student_name.split()
            query = Q()
            for part in name_parts:
                query |= Q(student__firstname__icontains=part)
                query |= Q(student__middle_name__icontains=part)
                query |= Q(student__surname__icontains=part)
            results = results.filter(query)
            logger.debug("Filtered results by student_name: %s", results)
        
        formset = EditResults(queryset=results)
        logger.debug("Created formset with queryset: %s", results)
        return render(request, "result/edit_results.html", {
            "formset": formset,
            "student_classes": student_classes,
            "subjects": subjects
        })

# View to edit results immediately
@login_required
@permission_required('result.change_result', raise_exception=True)
def edit_now_results(request):
    if request.method == 'POST':
        result_ids = request.POST.getlist('result_ids')
        for result_id in result_ids:
            result = get_object_or_404(Result, id=result_id)
            form = ResultEntryForm(request.POST, instance=result, prefix=f'result_{result_id}')
            if form.is_valid():
                form.save()
        messages.success(request, 'Results updated successfully.')
        return redirect('edit-results')
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
        return render(request, 'result/edit_now_results.html', context)

# View to delete results
@login_required
@permission_required('result.delete_result', raise_exception=True)  # Corrected permission name
def delete_page_results(request):
    if request.method == "POST":
        class_select = request.POST.get('class_select')
        subject_select = request.POST.get('subject_select')
        student_name = request.POST.get('student_name')
        results = Result.objects.filter(
            session_id=request.session.get('current_session'),
            term_id=request.session.get('current_term'),
            exam_id=request.session.get('current_exam')
        )
        if class_select:
            results = results.filter(current_class_id=class_select)
        if subject_select:
            results = results.filter(subject_id=subject_select)
        if student_name:
            results = results.filter(
                Q(student__firstname__icontains=student_name) |
                Q(student__surname__icontains=student_name) |
                Q(student__middle_name__icontains=student_name)
            )
        count, _ = results.delete()
        messages.success(request, f"Deleted {count} results successfully.")
        return redirect("edit-results")
    else:
        class_select = request.GET.get('class_select')
        subject_select = request.GET.get('subject_select')
        student_name = request.GET.get('student_name')
        context = {
            'class_select': class_select,
            'subject_select': subject_select,
            'student_name': student_name,
        }
        return render(request, 'result/confirm_delete_page_results.html', context)

class StudentResultsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'result/student_results.html'
    permission_required = "result.view_result"

    def get(self, request, student_id=None):
        if student_id:
            student = get_object_or_404(Student, pk=student_id)
        else:
            return redirect('student-selection')  # Redirect to a student selection page if no ID
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_exam = ExamType.objects.filter(current=True).first()
        student_info = student.studentinfos_set.filter(
            session=current_session,
            term=current_term,
            exam=current_exam
        ).last()
        form = StudentInfosForm(instance=student_info)
        return render(request, self.template_name, {
            'form': form,
            'session': current_session,
            'term': current_term,
            'exam_type': current_exam,
            'student_class': student.current_class,
            'student': student,
        })

    def post(self, request, student_id):
        student = get_object_or_404(Student, pk=student_id)
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_exam = ExamType.objects.filter(current=True).first()
        form = StudentInfosForm(request.POST)
        if form.is_valid():
            student_info = form.save(commit=False)
            student_info.student = student
            student_info.session = current_session
            student_info.term = current_term
            student_info.exam = current_exam
            student_info.save()
            messages.success(request, 'The student information has been saved successfully.')
            return redirect('student-results', student_id=student_id)
        return render(request, self.template_name, {
            'form': form,
            'session': current_session,
            'term': current_term,
            'exam_type': current_exam,
            'student_class': student.current_class,
            'student': student,
        })

class FormStatusView(LoginRequiredMixin, View):
    template_name = 'result/form_status.html'

    def calculate_overall_grade(self, overall_average):
        if overall_average is None:
            return "No results available"
        if overall_average >= 81:
            return "A"
        elif 75 <= overall_average < 81:
            return "B"
        elif 65 <= overall_average < 75:
            return "C"
        elif 55 <= overall_average < 65:
            return "D"
        else:
            return "F"

    def calculate_overall_total_marks(self, valid_results):
        return len(valid_results) * 100

    def get_total_active_students(self, class_id, current_session, current_term, current_exam_type):
        return Student.objects.filter(
            result__current_class_id=class_id,
            result__session_id=current_session,
            result__term_id=current_term,
            result__exam_id=current_exam_type,
            current_status="active",
            completed=False
        ).distinct().count()

    def get(self, request, class_id=None):
        if not class_id:
            return redirect('class-list')  # Redirect to class list if no class_id
        student_class = get_object_or_404(StudentClass, pk=class_id)
        current_session = request.GET.get('session', AcademicSession.objects.filter(current=True).first().id)
        current_term = request.GET.get('term', AcademicTerm.objects.filter(current=True).first().id)
        current_exam_type = request.GET.get('exam', ExamType.objects.filter(current=True).first().id)
        sessions = AcademicSession.objects.all()
        terms = AcademicTerm.objects.all()
        exams = ExamType.objects.all()
        total_active_students = self.get_total_active_students(class_id, current_session, current_term, current_exam_type)
        students_with_forms = Student.objects.filter(
            result__current_class=student_class,
            result__session_id=current_session,
            result__term_id=current_term,
            result__exam_id=current_exam_type
        ).distinct()
        query = request.GET.get('q')
        if query:
            students_with_forms = students_with_forms.filter(
                Q(firstname__icontains=query) | Q(middle_name__icontains=query) |
                Q(surname__icontains=query)
            )
        no_forms = not students_with_forms.exists()
        completed_forms_count = 0
        for student in students_with_forms:
            last_student_info = student.studentinfos_set.last()
            if last_student_info and last_student_info.head_comments:
                completed_forms_count += 1
        student_results = []
        for student in students_with_forms:
            student_results_queryset = student.result_set.filter(
                current_class=student_class,
                session_id=current_session,
                term_id=current_term,
                exam_id=current_exam_type
            )
            valid_results = student_results_queryset.exclude(
                test_score__isnull=True, exam_score__isnull=True
            )
            if not valid_results.exists():
                continue
            total_average = valid_results.aggregate(Sum('average'))['average__sum'] or 0
            overall_average = valid_results.aggregate(Avg('average'))['average__avg']
            overall_grade = self.calculate_overall_grade(overall_average)
            overall_total_marks = self.calculate_overall_total_marks(valid_results)
            student_results.append({
                'student': student,
                'total_average': total_average,
                'overall_average': overall_average,
                'overall_grade': overall_grade,
                'overall_total_marks': overall_total_marks,
                'results': valid_results,
                'position': None
            })
        sorted_results = sorted(
            student_results,
            key=lambda x: x['overall_average'] or 0,
            reverse=True
        )
        current_position = 1
        i = 0
        while i < len(sorted_results):
            tie_group = [sorted_results[i]]
            j = i + 1
            while j < len(sorted_results) and sorted_results[j]['overall_average'] == sorted_results[i]['overall_average']:
                tie_group.append(sorted_results[j])
                j += 1
            if len(tie_group) > 1:
                average_position = current_position + 0.5
                for result in tie_group:
                    result['position'] = average_position
            else:
                tie_group[0]['position'] = current_position
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
            'total_active_students': total_active_students,
            'headmaster_signature': headmaster_signature,
        })

class ClassResultsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'result/class_results.html'
    permission_required = "result.view_result"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        if not class_id:
            return redirect('class-list')  # Redirect if no class_id
        selected_class = get_object_or_404(StudentClass, pk=class_id)
        session_id = self.request.GET.get('session')
        term_id = self.request.GET.get('term')
        exam_id = self.request.GET.get('exam')
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
        results = Result.objects.filter(
            current_class=selected_class,
            session=session,
            term=term,
            exam=exam
        ).select_related('student')
        if not results.exists():
            context['no_results'] = True
            return context
        context['no_results'] = False
        data = []
        subjects = set()
        student_results_map = defaultdict(list)
        for result in results:
            student_results_map[result.student].append(result)
        for student, student_results in student_results_map.items():
            student_data = {
                'student': student,
                'student_class': selected_class,
                'subjects': {}
            }
            total_marks = 0
            valid_subject_count = 0
            for res in student_results:
                if res.test_score is not None or res.exam_score is not None:
                    total_marks += res.average
                    valid_subject_count += 1
            total_marks = math.ceil(total_marks) if total_marks % 1 >= 0.5 else math.floor(total_marks)
            overall_average = total_marks / valid_subject_count if valid_subject_count > 0 else 0
            overall_status = "PASS" if overall_average >= 50 else "FAIL"
            student_data['total'] = total_marks
            student_data['overall_average'] = overall_average
            student_data['overall_status'] = overall_status
            for result in student_results:
                subjects.add(result.subject.name)
                subject_average = math.floor(result.average) if (result.test_score is not None or result.exam_score is not None) else None
                student_data['subjects'][result.subject.name] = {
                    'average': subject_average
                }
            data.append(student_data)
        sorted_data = sorted(data, key=lambda x: x['overall_average'], reverse=True)
        current_position = 1
        i = 0
        while i < len(sorted_data):
            tie_group = [sorted_data[i]]
            j = i + 1
            while j < len(sorted_data) and sorted_data[j]['overall_average'] == sorted_data[i]['overall_average']:
                tie_group.append(sorted_data[j])
                j += 1
            if len(tie_group) > 1:
                average_position = current_position + 0.5
                for student_data in tie_group:
                    student_data['position'] = average_position
            else:
                tie_group[0]['position'] = current_position
            current_position += len(tie_group)
            i = j
        context['data'] = sorted_data
        context['subjects'] = sorted(subjects)
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
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        total_average = results.aggregate(total_average=Sum('average'))['total_average'] or 0
        count = results.count()
        return math.floor(total_average / count) if count else None

    def calculate_subject_grade(self, subject_average):
        if subject_average is None:
            return "-"
        if subject_average >= 81:
            return "A"
        elif 75 <= subject_average < 81:
            return "B"
        elif 65 <= subject_average < 75:
            return "C"
        elif 55 <= subject_average < 65:
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
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        count = results.count()
        if count == 0:
            return 0.00
        total_average = results.aggregate(total_average=Sum('average'))['total_average'] or Decimal(0)
        subject_average = total_average / count
        max_score = Decimal(100)
        gpa = (subject_average / max_score) * Decimal(4.0)
        return round(gpa, 2)

class ClassListView(View):
    def get(self, request):
        classes = StudentClass.objects.all()
        context = {'classes': classes}
        return render(request, 'result/class_list.html', context)

    def post(self, request):
        class_id = request.POST.get('class_id')
        if class_id:
            return redirect('class-results', class_id=class_id)
        return redirect('class-list')

class SingleClassResultsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'result/single_class_results.html'
    permission_required = "result.view_result"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        if not class_id:
            return redirect('single-class')  # Redirect if no class_id
        selected_class = get_object_or_404(StudentClass, pk=class_id)
        session_id = self.request.GET.get('session')
        term_id = self.request.GET.get('term')
        exam_id = self.request.GET.get('exam')
        session = AcademicSession.objects.get(id=session_id) if session_id else AcademicSession.objects.get(current=True)
        term = AcademicTerm.objects.get(id=term_id) if term_id else AcademicTerm.objects.get(current=True)
        exam = ExamType.objects.get(id=exam_id) if exam_id else ExamType.objects.get(current=True)
        context['class_id'] = class_id
        context['selected_class'] = selected_class
        context['sessions'] = AcademicSession.objects.all()
        context['terms'] = AcademicTerm.objects.all()
        context['exams'] = ExamType.objects.all()  # Corrected to ExamType
        context['current_session'] = session
        context['current_term'] = term
        context['current_exam'] = exam
        results = Result.objects.filter(
            current_class=selected_class,
            session=session,
            term=term,
            exam=exam
        ).select_related('student')
        if not results.exists():
            context['no_results'] = True
            return context
        context['no_results'] = False
        data = []
        subjects = set()
        student_results_map = defaultdict(list)
        for result in results:
            student_results_map[result.student].append(result)
        for student, student_results in student_results_map.items():
            student_data = {
                'student': student,
                'student_class': selected_class,
                'subjects': {}
            }
            total_marks = sum(res.average for res in student_results)
            overall_average = total_marks / len(student_results) if student_results else 0
            overall_status = "PASS" if overall_average >= 50 else "FAIL"
            student_data['total'] = total_marks
            student_data['overall_average'] = overall_average
            student_data['overall_status'] = overall_status
            for result in student_results:
                subjects.add(result.subject.name)
                student_data['subjects'][result.subject.name] = {
                    'test_score': result.test_score,
                    'exam_score': result.exam_score,
                    'average': result.average
                }
            data.append(student_data)
        sorted_data = sorted(data, key=lambda x: x['overall_average'], reverse=True)
        current_position = 1
        i = 0
        while i < len(sorted_data):
            tie_group = [sorted_data[i]]
            j = i + 1
            while j < len(sorted_data) and sorted_data[j]['overall_average'] == sorted_data[i]['overall_average']:
                tie_group.append(sorted_data[j])
                j += 1
            if len(tie_group) > 1:
                average_position = current_position + 0.5
                for student_data in tie_group:
                    student_data['position'] = average_position
            else:
                tie_group[0]['position'] = current_position
            current_position += len(tie_group)
            i = j
        context['data'] = sorted_data
        context['subjects'] = sorted(subjects)
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
        return round(total_average / count, 2) if count else 0.00

    def calculate_subject_grade(self, subject_average):
        if subject_average >= 81:
            return "A"
        elif 75 <= subject_average < 81:
            return "B"
        elif 65 <= subject_average < 75:
            return "C"
        elif 55 <= subject_average < 65:
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
        max_score = Decimal(100)
        gpa = (subject_average / max_score) * Decimal(4.0)
        return round(gpa, 2)

class SingleClassListView(View):
    def get(self, request):
        classes = StudentClass.objects.all()
        context = {'classes': classes}
        return render(request, 'result/single_class_list.html', context)

    def post(self, request):
        class_id = request.POST.get('class_id')
        if class_id:
            return redirect('single-results', class_id=class_id)
        return redirect('single-class')

class SingleStudentResultsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'result/single_student_results.html'
    permission_required = 'result.view_single_student_results'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = kwargs.get('student_id')
        if not student_id:
            return redirect('student-selection')  # Redirect if no student_id
        student = get_object_or_404(Student, pk=student_id)
        current_session = AcademicSession.objects.get(current=True)
        current_term = AcademicTerm.objects.get(current=True)
        current_exam = ExamType.objects.get(current=True)
        student_results = Result.objects.filter(
            student_id=student_id,
            session=current_session,
            term=current_term,
            exam=current_exam
        )
        context['student_name'] = f"{student.firstname} {student.middle_name} {student.surname}"
        subjects = {}
        for result in student_results:
            subject_name = result.subject.name
            if subject_name not in subjects:
                subjects[subject_name] = {
                    'test_score': result.test_score or 0,
                    'exam_score': result.exam_score or 0,
                    'average': result.average or 0,
                    'grade': result.calculate_grade() if hasattr(result, 'calculate_grade') else None,
                    'status': result.calculate_status() if hasattr(result, 'calculate_status') else None,
                    'comments': result.calculate_comments() if hasattr(result, 'calculate_comments') else None
                }
        context['subjects'] = subjects
        total = sum(result.total for result in student_results) if student_results else 0
        total_marks = sum(result.calculate_overall_total_marks() for result in student_results) if hasattr(Result, 'calculate_overall_total_marks') else 0
        overall_average = sum(result.average for result in student_results) / len(student_results) if student_results else None
        overall_grade = student_results[0].calculate_overall_grade(student) if student_results and hasattr(student_results[0], 'calculate_overall_grade') else None
        position = Result.calculate_position(overall_average) if hasattr(Result, 'calculate_position') else None
        context.update({
            'total': total,
            'total_marks': total_marks,
            'overall_average': overall_average,
            'overall_grade': overall_grade,
            'position': position,
            'student_id': student_id,
        })
        return context

# View to manage admin profile
@login_required
def admin_profile(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProfilePictureForm(instance=request.user)
    return render(request, 'result/admin_profile.html', {'form': form})