from django.urls import path
from .views import (
    HeadteacherDashboardView,
    HeadteacherStudentListView,
    HeadteacherStudentDetailView,
    HeadteacherStudentCreateView,
    HeadteacherStudentUpdateView,
    HeadteacherStudentDeleteView,
    HeadteacherAssignStudentsToTermView,
    HeadteacherHistoricalTermAssignmentsView,
)

urlpatterns = [
    path("", HeadteacherDashboardView.as_view(), name="headteacher_dashboard"),
    path("students/", HeadteacherStudentListView.as_view(), name="headteacher_student_list"),
    path("students/<int:pk>/", HeadteacherStudentDetailView.as_view(), name="headteacher_student_detail"),
    path("students/create/", HeadteacherStudentCreateView.as_view(), name="headteacher_student_create"),
    path("students/<int:pk>/update/", HeadteacherStudentUpdateView.as_view(), name="headteacher_student_update"),
    path("students/<int:pk>/delete/", HeadteacherStudentDeleteView.as_view(), name="headteacher_student_delete"),
    path("students/assign-term/", HeadteacherAssignStudentsToTermView.as_view(), name="headteacher_assign_term"),
    path("students/<int:pk>/historical-terms/", HeadteacherHistoricalTermAssignmentsView.as_view(), name="headteacher_historical_term_assignments"),
]