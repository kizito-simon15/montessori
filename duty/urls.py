# apps/staffs/urls.py

from django.urls import path
from .views import assign_staff_role, staff_role_list, update_staff_role, delete_staff_role, update_class_teacher, delete_class_teacher, daily_schedule_list, create_schedule

from . import views

urlpatterns = [
    path('assign-staff-role/', assign_staff_role, name='assign-staff-role'),
    path('staff-role-list/', staff_role_list, name='staff-role-list'),
    path('update-staff-role/<int:role_id>/', update_staff_role, name='update-staff-role'),
    path('delete-staff-role/<int:role_id>/', delete_staff_role, name='delete-staff-role'),
    path('update-class-teacher/<int:role_id>/', update_class_teacher, name='update-class-teacher'),
    path('delete-class-teacher/<int:role_id>/', delete_class_teacher, name='delete-class-teacher'),
    path('daily/schedule/list', daily_schedule_list, name='daily-schedule-list'),
    path('create-schedule/', create_schedule, name='create-schedule'),
    path('update-schedule/<int:day_id>/', views.update_schedule, name='update-schedule'),
    path('delete-schedule/<int:day_id>/', views.delete_schedule, name='delete-schedule'),
    path('delete-class-schedule/<int:day_id>/<int:class_schedule_id>/', views.delete_class_schedule, name='delete-class-schedule'),
    path('update-class-schedule/<int:day_id>/<int:class_schedule_id>/', views.update_class_schedule, name='update-class-schedule'),
]
