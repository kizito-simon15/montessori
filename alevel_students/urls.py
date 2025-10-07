from django.urls import path
from .views import (
    ALevelStudentListView,
    ActiveALevelStudentListView,
    InactiveALevelStudentsView,
    SelectALevelClassView,
    CompletedALevelStudentsView,
    CompletedALevelStudentDetailView,
    ALevelStudentDetailView,
    ALevelStudentCreateView,
    ALevelStudentUpdateView,
    ALevelStudentDeleteView,
    ALevelStudentBulkUploadView,
    ALevelDownloadCSVView,
)

app_name = 'alevel_students'

urlpatterns = [
    path('list/', ALevelStudentListView.as_view(), name='alevel-student-list'),
    path('active/', ActiveALevelStudentListView.as_view(), name='active-alevel-student-list'),
    path('inactive/', InactiveALevelStudentsView.as_view(), name='inactive-alevel-student-list'),
    path('select-class/', SelectALevelClassView.as_view(), name='select-alevel-class'),
    path('completed/', CompletedALevelStudentsView.as_view(), name='completed-alevel-students'),
    path('completed/<int:pk>/', CompletedALevelStudentDetailView.as_view(), name='completed-alevel-student-detail'),
    path('<int:pk>/', ALevelStudentDetailView.as_view(), name='alevel-student-detail'),
    path('create/', ALevelStudentCreateView.as_view(), name='alevel-student-create'),
    path('<int:pk>/update/', ALevelStudentUpdateView.as_view(), name='alevel-student-update'),
    path('<int:pk>/delete/', ALevelStudentDeleteView.as_view(), name='alevel-student-delete'),
    path('upload/', ALevelStudentBulkUploadView.as_view(), name='alevel-student-upload'),
    path('download-csv/', ALevelDownloadCSVView.as_view(), name='download-alevel-csv'),
]