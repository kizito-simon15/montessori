from django.db import models
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType
from apps.students.models import Student

class AcademicAnswer(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)
    exam = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)  # Allow blank text answers
    audio_answer = models.FileField(upload_to='academic_audio_answers/', blank=True, null=True)  # Audio field
    date_commented = models.DateTimeField(auto_now_add=True)
    date_updated_comments = models.DateTimeField(auto_now=True)
    mark_comment = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer by {self.student} for {self.exam} in {self.term}, {self.session}"
