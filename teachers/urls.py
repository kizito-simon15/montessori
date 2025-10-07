from django.urls import path
from .views import (
    teacher_dashboard, teacher_profile, teacher_logout, teacher_details, teacher_salary_invoices, teacher_class_list, teacher_class_results, all_class_list, all_class_results, TeachersStudentListView, TeachersStaffListView, TeachersEventListView, TeachersViewAvailableBooksView, TeachersBookDetailView, TeacherStudentListView, TeacherInactiveStudentsView, TeacherCompletedStudentsView, mark_teacher_attendance
)

urlpatterns = [
    path('teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('teacher/profile/', teacher_profile, name='teacher_profile'),
    path('teacher/logout/', teacher_logout, name='teacher_logout'),
    path('teacher/details/', teacher_details, name='teacher_details'),
    path('teacher/salary/invoices/', teacher_salary_invoices, name='teacher_salary_invoices'),
    path('classes/', teacher_class_list, name='teacher_class_list'),
    path('classes/<int:class_id>/results/', teacher_class_results, name='teacher_class_results'),
    path('all/classes/', all_class_list, name='all_class_list'),
    path('all/classes/<int:class_id>/results/', all_class_results, name='all_class_results'),
    path("teachers/students/list", TeachersStudentListView.as_view(), name="teachers-student-list"),
    path("teachers/staff/list/", TeachersStaffListView.as_view(), name="teachers-staff-list"),
    path('teachers/event/list/', TeachersEventListView.as_view(), name='teachers_event_list'),
    path('teachers_view_available_books/', TeachersViewAvailableBooksView.as_view(), name='teachers_view_available_books'),
    path('teachers_book_detail/<int:book_id>/', TeachersBookDetailView.as_view(), name='teachers_book_detail'),
    path("teachers/students/list", TeacherStudentListView.as_view(), name="teachers-student-list"),
    path('teachers-inactive-students/', TeacherInactiveStudentsView.as_view(), name='teachers-inactive-student-list'),
    path('teachers-completed-students/', TeacherCompletedStudentsView.as_view(), name='teachers-completed-student-list'),
    path('dashboard/teacher/mark-attendance/', mark_teacher_attendance, name='mark_teacher_attendance'),
]