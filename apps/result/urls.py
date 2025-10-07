from django.urls import path
from .views import create_result, edit_results, StudentResultsView, ClassListView, ClassResultsView, SingleClassResultsView, SingleClassListView, SingleStudentResultsView, FormStatusView, admin_profile, edit_now_results, delete_page_results

urlpatterns = [
    path("create/", create_result, name="create-result"),
    path("edit-results/", edit_results, name="edit-results"),
    path("edit-now-results/", edit_now_results, name="edit-now-results"),
    path('delete-page-results/', delete_page_results, name='delete-page-results'),
    path('student/results/', StudentResultsView.as_view(), name='student-results'),  # Removed student_id for now
    path('form-status/', FormStatusView.as_view(), name='form_status'),  # Removed class_id for now
    path('class/', ClassListView.as_view(), name='class-list'),
    path('class/results/', ClassResultsView.as_view(), name='class-results'),  # Removed class_id for now
    path('single/class/list', SingleClassListView.as_view(), name='single-class'),
    path('single/class/result/', SingleClassResultsView.as_view(), name='single-results'),  # Removed class_id for now
    path('single/student/results/', SingleStudentResultsView.as_view(), name='single-student'),  # Removed student_id for now
    path('admin/profile/', admin_profile, name='admin_profile'),
]