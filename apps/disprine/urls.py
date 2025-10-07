# apps/disprine/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.discipline_issue_list, name='discipline_issue_list'),
    path('<int:student_id>/', views.discipline_issue_detail, name='discipline_issue_detail'),
    path('new/', views.discipline_issue_create, name='discipline_issue_create'),
    path('<int:pk>/edit/', views.discipline_issue_update, name='discipline_issue_update'),
    path('<int:pk>/delete/', views.discipline_issue_delete, name='discipline_issue_delete'),
    path('<int:issue_id>/action/', views.action_create, name='action_create'),
]
