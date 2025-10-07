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

from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, SiteConfig, StudentClass, Subject, Signature
from alevel_students.models import ALevelStudent
from alevel_results.models import ALevelResult, ALevelStudentInfos
from alevel_results.forms import (
    ClassSelectionForm, SessionTermExamSubjectForm, ResultEntryForm, ALevelStudentInfosForm,
    CreateResults, EditResults, ViewResultsForm, ViewResultsFormSet
)
from accounts.forms import ProfilePictureForm

logger = logging.getLogger(__name__)

@login_required
@permission_required('alevel_results.add_alevelresult', raise_exception=True)
def create_result(request):
    students = ALevelStudent.objects.filter(current_status__iexact="active", completed=False)
    logger.debug(f"Active A-Level students count: {students.count()}")
    for student in students:
        logger.debug(f"Student: {student}, Class: {student.current_class}, Gender: {student.gender}")

    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam = ExamType.objects.filter(current=True).first()

    if not current_session or not current_term or not current_exam:
        messages.warning(request, "Please ensure an Academic Session, Term, and Exam Type are set as current.")
        return render(request, "alevel_results/create_result.html", {"students": students, "students_by_class": {}})

    request.session['current_session'] = current_session.id if current_session else None
    request.session['current_term'] = current_term.id if current_term else None
    request.session['current_exam'] = current_exam.id if current_exam else None

    if not StudentClass.objects.exists():
        messages.warning(request, "No student classes found. Please create a class first.")
        return render(request, "alevel_results/create_result.html", {"students": students, "students_by_class": {}})

    if not students.exists():
        messages.warning(request, "No active, non-completed A-Level students found. Please add or update students.")
        return render(request, "alevel_results/create_result.html", {"students": students, "students_by_class": {}})

    # Sort students: females first, then males, both in alphabetical order
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

    # Group students by class
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
        return render(request, "alevel_results/create_result.html", {"students": students, "students_by_class": {}})

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
                        stu = ALevelStudent.objects.get(pk=student_id)
                        if stu.current_class:
                            for subject in subjects:
                                check = ALevelResult.objects.filter(
                                    session=session,
                                    term=term,
                                    exam=exam,
                                    current_class=stu.current_class,
                                    subject=subject,
                                    student=stu,
                                ).first()
                                if not check:
                                    results.append(
                                        ALevelResult(
                                            session=session,
                                            term=term,
                                            exam=exam,
                                            current_class=stu.current_class,
                                            subject=subject,
                                            student=stu,
                                        )
                                    )
                    ALevelResult.objects.bulk_create(results)
                    request.session['selected_students'] = students_str
                    selected_student_names = ', '.join([
                        f"{ALevelStudent.objects.get(pk=sid).firstname} "
                        f"{ALevelStudent.objects.get(pk=sid).middle_name} "
                        f"{ALevelStudent.objects.get(pk=sid).surname}"
                        for sid in students_str.split(",")
                    ])
                    request.session['selected_student_name'] = selected_student_names
                    return redirect("alevel_results:edit_results")
                else:
                    messages.warning(request, "You didn't select any student.")
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
                    "alevel_results/create_result_page2.html",
                    {"students": studentlist, "form": form, "count": len(id_list), "students_by_class": students_by_class},
                )
            else:
                messages.warning(request, "You didn't select any student.")

    return render(request, "alevel_results/create_result.html", {"students": students, "students_by_class": dict(students_by_class)})

@login_required
@permission_required('alevel_results.change_alevelresult', raise_exception=True)
def edit_results(request):
    logger.debug("Entering the edit_results view")
    student_classes = StudentClass.objects.all()
    subjects = Subject.objects.all()
    sessions = AcademicSession.objects.all()
    terms = AcademicTerm.objects.all()
    exam_types = ExamType.objects.all()
    logger.debug("Fetched student classes and subjects: %s, %s", student_classes, subjects)

    current_session = AcademicSession.objects.filter(current=True).first()
    current_term = AcademicTerm.objects.filter(current=True).first()
    current_exam_type = ExamType.objects.filter(current=True).first()

    if request.method == "POST":
        logger.debug("Handling POST request")
        formset = EditResults(request.POST)
        result_ids = request.POST.getlist('result_ids')  # Get selected result IDs

        if not result_ids:
            messages.warning(request, "Please select at least one result to update.")
            return redirect("alevel_results:edit_results")

        if formset.is_valid():
            logger.debug("Formset is valid. Processing forms...")
            updated_count = 0
            for form in formset:
                # Only process forms that correspond to selected result_ids
                if str(form.instance.id) in result_ids:
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
                        updated_count += 1
            messages.success(request, f"{updated_count} results successfully updated.")
            return redirect("alevel_results:edit_results")
        else:
            logger.error("Formset is invalid. Errors: %s", formset.errors)
            messages.error(request, "There was an error updating the results. Please fix the errors and try again.")
    else:
        logger.debug("Handling GET request")
        session_id = request.GET.get('session', request.session.get('current_session'))
        term_id = request.GET.get('term', request.session.get('current_term'))
        exam_id = request.GET.get('exam', request.session.get('current_exam'))
        class_select = request.GET.get('class_select')
        subject_select = request.GET.get('subject_select')
        student_name = request.GET.get('student_name')

        logger.debug("Filters: session_id=%s, term_id=%s, exam_id=%s, class_select=%s, subject_select=%s, student_name=%s", 
                     session_id, term_id, exam_id, class_select, subject_select, student_name)

        results = ALevelResult.objects.all()

        if session_id:
            results = results.filter(session_id=session_id)
        if term_id:
            results = results.filter(term_id=term_id)
        if exam_id:
            results = results.filter(exam_id=exam_id)
        if class_select:
            results = results.filter(current_class_id=class_select)
            logger.debug("Filtered results by class_select: %s", results)
        if subject_select:
            results = results.filter(subject_id=subject_select)
            logger.debug("Filtered results by subject_select: %s", results)
        if student_name:
            results = results.filter(
                Q(student__firstname__icontains=student_name) |
                Q(student__middle_name__icontains=student_name) |
                Q(student__surname__icontains=student_name)
            )
            logger.debug("Filtered results by student_name: %s", results)

        formset = EditResults(queryset=results)
        logger.debug("Created formset with queryset: %s", results)

    return render(request, "alevel_results/edit_results.html", {
        "formset": formset,
        "student_classes": student_classes,
        "subjects": subjects,
        "sessions": sessions,
        "terms": terms,
        "exam_types": exam_types,
        "current_session": current_session,
        "current_term": current_term,
        "current_exam_type": current_exam_type,
    })

@login_required
@permission_required('alevel_results.change_alevelresult', raise_exception=True)
def edit_now_results(request):
    if request.method == 'POST':
        result_ids = request.POST.getlist('result_ids')
        for result_id in result_ids:
            result = get_object_or_404(ALevelResult, id=result_id)
            form = ResultEntryForm(request.POST, instance=result, prefix=f'result_{result_id}')
            if form.is_valid():
                form.save()
        messages.success(request, 'Results updated successfully.')
        return redirect('alevel_results:edit_results')
    else:
        results = ALevelResult.objects.all()
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
    return render(request, 'alevel_results/edit_now_results.html', context)

@login_required
@permission_required('alevel_results.delete_page', raise_exception=True)
def delete_page_results(request):
    if request.method == "POST":
        class_select = request.POST.get('class_select')
        subject_select = request.POST.get('subject_select')
        student_name = request.POST.get('student_name')

        results = ALevelResult.objects.filter(
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
        return redirect("alevel_results:edit_results")
    else:
        class_select = request.GET.get('class_select')
        subject_select = request.GET.get('subject_select')
        student_name = request.GET.get('student_name')

        context = {
            'class_select': class_select,
            'subject_select': subject_select,
            'student_name': student_name,
        }
        return render(request, 'alevel_results/confirm_delete_page_results.html', context)

class ALevelStudentResultsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'alevel_results/student_results.html'
    permission_required = "alevel_results.view_alevelresult"

    def get(self, request, student_id):
        student = get_object_or_404(ALevelStudent, pk=student_id)
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_exam = ExamType.objects.filter(current=True).first()

        student_info = student.alevelstudentinfos_set.filter(
            session=current_session,
            term=current_term,
            exam=current_exam
        ).last()

        form = ALevelStudentInfosForm(instance=student_info)
        return render(request, self.template_name, {
            'form': form,
            'session': current_session,
            'term': current_term,
            'exam_type': current_exam,
            'student_class': student.current_class,
            'student': student,
        })

    def post(self, request, student_id):
        student = get_object_or_404(ALevelStudent, pk=student_id)
        current_session = AcademicSession.objects.filter(current=True).first()
        current_term = AcademicTerm.objects.filter(current=True).first()
        current_exam = ExamType.objects.filter(current=True).first()

        form = ALevelStudentInfosForm(request.POST)
        if form.is_valid():
            student_info = form.save(commit=False)
            student_info.student = student
            student_info.session = current_session
            student_info.term = current_term
            student_info.exam = current_exam
            student_info.save()
            messages.success(request, 'The student information has been saved successfully.')
            return redirect('alevel_results:student_results', student_id=student_id)

        return render(request, self.template_name, {
            'form': form,
            'session': current_session,
            'term': current_term,
            'exam_type': current_exam,
            'student_class': student.current_class,
            'student': student,
        })

class ALevelFormStatusView(LoginRequiredMixin, View):
    template_name = 'alevel_results/form_status.html'

    def calculate_overall_grade(self, overall_average):
        if overall_average >= 80:
            return "A"
        elif 70 <= overall_average < 80:
            return "B"
        elif 60 <= overall_average < 70:
            return "C"
        elif 50 <= overall_average < 60:
            return "D"
        elif 40 <= overall_average < 50:
            return "E"
        elif 35 <= overall_average < 40:
            return "S"
        else:
            return "F"

    def calculate_overall_total_marks(self, student):
        subject_count = student.alevelresult_set.values('subject').distinct().count()
        return subject_count * 100

    def get_total_active_students(self, class_id, current_session, current_term, current_exam_type):
        return ALevelStudent.objects.filter(
            alevelresult__current_class_id=class_id,
            alevelresult__session_id=current_session,
            alevelresult__term_id=current_term,
            alevelresult__exam_id=current_exam_type,
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

        total_active_students = self.get_total_active_students(class_id, current_session, current_term, current_exam_type)

        students_with_forms = ALevelStudent.objects.filter(
            alevelresult__current_class=student_class,
            alevelresult__session_id=current_session,
            alevelresult__term_id=current_term,
            alevelresult__exam_id=current_exam_type
        ).distinct()

        query = request.GET.get('q')
        if query:
            students_with_forms = students_with_forms.filter(
                Q(firstname__icontains=query) | Q(middle_name__icontains=query) |
                Q(surname__icontains=query) | Q(registration_number=query)
            )

        no_forms = not students_with_forms.exists()
        completed_forms_count = 0
        for student in students_with_forms:
            last_student_info = student.alevelstudentinfos_set.last()
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
            student_results_queryset = student.alevelresult_set.filter(
                current_class=student_class,
                session_id=current_session,
                term_id=current_term,
                exam_id=current_exam_type
            )

            total_average = student_results_queryset.aggregate(Sum('average'))['average__sum']
            overall_average = student_results_queryset.aggregate(Avg('average'))['average__avg']
            overall_grade = self.calculate_overall_grade(overall_average) if overall_average is not None else "No results available"
            overall_total_marks = self.calculate_overall_total_marks(student)

            # Get division from the first result (since it's calculated per student)
            division = student_results_queryset.first().division if student_results_queryset.exists() else "0"

            student_results.append({
                'student': student,
                'total_average': total_average,
                'overall_average': overall_average,
                'overall_grade': overall_grade,
                'overall_total_marks': overall_total_marks,
                'division': division,
                'results': student_results_queryset
            })

        sorted_results = sorted(student_results, key=lambda x: x['overall_average'] or 0, reverse=True)

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
            'current_exam_type': AcademicTerm.objects.get(id=current_term),
            'completed_forms_count': completed_forms_count,
            'no_forms': no_forms,
            'total_active_students': total_active_students,
            'headmaster_signature': headmaster_signature,
        })


class ALevelClassResultsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'alevel_results/class_results.html'
    permission_required = "alevel_results.view_alevelresult"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        selected_class = StudentClass.objects.get(pk=class_id)

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

        results = ALevelResult.objects.filter(
            current_class=selected_class,
            session=session,
            term=term,
            exam=exam
        ).exclude(test_score__isnull=True, exam_score__isnull=True).select_related('student')

        if not results.exists():
            context['no_results'] = True
            return context

        context['no_results'] = False
        data = []
        subjects = set()

        student_results_map = {}
        for result in results:
            if result.student not in student_results_map:
                student_results_map[result.student] = []
            student_results_map[result.student].append(result)

        for student, student_results in student_results_map.items():
            student_data = {
                'student': student,
                'student_class': selected_class,
                'subject_results': [],
                'division': student_results[0].division if student_results else "0"
            }

            total_marks = sum(float(res.average) for res in student_results)
            overall_average = total_marks / len(student_results) if student_results else 0
            overall_status = "PASS" if overall_average >= 40 else "FAIL"

            student_data['total'] = total_marks
            student_data['overall_average'] = overall_average
            student_data['overall_status'] = overall_status

            for result in student_results:
                subjects.add(result.subject.name)
                student_data['subject_results'].append({
                    'subject': result.subject.name,
                    'test_score': result.test_score,
                    'exam_score': result.exam_score,
                    'average': result.average,
                    'grade': result.subject_grade
                })

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
        results = ALevelResult.objects.filter(
            current_class=student_class,
            subject=subject,
            session=session,
            term=term,
            exam=exam
        ).exclude(test_score__isnull=True, exam_score__isnull=True)

        total_average = results.aggregate(total_average=Sum('average'))['total_average'] or 0
        count = results.count()
        return round(total_average / count, 2) if count else 0.00

    def calculate_subject_grade(self, subject_average):
        if subject_average >= 80:
            return "A"
        elif 70 <= subject_average < 80:
            return "B"
        elif 60 <= subject_average < 70:
            return "C"
        elif 50 <= subject_average < 60:
            return "D"
        elif 40 <= subject_average < 50:
            return "E"
        elif 35 <= subject_average < 40:
            return "S"
        else:
            return "F"

    def calculate_subject_gpa(self, student_class, subject, session, term, exam):
        results = ALevelResult.objects.filter(
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

class ALevelClassListView(View):
    def get(self, request):
        classes = StudentClass.objects.all()
        context = {'classes': classes}
        return render(request, 'alevel_results/class_list.html', context)

    def post(self, request):
        class_id = request.POST.get('class_id')
        if class_id:
            return redirect('alevel_results:class_results', class_id=class_id)
        return redirect('alevel_results:class_list')

class ALevelSingleClassResultsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'alevel_results/single_class_results.html'
    permission_required = "alevel_results.view_alevelresult"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        selected_class = StudentClass.objects.get(pk=class_id)

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

        results = ALevelResult.objects.filter(
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

        student_results_map = {}
        for result in results:
            if result.student not in student_results_map:
                student_results_map[result.student] = []
            student_results_map[result.student].append(result)

        for student, student_results in student_results_map.items():
            student_data = {
                'student': student,
                'student_class': selected_class,
                'subject_results': [],
                'division': student_results[0].division if student_results else "0"
            }

            total_marks = sum(float(res.average) for res in student_results)
            overall_average = total_marks / len(student_results) if student_results else 0
            overall_status = "PASS" if overall_average >= 40 else "FAIL"

            student_data['total'] = total_marks
            student_data['overall_average'] = overall_average
            student_data['overall_status'] = overall_status

            for result in student_results:
                subjects.add(result.subject.name)
                student_data['subject_results'].append({
                    'subject': result.subject.name,
                    'test_score': result.test_score,
                    'exam_score': result.exam_score,
                    'average': result.average,
                    'grade': result.subject_grade
                })

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
        results = ALevelResult.objects.filter(
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
        if subject_average >= 80:
            return "A"
        elif 70 <= subject_average < 80:
            return "B"
        elif 60 <= subject_average < 70:
            return "C"
        elif 50 <= subject_average < 60:
            return "D"
        elif 40 <= subject_average < 50:
            return "E"
        elif 35 <= subject_average < 40:
            return "S"
        else:
            return "F"

    def calculate_subject_gpa(self, student_class, subject, session, term, exam):
        results = ALevelResult.objects.filter(
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

class ALevelSingleClassListView(View):
    def get(self, request):
        classes = StudentClass.objects.all()
        context = {'classes': classes}
        return render(request, 'alevel_results/single_class_list.html', context)

    def post(self, request):
        class_id = request.POST.get('class_id')
        if class_id:
            return redirect('alevel_results:single_results', class_id=class_id)
        return redirect('alevel_results:single_class')


class ALevelSingleStudentResultsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'alevel_results/single_student_results.html'
    permission_required = 'alevel_results.view_single_student_results'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_id = kwargs.get('student_id')
        student = ALevelStudent.objects.get(pk=student_id)

        session_id = self.request.GET.get('session')
        term_id = self.request.GET.get('term')
        exam_id = self.request.GET.get('exam')

        current_session = AcademicSession.objects.get(id=session_id) if session_id else AcademicSession.objects.get(current=True)
        current_term = AcademicTerm.objects.get(id=term_id) if term_id else AcademicTerm.objects.get(current=True)
        current_exam = ExamType.objects.get(id=exam_id) if exam_id else ExamType.objects.get(current=True)

        student_results = ALevelResult.objects.filter(
            student_id=student_id,
            session=current_session,
            term=current_term,
            exam=current_exam
        ).exclude(test_score__isnull=True, exam_score__isnull=True)

        context['student_name'] = f"{student.firstname} {student.middle_name} {student.surname}"
        context['registration_number'] = student.registration_number
        context['sessions'] = AcademicSession.objects.all()
        context['terms'] = AcademicTerm.objects.all()
        context['exams'] = ExamType.objects.all()
        context['current_session'] = current_session
        context['current_term'] = current_term
        context['current_exam'] = current_exam
        context['student'] = student
        context['class_id'] = student.current_class.id if student.current_class else None
        context['student_id'] = student_id

        subjects = {}
        for result in student_results:
            subject_name = result.subject.name
            subjects[subject_name] = {
                'test_score': result.test_score,
                'exam_score': result.exam_score,
                'average': result.average,
                'grade': result.calculate_grade(),
                'status': result.calculate_status(),
                'comments': result.calculate_comments(),
                'division': result.division
            }

        context['subjects'] = subjects

        total = sum(float(result.total) for result in student_results) if student_results else 0
        total_marks = sum(result.calculate_overall_total_marks() for result in student_results) if student_results else 0
        overall_average = sum(float(result.average) for result in student_results) / len(student_results) if student_results else None
        overall_grade = ALevelResult.calculate_overall_grade(student) if student_results else "No results available"
        position = ALevelResult.calculate_position(overall_average)
        division = student_results[0].division if student_results else "0"

        context.update({
            'total': total,
            'total_marks': total_marks,
            'overall_average': overall_average,
            'overall_grade': overall_grade,
            'position': position,
            'division': division,
        })

        return context



class ALevelFormStatusView(LoginRequiredMixin, View):
    template_name = 'alevel_results/form_status.html'

    def calculate_overall_grade(self, overall_average):
        if overall_average is None:
            return "No results available"
        if overall_average >= 80:
            return "A"
        elif 70 <= overall_average < 80:
            return "B"
        elif 60 <= overall_average < 70:
            return "C"
        elif 50 <= overall_average < 60:
            return "D"
        elif 40 <= overall_average < 50:
            return "E"
        elif 35 <= overall_average < 40:
            return "S"
        else:
            return "F"

    def calculate_overall_total_marks(self, valid_results):
        return valid_results.count() * 100

    def get_total_active_students(self, class_id, current_session, current_term, current_exam_type):
        return ALevelStudent.objects.filter(
            alevelresult__current_class_id=class_id,
            alevelresult__session_id=current_session,
            alevelresult__term_id=current_term,
            alevelresult__exam_id=current_exam_type,
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

        total_active_students = self.get_total_active_students(class_id, current_session, current_term, current_exam_type)

        students_with_forms = ALevelStudent.objects.filter(
            alevelresult__current_class=student_class,
            alevelresult__session_id=current_session,
            alevelresult__term_id=current_term,
            alevelresult__exam_id=current_exam_type
        ).distinct()

        query = request.GET.get('q')
        if query:
            students_with_forms = students_with_forms.filter(
                Q(firstname__icontains=query) | Q(middle_name__icontains=query) |
                Q(surname__icontains=query) | Q(registration_number=query)
            )

        no_forms = not students_with_forms.exists()
        completed_forms_count = 0
        for student in students_with_forms:
            last_student_info = student.alevelstudentinfos_set.filter(
                session_id=current_session,
                term_id=current_term,
                exam_id=current_exam_type
            ).last()
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
            student_results_queryset = student.alevelresult_set.filter(
                current_class=student_class,
                session_id=current_session,
                term_id=current_term,
                exam_id=current_exam_type
            ).exclude(test_score__isnull=True, exam_score__isnull=True)

            if not student_results_queryset.exists():
                continue

            total_average = student_results_queryset.aggregate(Sum('average'))['average__sum'] or 0
            overall_average = student_results_queryset.aggregate(Avg('average'))['average__avg']
            overall_grade = self.calculate_overall_grade(overall_average)
            overall_total_marks = self.calculate_overall_total_marks(student_results_queryset)
            division = student_results_queryset.first().division if student_results_queryset.exists() else "0"

            student_results.append({
                'student': student,
                'total_average': total_average,
                'overall_average': overall_average,
                'overall_grade': overall_grade,
                'overall_total_marks': overall_total_marks,
                'division': division,
                'results': student_results_queryset,
                'position': None
            })

        sorted_results = sorted(student_results, key=lambda x: x['overall_average'] or 0, reverse=True)

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

@login_required
def admin_profile(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProfilePictureForm(instance=request.user)
    return render(request, 'alevel_results/admin_profile.html', {'form': form})