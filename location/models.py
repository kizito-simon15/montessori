from django.db import models

DAYS_OF_WEEK = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
    ('Sunday', 'Sunday'),
]

class SchoolLocation(models.Model):
    name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=40, decimal_places=35, blank=True, null=True)
    longitude = models.DecimalField(max_digits=40, decimal_places=35, blank=True, null=True)
    start_day = models.CharField(max_length=10, choices=DAYS_OF_WEEK, default='Monday')
    end_day = models.CharField(max_length=10, choices=DAYS_OF_WEEK, default='Friday')
    start_time = models.TimeField(default='07:00')
    end_time = models.TimeField(default='19:00')
    is_active = models.BooleanField(default=False)
    distance = models.DecimalField(max_digits=30, decimal_places=10, blank=True, null=True)  # New field

    def __str__(self):
        return self.name
