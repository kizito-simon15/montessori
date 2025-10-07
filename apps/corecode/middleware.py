from .models import AcademicSession, AcademicTerm, ExamType, Installment
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

class SiteWideConfigs:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            current_session = AcademicSession.objects.get(current=True)
            current_term = AcademicTerm.objects.get(current=True)
            current_exam = ExamType.objects.get(current=True)
            current_install = Installment.objects.filter(current=True)
            if current_install.exists():
                # If there are multiple current installments, take the first one
                current_install = current_install.first()
            else:
                current_install = None
        except ObjectDoesNotExist:
            # Handle the case where one of the objects does not exist
            # Log the error or provide a default behavior
            current_session = None
            current_term = None
            current_exam = None
            current_install = None
        except MultipleObjectsReturned:
            # Handle the case where multiple current installments exist
            # Log the error or provide a default behavior
            current_install = None

        request.current_session = current_session
        request.current_term = current_term
        request.current_exam = current_exam
        request.current_install = current_install

        response = self.get_response(request)

        return response
