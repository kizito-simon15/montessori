from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from apps.corecode.models import StudentClass, AcademicTerm, AcademicSession

class Student(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive")]
    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]  # Updated to match form
    CATEGORY_CHOICES = [
        ("boarding", "Boarding"),
        ("day_walker", "Day Scholar (Walker)"),
        ("day_bus", "Day Scholar (Bus)"),
    ]
    NHIF_SOURCE_CHOICES = [
        ("parent_processed", "Parent-Processed"),
        ("school_processed", "School-Processed"),
    ]

    current_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    registration_number = models.CharField(
        max_length=200,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^S[0-9]{7}/[0-9]{4}/[0-9]{4}$',
                message="Registration number must be in the format SXXXXXXX/XXXX/YYYY (e.g., S1234567/0032/2025)."
            )
        ]
    )
    firstname = models.CharField(max_length=200)
    middle_name = models.CharField(max_length=200, blank=True)
    surname = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="M")  # Updated default to 'M'
    date_of_birth = models.DateField(default=timezone.now)
    current_class = models.ForeignKey(StudentClass, on_delete=models.SET_NULL, blank=True, null=True)
    date_of_admission = models.DateField(default=timezone.now)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="boarding")
    mobile_num_regex = RegexValidator(regex=r"^\+255[0-9]{9}$", message="Entered mobile number isn't in a right format!")
    guardian1_mobile_number = models.CharField(validators=[mobile_num_regex], max_length=13, blank=True, default='+255')
    guardian2_mobile_number = models.CharField(max_length=13, blank=True)
    has_nhif = models.BooleanField(default=False)
    nhif_source = models.CharField(max_length=20, choices=NHIF_SOURCE_CHOICES, blank=True, null=True)
    nhif_number = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True)
    others = models.TextField(blank=True)
    passport = models.ImageField(blank=True, upload_to="students/passports/")
    parent_student_id = models.IntegerField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    alumni_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="alumni",
        help_text="Academic session when the student became an alumnus"
    )

    class Meta:
        ordering = ["firstname", "middle_name", "surname"]

    def __str__(self):
        return f"{self.firstname} {self.middle_name} {self.surname} ({self.registration_number})"

    def get_absolute_url(self):
        return reverse("student-detail", kwargs={"pk": self.pk})

    def clean(self):
        if self.guardian1_mobile_number and self.guardian1_mobile_number.startswith('0'):
            self.guardian1_mobile_number = '+255' + self.guardian1_mobile_number[1:]
        if self.guardian2_mobile_number and self.guardian2_mobile_number.startswith('0'):
            self.guardian2_mobile_number = '+255' + self.guardian2_mobile_number[1:]
        if self.guardian2_mobile_number and not self.guardian2_mobile_number.startswith('+255'):
            raise ValueError("Guardian 2 mobile number must be in the format +255XXXXXXXXX")
        if self.has_nhif:
            if not self.nhif_source:
                raise ValueError("NHIF source must be specified if the student has NHIF.")
            if not self.nhif_number:
                raise ValueError("NHIF number must be provided if the student has NHIF.")
        else:
            self.nhif_source = None
            self.nhif_number = None
        super(Student, self).clean()

    def save(self, *args, **kwargs):
        self.clean()
        super(Student, self).save(*args, **kwargs)

class StudentTermAssignment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)
    academic_session = models.ForeignKey('corecode.AcademicSession', on_delete=models.CASCADE)
    assigned_date = models.DateField(default=timezone.now)

    class Meta:
        unique_together = ['student', 'academic_term', 'academic_session']
        ordering = ['student__firstname', 'academic_session__name', 'academic_term__name']

    def __str__(self):
        return f"{self.student} - {self.academic_term} ({self.academic_session})"

class StudentBulkUpload(models.Model):
    date_uploaded = models.DateTimeField(auto_now=True)
    csv_file = models.FileField(upload_to="students/bulkupload/")