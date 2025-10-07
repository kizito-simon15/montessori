# apps/staffs/models.py

from django.db import models
from django.utils import timezone
from apps.corecode.models import StudentClass, Subject  # Import the Subject model
from apps.staffs.models import Staff

class StaffRoles(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="roles")
    assigned_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE, related_name="class_roles")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name="subject_roles")  # Allow null and blank values
    is_class_teacher = models.BooleanField(default=False)  # Indicates if the staff controls overall class activities
    on_duty = models.BooleanField(default=False)  # Indicates if the teacher is on duty for the current week

    date_assigned = models.DateField(default=timezone.now)

    class Meta:
        verbose_name = "Staff Role"
        verbose_name_plural = "Staff Roles"
        unique_together = ('staff', 'assigned_class', 'subject')  # Ensures unique assignment for a staff, class, and subject combo

    def __str__(self):
        role = "Class Teacher" if self.is_class_teacher else f"Subject Teacher ({self.subject.name if self.subject else 'N/A'})"
        duty_status = " - On Duty" if self.on_duty else ""
        return f"{self.staff} - {role} for {self.assigned_class}{duty_status}"

    def save(self, *args, **kwargs):
        # Ensure only one teacher can be set as on duty at a time
        if self.on_duty:
            # Set all other staff roles' on_duty to False
            StaffRoles.objects.filter(on_duty=True).update(on_duty=False)
        
        super().save(*args, **kwargs)

from datetime import time
from django.db import models
from apps.corecode.models import StudentClass, Subject
from apps.staffs.models import Staff

class DailySchedule(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    day = models.CharField(max_length=20, choices=DAY_CHOICES, unique=True)
    start_time = models.TimeField(default=time(0, 0), help_text="Start time for school activities.")  # Default set to 00:00
    end_time = models.TimeField(default=time(0, 0), help_text="End time for school activities.")  # Default set to 00:00

    def __str__(self):
        return f"{self.day}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    class Meta:
        ordering = ['day']


class ClassSchedule(models.Model):
    daily_schedule = models.ForeignKey(DailySchedule, on_delete=models.CASCADE, related_name='class_schedules')
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE, related_name='schedules')
    start_time = models.TimeField(default=time(0, 0))  # Default set to 00:00
    end_time = models.TimeField(default=time(0, 0))  # Default set to 00:00
    activity_type = models.CharField(max_length=100, choices=[
        ('study', 'Study'),
        ('break', 'Break'),
        ('event', 'Event')
    ], default='study')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='class_subjects')
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='class_staff')
    description = models.CharField(max_length=200, blank=True, help_text="Optional description for event activities")

    def __str__(self):
        return f"{self.daily_schedule.day} - {self.student_class}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')} ({self.activity_type})"

    class Meta:
        unique_together = ('daily_schedule', 'student_class', 'start_time', 'end_time')
        ordering = ['daily_schedule__day', 'student_class', 'start_time']
