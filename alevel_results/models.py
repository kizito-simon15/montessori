from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, StudentClass, Subject
from alevel_students.models import ALevelStudent
from decimal import Decimal

class ALevelResult(models.Model):
    student = models.ForeignKey(ALevelStudent, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)
    exam = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    current_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    test_score = models.DecimalField(
        null=True, blank=True, default=None,
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    exam_score = models.DecimalField(
        null=True, blank=True, default=None,
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    average = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    overall_average = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    overall_status = models.CharField(max_length=10, default='FAIL')
    status = models.CharField(max_length=10, default='FAIL')
    gpa = models.DecimalField(max_digits=5, decimal_places=3, default=0.000)
    subject_grade = models.CharField(max_length=1, default='F')
    division = models.CharField(max_length=5, default='0')

    class Meta:
        ordering = ["subject"]
        permissions = [
            ('delete_page', 'Can delete page results'),
        ]

    def __str__(self):
        return f"{self.student} {self.session} {self.term} {self.subject}"

    def save(self, *args, **kwargs):
        if self.test_score is not None and self.exam_score is None:
            self.average = self.test_score
        elif self.test_score is None and self.exam_score is not None:
            self.average = self.exam_score
        elif self.test_score is not None and self.exam_score is not None:
            self.average = (self.test_score + self.exam_score) / 2
        else:
            self.average = 0

        self.total = self.average
        self.status = self.calculate_status()
        self.subject_grade = self.calculate_grade()
        self.gpa = self.calculate_gpa()
        self.division = self.calculate_division()

        super().save(*args, **kwargs)

    def calculate_status(self):
        return "PASS" if self.average >= 40 else "FAIL"

    def calculate_grade(self):
        avg = float(self.average)
        if 80 <= avg <= 100:
            return "A"
        elif 70 <= avg < 80:
            return "B"
        elif 60 <= avg < 70:
            return "C"
        elif 50 <= avg < 60:
            return "D"
        elif 40 <= avg < 50:
            return "E"
        elif 35 <= avg < 40:
            return "S"
        else:
            return "F"

    def calculate_gpa(self):
        grade_points = {'A': 1.0, 'B': 2.0, 'C': 3.0, 'D': 4.0, 'E': 5.0, 'S': 6.0, 'F': 7.0}
        results = ALevelResult.objects.filter(
            student=self.student, session=self.session, term=self.term, exam=self.exam
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        count = results.count()
        if count == 0:
            return 0.000
        total_points = sum(grade_points.get(r.calculate_grade(), 7.0) for r in results)
        return round(total_points / count, 3)

    def calculate_division(self):
        grade_points = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'S': 6, 'F': 7}
        results = ALevelResult.objects.filter(
            student=self.student, session=self.session, term=self.term, exam=self.exam
        ).exclude(
            test_score__isnull=True, exam_score__isnull=True
        ).exclude(
            subject__name__in=['Basic Applied Mathematics', 'General Studies']
        )

        if results.count() < 3:
            return "0"

        grades = [r.calculate_grade() for r in results]
        points = [grade_points[grade] for grade in grades]
        points.sort()
        total_points = sum(points[:3]) if len(points) >= 3 else sum(points)

        has_principal_pass = any(grade in ['A', 'B', 'C', 'D', 'E'] for grade in grades)
        if not has_principal_pass:
            return "0"

        if 3 <= total_points <= 9:
            return "I"
        elif 10 <= total_points <= 12:
            return "II"
        elif 13 <= total_points <= 17:
            return "III"
        elif 18 <= total_points <= 19:
            return "IV"
        elif 20 <= total_points <= 21:
            return "0"
        else:
            return "0"

    def calculate_overall_status(self):
        results = ALevelResult.objects.filter(
            student=self.student, session=self.session, term=self.term, exam=self.exam
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        has_principal_pass = any(result.average >= 40 for result in results)
        return "PASS" if has_principal_pass else "FAIL"

    def calculate_overall_total_marks(self):
        results = ALevelResult.objects.filter(
            student=self.student, session=self.session, term=self.term, exam=self.exam
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        return results.count() * 100

    @classmethod
    def calculate_overall_grade(cls, student):
        student_results = cls.objects.filter(
            student=student
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        count = student_results.count()
        if count == 0:
            return "No results available"
        overall_average = sum(float(r.average) for r in student_results) / count
        if 80 <= overall_average <= 100:
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

    def calculate_comments(self):
        grade = self.calculate_grade()
        if grade == "A":
            return "VIZURI SANA"
        elif grade == "B":
            return "VIZURI"
        elif grade == "C":
            return "WASTANI"
        elif grade == "D":
            return "HAFIFU"
        elif grade in ["E", "S", "F"]:
            return "MBAYA"
        return ""

    @classmethod
    def calculate_position(cls, overall_average):
        if overall_average is not None:
            distinct_averages = cls.objects.filter(
                overall_average__gt=0
            ).values_list('overall_average', flat=True).distinct().order_by('-overall_average')
            distinct_list = list(distinct_averages)
            try:
                position = distinct_list.index(overall_average) + 1
            except ValueError:
                position = None
        else:
            position = None
        return position

    @classmethod
    def total_students(cls, student_class):
        return cls.objects.filter(
            current_class=student_class
        ).exclude(test_score__isnull=True, exam_score__isnull=True).values_list('student', flat=True).distinct().count()

    @classmethod
    def calculate_subject_gpa(cls, student_class, subject):
        grade_points = {'A': 1.0, 'B': 2.0, 'C': 3.0, 'D': 4.0, 'E': 5.0, 'S': 6.0, 'F': 7.0}
        results = cls.objects.filter(
            current_class=student_class, subject=subject
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        count = results.count()
        if count == 0:
            return 0.000
        total_points = sum(grade_points.get(r.calculate_grade(), 7.0) for r in results)
        return round(total_points / count, 3)

    @classmethod
    def calculate_subject_overall_average(cls, student_class, subject):
        results = cls.objects.filter(
            current_class=student_class, subject=subject
        ).exclude(test_score__isnull=True, exam_score__isnull=True)
        count = results.count()
        if count == 0:
            return 0.000
        total_average = sum(float(r.average) for r in results)
        return round(total_average / count, 2)

    def calculate_subject_grade(self, student_class, subject):
        subject_overall_average = self.calculate_subject_overall_average(student_class, subject)
        if 80 <= subject_overall_average <= 100:
            return "A"
        elif 70 <= subject_overall_average < 80:
            return "B"
        elif 60 <= subject_overall_average < 70:
            return "C"
        elif 50 <= subject_overall_average < 60:
            return "D"
        elif 40 <= subject_overall_average < 50:
            return "E"
        elif 35 <= subject_overall_average < 40:
            return "S"
        else:
            return "F"

class ALevelStudentInfos(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, default=None)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, default=None)
    exam = models.ForeignKey(ExamType, on_delete=models.CASCADE, default=None)

    DISCIPLINE_CHOICES = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("F", "F")]
    SPORTS_CHOICES = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("F", "F")]
    CARE_OF_PROPERTY_CHOICES = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("F", "F")]
    COLLABORATIONS_CHOICES = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("F", "F")]

    disprine = models.CharField(max_length=1, choices=DISCIPLINE_CHOICES, default="A")
    sports = models.CharField(max_length=1, choices=SPORTS_CHOICES, default="A")
    care_of_property = models.CharField(max_length=1, choices=CARE_OF_PROPERTY_CHOICES, default="A")
    collaborations = models.CharField(max_length=1, choices=COLLABORATIONS_CHOICES, default="A")
    date_of_closing = models.DateField(default=timezone.now)
    date_of_opening = models.DateField(default=timezone.now)
    teacher_comments = models.TextField(blank=True)
    head_comments = models.TextField(blank=True)
    academic_answers = models.TextField(blank=True)
    student = models.ForeignKey(ALevelStudent, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        permissions = [
            ('view_single_student_results', 'Can view single student results'),
        ]

    def __str__(self):
        return f"{self.student} - {self.session} - {self.term}"