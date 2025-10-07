from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, StudentClass, Subject
from apps.students.models import Student


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)
    exam = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    current_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    # Scores validated to be between 0 and 100
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

    # Fields to store calculated values (max 100 per subject)
    average = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    overall_average = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    overall_status = models.CharField(max_length=10, default='FAIL')
    status = models.CharField(max_length=10, default='FAIL')
    gpa = models.DecimalField(max_digits=5, decimal_places=3, default=0.000)
    subject_grade = models.CharField(max_length=1, default='F')

    class Meta:
        ordering = ["subject"]
        permissions = [
            ('delete_page', 'Can delete page results'),
        ]

    def __str__(self):
        return f"{self.student} {self.session} {self.term} {self.subject}"

    def save(self, *args, **kwargs):
        # Calculate average: (test_score + exam_score)/2, max 100
        if self.test_score is not None and self.exam_score is None:
            self.average = self.test_score
        elif self.test_score is None and self.exam_score is not None:
            self.average = self.exam_score
        elif self.test_score is not None and self.exam_score is not None:
            self.average = (self.test_score + self.exam_score) / 2
        else:
            self.average = 0

        # Set total to the average for this subject
        self.total = self.average

        # Update status, grade, and GPA
        self.status = self.calculate_status()
        self.subject_grade = self.calculate_grade()
        self.gpa = self.calculate_gpa()

        super().save(*args, **kwargs)

    def calculate_result(self):
        pass

    def calculate_overall_status(self):
        # Passing threshold: 50 out of 100 (50% mark)
        return "PASS" if self.overall_average >= 50 else "FAIL"

    def calculate_status(self):
        # Passing threshold: 50 out of 100
        return "PASS" if self.average >= 50 else "FAIL"

    def calculate_grade(self):
        avg = float(self.average)
        # New grading scale
        if avg >= 81:
            return "A"
        elif 75 <= avg < 81:
            return "B"
        elif 65 <= avg < 75:
            return "C"
        elif 55 <= avg < 65:
            return "D"
        else:
            return "F"

    def calculate_overall_total_marks(self):
        # Each subject max is 100, total max = count * 100
        return Subject.objects.count() * 100

    @classmethod
    def calculate_overall_grade(cls, student):
        student_results = cls.objects.filter(student=student)
        count = student_results.count()
        if count == 0:
            return "No results available"
        overall_average = sum(r.average for r in student_results) / count
        # New grading scale
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
        else:
            return "MBAYA"

    @classmethod
    def calculate_position(cls, overall_average):
        if overall_average is not None:
            distinct_averages = cls.objects.values_list('overall_average', flat=True).distinct().order_by('-overall_average')
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
        return cls.objects.filter(current_class=student_class).values_list('student', flat=True).distinct().count()

    def calculate_gpa(self):
        grade_points = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}
        results = Result.objects.filter(student=self.student)
        count = results.count()
        if count == 0:
            return 0.000
        total_points = sum(grade_points.get(r.calculate_grade(), 0) for r in results)
        return round(total_points / count, 3)

    @classmethod
    def calculate_subject_gpa(cls, student_class, subject):
        grade_points = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}
        results = cls.objects.filter(current_class=student_class, subject=subject)
        count = results.count()
        if count == 0:
            return 0.000
        total_points = sum(grade_points.get(r.calculate_grade(), 0) for r in results)
        return round(total_points / count, 3)

    @classmethod
    def calculate_subject_overall_average(cls, student_class, subject):
        results = cls.objects.filter(current_class=student_class, subject=subject)
        count = results.count()
        if count == 0:
            return 0.000
        total_average = sum(r.average for r in results)
        return round(total_average / count, 2)

    def calculate_subject_grade(self, student_class, subject):
        subject_overall_average = self.calculate_subject_overall_average(student_class, subject)
        # New grading scale
        if subject_overall_average >= 81:
            return "A"
        elif 75 <= subject_overall_average < 81:
            return "B"
        elif 65 <= subject_overall_average < 75:
            return "C"
        elif 55 <= subject_overall_average < 65:
            return "D"
        else:
            return "F"




class StudentInfos(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, default=None)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, default=None)
    exam = models.ForeignKey(ExamType, on_delete=models.CASCADE, default=None)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)

    # Choices for behavior evaluation fields
    BEHAVIOR_CHOICES = [
        ("A", "A (Excellent)"),
        ("B", "B (Very Good)"),
        ("C", "C (Good)"),
        ("D", "D (Satisfactory)"),
        ("F", "F (Needs Improvement)"),
    ]

    cooperation_with_peers = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    honesty = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    hygiene = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    willingness_to_work = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    respect = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    collaboration_in_work = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    love_for_work = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    behavior_improvement = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    effort = models.CharField(max_length=1, choices=BEHAVIOR_CHOICES, default="A")
    date_of_closing = models.DateField(default=timezone.now)
    date_of_opening = models.DateField(default=timezone.now)
    head_comments = models.TextField(blank=True)

    class Meta:
        permissions = [
            ('view_single_student_results', 'Can view single student results'),
        ]

    def __str__(self):
        return f"{self.student} - {self.session} - {self.term}"