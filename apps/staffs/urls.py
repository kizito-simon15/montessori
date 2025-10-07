from django.urls import path
from .views import (
    StaffListView, InactiveStaffListView, StaffDetailView, StaffCreateView,
    StaffUpdateView, StaffDeleteView, staff_attendance_report
)

urlpatterns = [
    path('staff/', StaffListView.as_view(), name='staff-list'),
    path('staff/inactive/', InactiveStaffListView.as_view(), name='inactive-staff-list'),
    path('staff/<int:pk>/', StaffDetailView.as_view(), name='staff-detail'),
    path('staff/create/', StaffCreateView.as_view(), name='staff-create'),
    path('staff/<int:pk>/update/', StaffUpdateView.as_view(), name='staff-update'),  # Added missing comma here
    path('staff/<int:pk>/delete/', StaffDeleteView.as_view(), name='staff-delete'),
    path('staff/attendance-report/', staff_attendance_report, name='staff-attendance-report'),
]

