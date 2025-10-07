from django.db import models
from apps.corecode.models import AcademicSession, AcademicTerm, StudentClass
from apps.students.models import Student
from apps.staffs.models import Staff

class Book(models.Model):
    book_name = models.CharField(max_length=100)
    book_number = models.CharField(max_length=20)
    author = models.CharField(max_length=100)
    ISBN = models.CharField(max_length=20)
    category = models.CharField(max_length=50)
    quantity = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, default=None)
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE, default=None)  # Added field
    date_buyed = models.DateField(null=True, blank=True)
    date_updated = models.DateField(auto_now=True)  # Added field

    def __str__(self):
        return self.book_name

class Stationery(models.Model):
    TYPE_CHOICES = [
        ('Dozen', 'Dozen'),
        ('Carton', 'Carton'),
        ('Pc', 'Pc'),
        ('Ft', 'Ft'),
        ('Inch', 'Inch'),
        ('Box', 'Box'),
    ]

    name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    date_buyed = models.DateField(null=True, blank=True)  # Date input field
    date_updated = models.DateField(auto_now=True)  # Auto-updated field
    office_department = models.CharField(max_length=100, blank=True, default=None)  # Optional field with default value
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Pc')  # New choice field

    def __str__(self):
        return self.name

class IssuedBook(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    book_number = models.IntegerField(default=0)
    date_issued = models.DateField()
    expiry_date = models.DateField()
    returned = models.BooleanField(default=False)

    def __str__(self):
        return f"Issued: {self.book} to {self.student}"

class IssuedStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    book_number = models.IntegerField(default=0)
    date_issued = models.DateField()
    expiry_date = models.DateField()
    returned = models.BooleanField(default=False)

    def __str__(self):
        return f"Issued: {self.book} to {self.staff}"
