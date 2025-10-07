from django.db import models
from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from apps.students.models import Student
from django.core.exceptions import ValidationError

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_group = models.ForeignKey(StudentClass, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    present = models.BooleanField(default=False)
    absent = models.BooleanField(default=False)
    permission = models.BooleanField(default=False)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)

    def clean(self):
        # Ensure only one of present, absent, or permission is True
        if sum([self.present, self.absent, self.permission]) > 1:
            raise ValidationError('A student cannot be present, absent, and on permission at the same time.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

