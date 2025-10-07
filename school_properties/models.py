# Create your models here.
from django.db import models
from apps.corecode.models import AcademicSession

class Property(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
