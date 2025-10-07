from django.db import models
from apps.corecode.models import AcademicSession, AcademicTerm

class Event(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    date = models.DateTimeField()
    participants = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set the timestamp when an event is created
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, default=None)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, default=None)

    def __str__(self):
        return self.title
