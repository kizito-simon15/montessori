from .models import AcademicSession, AcademicTerm, ExamType, Installment, SiteConfig

def site_defaults(request):
    contexts = {
        "current_session": "N/A",
        "current_term": "N/A",
        "current_exam": "N/A",
        "current_install": "N/A",
    }
    
    current_session = AcademicSession.objects.filter(current=True).first()
    if current_session:
        contexts["current_session"] = current_session.name
    
    current_term = AcademicTerm.objects.filter(current=True).first()
    if current_term:
        contexts["current_term"] = current_term.name
    
    current_exam = ExamType.objects.filter(current=True).first()
    if current_exam:
        contexts["current_exam"] = current_exam.name
    
    current_install = Installment.objects.filter(current=True).first()
    if current_install:
        contexts["current_install"] = current_install.name
    
    vals = SiteConfig.objects.all()
    for val in vals:
        contexts[val.key] = val.value

    return contexts