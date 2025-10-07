from django.db import models
from apps.students.models import Student
from apps.corecode.models import AcademicSession, Installment
from apps.finance.models import Invoice
from accounts.models import ParentUser
#from parents.models import InvoiceComments

class BursorAnswer(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, default=None)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, default=None)
    installment = models.ForeignKey(Installment, on_delete=models.CASCADE, default=None)
    parent = models.ForeignKey(ParentUser, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)  # Allow blank text answers if only audio is provided
    audio_answer = models.FileField(upload_to='bursor_audio_answers/', blank=True, null=True)  # Audio field
    date_commented = models.DateTimeField(auto_now_add=True)
    date_updated_comments = models.DateTimeField(auto_now=True)
    satisfied = models.BooleanField(default=False)
    #comment = models.OneToOneField(InvoiceComments, on_delete=models.CASCADE)

    def __str__(self):
        return f"Answer for Invoice {self.invoice.id} by {self.parent.username}"
