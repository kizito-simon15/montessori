from django.urls import path
from . import views

urlpatterns = [
    path('select-class/', views.select_class, name='select_class'),
    path('take-attendance/<int:class_id>/', views.take_attendance, name='take_attendance'),
    path('selecting-class/', views.selecting_class, name='selecting_class'),
    path('class-attendance/<int:class_id>/', views.class_attendance, name='class_attendance'),
    path('view-attendance/<int:class_id>/<str:attendance_date>/', views.view_attendance, name='view_attendance'),
    path('pick-class/', views.pick_class, name='pick_class'),
    path('all-students/<int:class_id>/', views.all_students, name='all_students'),
    path('single-student/<int:class_id>/<int:student_id>/', views.single_student, name='single_student'),
    # existing URLs...
]
