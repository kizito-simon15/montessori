from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AcademicSession, AcademicTerm, ExamType, Installment
from apps.students.models import Student, StudentClass
from django.db import transaction
import re
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=AcademicSession)
def after_saving_session(sender, created, instance, *args, **kwargs):
    """Update other sessions to non-current when a new session is set as current."""
    if instance.current:
        with transaction.atomic():
            # Set other sessions to non-current
            other_sessions = AcademicSession.objects.exclude(pk=instance.id)
            other_sessions.update(current=False)
            logger.info(f"Set {instance.name} as current session; other sessions updated to non-current.")

@receiver(post_save, sender=AcademicTerm)
def after_saving_term(sender, created, instance, *args, **kwargs):
    """Change all academic terms to false if this is true."""
    if instance.current:
        AcademicTerm.objects.exclude(pk=instance.id).update(current=False)
        logger.info(f"Set {instance.name} as current term; other terms updated to non-current.")

@receiver(post_save, sender=ExamType)
def after_saving_exam(sender, created, instance, *args, **kwargs):
    """Change all exam types to false if this is true."""
    if instance.current:
        ExamType.objects.exclude(pk=instance.id).update(current=False)
        logger.info(f"Set {instance.name} as current exam type; other exam types updated to non-current.")

@receiver(post_save, sender=Installment)
def after_saving_install(sender, created, instance, *args, **kwargs):
    """Change all installments to false if this is true."""
    if instance.current:
        Installment.objects.exclude(pk=instance.id).update(current=False)
        logger.info(f"Set {instance.name} as current installment; other installments updated to non-current.")