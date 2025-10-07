from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.students.models import Student
from apps.staffs.models import Staff  # Assuming the staff app and model are named accordingly

class DisciplineIssue(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    reported_by_student = models.ForeignKey(Student, related_name='reported_issues', null=True, blank=True, on_delete=models.SET_NULL)
    reported_by_staff = models.ForeignKey(Staff, related_name='reported_issues', null=True, blank=True, on_delete=models.SET_NULL)
    issue_description = models.TextField()
    date_reported = models.DateTimeField(default=timezone.now)
    action_taken = models.TextField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    issue_file = models.FileField(upload_to='discipline_issues/', null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.issue_description[:20]}"

class Action(models.Model):
    discipline_issue = models.ForeignKey(DisciplineIssue, related_name='actions', on_delete=models.CASCADE)
    action_description = models.TextField()
    date_taken = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Action for {self.discipline_issue}"


class Action(models.Model):
    discipline_issue = models.ForeignKey(DisciplineIssue, related_name='actions', on_delete=models.CASCADE)
    action_description = models.TextField()
    date_taken = models.DateTimeField(default=timezone.now)
    action_taker = models.ForeignKey(Staff, on_delete=models.CASCADE)

    def __str__(self):
        return f"Action by {self.action_taker}"
