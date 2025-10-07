from django.db import models
from apps.students.models import Student
from accounts.models import ParentUser
from apps.finance.models import Invoice
from apps.corecode.models import AcademicSession, AcademicTerm, ExamType, Installment

class ParentComments(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey('accounts.ParentUser', on_delete=models.CASCADE)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, default=None)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, default=None)
    exam = models.ForeignKey(ExamType, on_delete=models.CASCADE, default=None)
    comment = models.TextField(default=None, blank=True, null=True)
    audio_comment = models.FileField(upload_to='parent_audio_comments/', null=True, blank=True)  # New field
    date_commented = models.DateTimeField(auto_now_add=True)
    date_updated_comments = models.DateTimeField(auto_now=True)
    mark_comment = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.parent.username} for {self.student.firstname} {self.student.surname}"

class StudentComments(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey('accounts.ParentUser', on_delete=models.CASCADE)
    comment = models.TextField(default=None, blank=True, null=True)
    audio_comment = models.FileField(upload_to='student_audio_comments/', null=True, blank=True)  # New field
    date_commented = models.DateTimeField(auto_now_add=True)
    date_updated_comments = models.DateTimeField(auto_now=True)
    mark_student_comment = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.parent.username} for {self.student.firstname} {self.student.surname}"

class InvoiceComments(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, default=None)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, default=None)
    installment = models.ForeignKey(Installment, on_delete=models.CASCADE, default=None)
    parent = models.ForeignKey(ParentUser, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)
    audio_comment = models.FileField(upload_to='invoice_audio_comments/', null=True, blank=True)  # New field
    date_commented = models.DateTimeField(auto_now_add=True)
    date_updated_comments = models.DateTimeField(auto_now=True)
    satisfied = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.parent.username} for Invoice {self.invoice.id}"
