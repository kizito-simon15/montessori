from django.db import models
from apps.students.models import Student 
#from parents.models import StudentComments
from accounts.models import ParentUser
# models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.students.models import Student 
#from parents.models import StudentComments

from django.db import models
from apps.students.models import Student
#from parents.models import StudentComments
from accounts.models import ParentUser

class SecretaryAnswers(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey(ParentUser, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)  # Allow blank text answers
    audio_answer = models.FileField(upload_to='secretary_audio_answers/', blank=True, null=True)  # Audio field
    date_commented = models.DateTimeField(auto_now_add=True)
    date_updated_comments = models.DateTimeField(auto_now=True)
    mark_student_comment = models.BooleanField(default=False)
    #comment = models.OneToOneField(StudentComments, on_delete=models.CASCADE)
    mark_secretary_answer = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer for {self.student.firstname} {self.student.surname} by {self.parent.username}"

class SecretaryNotification(models.Model):
    secretary = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    #comment = models.OneToOneField(StudentComments, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.secretary.username} - Comment {self.comment.id}"
