from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


# ──────────────────────────────────────────────
# Custom User Manager
# ──────────────────────────────────────────────
class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra_fields)


# ──────────────────────────────────────────────
# Base User
# ──────────────────────────────────────────────
class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="en",
    )
    profile_picture = models.ImageField(
        upload_to="profile_pics/",
        null=True,
        blank=True,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "username"

    def __str__(self):
        return self.username


# ──────────────────────────────────────────────
# Profile model (extra info not in auth table)
# ──────────────────────────────────────────────
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    role = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


# ──────────────────────────────────────────────
# Auto-create / update profile
# ──────────────────────────────────────────────
@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Only save if a profile already exists
        if hasattr(instance, "profile"):
            instance.profile.save()


# ──────────────────────────────────────────────
# Role-based subclasses
# ──────────────────────────────────────────────
class ParentUser(CustomUser):
    student = models.OneToOneField(
        "students.Student",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    parent_first_name = models.CharField(max_length=200, blank=True, null=True)
    parent_middle_name = models.CharField(max_length=200, blank=True, null=True)
    parent_last_name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return (
            f"{self.parent_first_name or ''} {self.parent_last_name or ''}".strip()
            or self.username
        )


class TeacherUser(CustomUser):
    staff = models.OneToOneField(
        "staffs.Staff",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username


class BursorUser(CustomUser):
    staff = models.OneToOneField(
        "staffs.Staff",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username


class SecretaryUser(CustomUser):
    staff = models.OneToOneField(
        "staffs.Staff",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username


class AcademicUser(CustomUser):
    staff = models.OneToOneField(
        "staffs.Staff",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username


class HeadTeacherUser(CustomUser):
    staff = models.OneToOneField(
        "staffs.Staff",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username
