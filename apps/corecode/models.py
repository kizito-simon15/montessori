from django.conf import settings
from django.db import models


# -------------------------
# Site settings / taxonomy
# -------------------------

class SiteConfig(models.Model):
    """Key-value configuration for site-wide flags and texts."""
    key = models.SlugField(max_length=64, unique=True)
    value = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "Site configuration"
        verbose_name_plural = "Site configurations"

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"


class AcademicSession(models.Model):
    """Academic Session (e.g., 2024/2025)."""
    name = models.CharField(max_length=200, unique=True)
    current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-name"]

    def __str__(self) -> str:
        return self.name


class AcademicTerm(models.Model):
    """Academic Term (e.g., Term I)."""
    name = models.CharField(max_length=20, unique=True)
    current = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ExamType(models.Model):
    """Exam Type (e.g., Midterm, Final, Mock)."""
    name = models.CharField(max_length=50, unique=True)
    current = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Installment(models.Model):
    """Fee installment names (e.g., First, Second)."""
    name = models.CharField(max_length=50, unique=True)
    current = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Subject(models.Model):
    """School subjects."""
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StudentClass(models.Model):
    """A class/stream e.g., Grade 1, Standard III Blue."""
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Signature(models.Model):
    """Named signature image for reports/certificates."""
    name = models.CharField(max_length=255)
    signature_image = models.ImageField(upload_to="signatures/")

    def __str__(self) -> str:
        return self.name


# -------------------------------------------
# Future Plans → Project Updates (Uploads)
# -------------------------------------------

class ProjectAlbum(models.Model):
    """
    Optional grouping for project photos (e.g., 'New Campus 2025').
    Keep one default album active if you don't want multiple.
    """
    title = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, help_text="Short identifier used in URLs (e.g., 'new-campus-2025').")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Project album"
        verbose_name_plural = "Project albums"

    def __str__(self) -> str:
        return self.title


def project_photo_upload_to(instance: "ProjectPhoto", filename: str) -> str:
    """
    Store photos under /media/project_photos/YYYY/MM/DD/<filename>
    Grouped by album slug if you want (kept simple here).
    """
    return f"project_photos/%Y/%m/%d/{filename}"


class ProjectPhoto(models.Model):
    """
    Actual uploaded images displayed in 'Project Updates'.
    Hook this to your form/view (project_upload) to save.
    """
    album = models.ForeignKey(
        ProjectAlbum,
        related_name="photos",
        on_delete=models.CASCADE,
        help_text="Choose an album to group related photos."
    )
    image = models.ImageField(upload_to="project_photos/%Y/%m/%d/")
    caption = models.CharField(max_length=140, blank=True)

    # Optional: who uploaded the photo
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_project_photos",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Project photo"
        verbose_name_plural = "Project photos"

    def __str__(self) -> str:
        if self.caption:
            return f"{self.caption} ({self.created_at:%Y-%m-%d})"
        return f"Photo {self.pk} ({self.created_at:%Y-%m-%d})"
