from django.urls import path
from .views import set_school_location, location_details, update_location, location_list, delete_location, activate_location, deactivate_location

urlpatterns = [
    path('set-school-location/', set_school_location, name='set_school_location'),
    path('location-details/<int:pk>/', location_details, name='location_details'),
    path('update-location/<int:pk>/', update_location, name='update_location'),
    path('location-list/', location_list, name='location_list'),  # New URL pattern for listing locations
    path('delete-location/<int:pk>/', delete_location, name='delete_location'),
    path('activate-location/<int:pk>/', activate_location, name='activate_location'),
    path('deactivate-location/<int:pk>/', deactivate_location, name='deactivate_location'),
]
