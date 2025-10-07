from django.urls import path
from . import views

# In urls.py
urlpatterns = [
    path('properties/', views.property_list, name='property_list'),
    path('properties/<int:pk>/', views.property_detail, name='property_detail'),
    path('add-property/', views.add_property, name='add_property'),
    path('properties/<int:pk>/update/', views.update_property, name='update_property'),
    path('properties/<int:pk>/delete/', views.delete_property, name='delete_property'),
]
