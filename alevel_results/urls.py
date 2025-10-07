from django.urls import path
from . import views

app_name = 'alevel_results'

urlpatterns = [
    path('create/', views.create_result, name='create_result'),
    path('edit/', views.edit_results, name='edit_results'),
    path('edit-now/', views.edit_now_results, name='edit_now_results'),
    path('delete-page/', views.delete_page_results, name='delete_page_results'),
    path('student/<int:student_id>/', views.ALevelStudentResultsView.as_view(), name='student_results'),
    path('form-status/<int:class_id>/', views.ALevelFormStatusView.as_view(), name='form_status'),
    path('class-results/<int:class_id>/', views.ALevelClassResultsView.as_view(), name='class_results'),
    path('class-list/', views.ALevelClassListView.as_view(), name='class_list'),
    path('single-results/<int:class_id>/', views.ALevelSingleClassResultsView.as_view(), name='single_results'),
    path('single-class/', views.ALevelSingleClassListView.as_view(), name='single_class'),
    path('single-student/<int:student_id>/', views.ALevelSingleStudentResultsView.as_view(), name='single_student_results'),
    path('admin-profile/', views.admin_profile, name='admin_profile'),
]
