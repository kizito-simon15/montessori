from django.urls import path

from .views import (
    NonStaffCreateView,
    NonStaffDeleteView,
    NonStaffDetailView,
    NonStaffListView,
    NonStaffUpdateView
)

urlpatterns = [
    path("non/list/", NonStaffListView.as_view(), name="non-staff-list"),
    path("<int:pk>/", NonStaffDetailView.as_view(), name="non-staff-detail"),
    path("non/create/", NonStaffCreateView.as_view(), name="non-staff-create"),
    path("<int:pk>/non/update/", NonStaffUpdateView.as_view(), name="non-staff-update"),
    path("<int:pk>/non/delete/", NonStaffDeleteView.as_view(), name="non-staff-delete"),
]
