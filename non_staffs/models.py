from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class NonStaff(models.Model):
    STATUS = [("active", "Active"), ("inactive", "Inactive")]
    GENDER = [("male", "Male"), ("female", "Female")]

    current_status = models.CharField(max_length=10, choices=STATUS, default="active")
    firstname = models.CharField(max_length=200)
    other_name = models.CharField(max_length=200, blank=True)
    surname = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=GENDER, default="male")
    date_of_birth = models.DateField(default=timezone.now)
    date_of_admission = models.DateField(default=timezone.now)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # New field

    mobile_num_regex = RegexValidator(
        regex="^[0-9]{10,15}$", message="Entered mobile number isn't in a right format!"
    )
    mobile_number = models.CharField(
        validators=[mobile_num_regex], max_length=13, blank=True
    )

    address = models.TextField(blank=True)
    others = models.TextField(blank=True)

    def __str__(self):
        return f"{self.firstname} {self.other_name} {self.surname} "

    def get_absolute_url(self):
        return reverse("non-staff-detail", kwargs={"pk": self.pk})
