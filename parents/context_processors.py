# context_processors.py
from apps.students.models import Student

def student_context(request):
    if request.user.is_authenticated and hasattr(request.user, 'parentuser'):
        parent = request.user.parentuser
        students = Student.objects.filter(parent_student_id=parent.id)  # or use the correct field
        student = students.first() if students.exists() else None
        return {'student': student}
    return {}
