# meetings/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

CustomUser = settings.AUTH_USER_MODEL  # Reference to your custom user model

from django.db import models
from django.conf import settings
from django.utils import timezone

CustomUser = settings.AUTH_USER_MODEL  # Reference to your custom user model

class Meeting(models.Model):
    title = models.CharField(max_length=255)
    host = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='hosted_meetings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)  # Indicates if the meeting is ongoing
    is_past = models.BooleanField(default=False)    # Indicates if the meeting is marked as past
    created_at = models.DateTimeField(auto_now_add=True)
    meeting_url = models.URLField(max_length=500, blank=True, null=True)  # Stores the unique meeting URL

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Generate meeting URL if it does not exist
        if not self.meeting_url:
            self.meeting_url = f"https://meet.jit.si/{self.title}-{self.id}"
        super(Meeting, self).save(*args, **kwargs)


class Agenda(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="agendas")
    description = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f"{self.description} for {self.meeting.title}"

class Participant(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='participants')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_admin_invited = models.BooleanField(default=False)  # Indicates if admin invited this participant
    has_video = models.BooleanField(default=False)  # Tracks video participation
    has_audio = models.BooleanField(default=False)  # Tracks audio participation

    def __str__(self):
        return f"{self.user.username} in {self.meeting.title}"

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} - {self.meeting.title}"
