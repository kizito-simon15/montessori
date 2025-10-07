from django.urls import path
from .views import (
    academic_dashboard, academic_profile, academic_logout, academic_details, academic_salary_invoices, create_academic_results_view, edit_academic_results, academic_class_list, academic_class_results, academic_all_class_list, academic_all_class_results, student_infos_form_view, academic_form_results_view, AcademicStudentListView, AcademicInactiveStudentsView, AcademicCompletedStudentsView, AcademicCompletedStudentDetailView, AcademicStaffListView, AcademicStudentResultsView, AcademicSingleStudentResultsView, AcademicClassResultsView, AcademicFormStatusView, AcademicSingleClassResultsView, AcademicLibraryActionView, AcademicAddBookView, AcademicViewAvailableBooksView,
    AcademicIssueNewBookView, AcademicMarkBookReturnedView, AcademicIssuedStudentsView,
    AcademicViewIssuedBooksView, AcademicIssueStaffBookView,
    AcademicIssuedStaffsView, AcademicViewIssuedStaffsView, AcademicMarkStaffReturnedView,
    AcademicUpdateBookView, AcademicBookDetailView,
    AcademicDeleteBookView, AcademicAddStationeryView, AcademicStationeryListView,
    AcademicStationeryDetailView, AcademicStationeryUpdateView, AcademicStationeryDeleteView, AcademicEventListView, academicpick, mark_parent_comment_as_read, mark_academic_attendance
)

from . import views

urlpatterns = [
    # Academic Dashboard and Profile
    path('academic/pick/', academicpick, name='academic_pick'),
    path('academic/dashboard/', academic_dashboard, name='academic_dashboard'),
    path('academic/profile/', academic_profile, name='academic_profile'),
    path('academic/logout/', academic_logout, name='academic_logout'),
    path('academic/details/', academic_details, name='academic_details'),
    path('academic/salary/invoices/', academic_salary_invoices, name='academic_salary_invoices'),

    # Academic Results
    path('create/academic/results/', create_academic_results_view, name='create_academic_results_view'),
    path('edit_academic_results/', edit_academic_results, name='edit_academic_results'),
    path('class-results/<int:class_id>/', academic_form_results_view, name='academic_form_results_view'),
    path('academic-form-status/<int:class_id>/', AcademicFormStatusView.as_view(), name='academic_form_status'),
    path('academic/class/results/<int:class_id>/', AcademicClassResultsView.as_view(), name='academic-class-results'),
    path('academic/single/class/result/<int:class_id>/', AcademicSingleClassResultsView.as_view(), name='academic-single-results'),
    path('academic/single/student/results/<int:student_id>/', AcademicSingleStudentResultsView.as_view(), name='academic-single-student'),
    path('academic/student/<int:student_id>/results/', AcademicStudentResultsView.as_view(), name='academic-student-results'),

    # Academic Classes
    path('academics/classes/', academic_class_list, name='academic_class_list'),
    path('academics/classes/<int:class_id>/results/', academic_class_results, name='academic_class_results'),
    path('all/academics/classes/', academic_all_class_list, name='academic_all_class_list'),
    path('all/academics/classes/<int:class_id>/results/', academic_all_class_results, name='academic_all_class_results'),

    # Student Information
    path('student-info/<int:student_id>/', student_infos_form_view, name='student_infos_form_view'),
    path('academic/students/list/', AcademicStudentListView.as_view(), name='academic-student-list'),
    path('academic/inactive/students/', AcademicInactiveStudentsView.as_view(), name='academic-inactive-student-list'),
    path('academic-completed-students/', AcademicCompletedStudentsView.as_view(), name='academic-completed-students'),
    path('academic-completed/student/<int:pk>/', AcademicCompletedStudentDetailView.as_view(), name='academic-completed-student-detail'),

    # Staff Information
    path('staffs/academic/staff/list/', AcademicStaffListView.as_view(), name='academic-staff-list'),

    # Library Actions
    path('academic_library_action/', AcademicLibraryActionView.as_view(), name='academic_library_action'),
    path('academic_issued_students/', AcademicIssuedStudentsView.as_view(), name='academic_issued_students'),
    path('academic_issued_staffs/', AcademicIssuedStaffsView.as_view(), name='academic_issued_staffs'),
    path('academic_add_book/', AcademicAddBookView.as_view(), name='academic_add_book'),
    path('academic_view_available_books/', AcademicViewAvailableBooksView.as_view(), name='academic_view_available_books'),
    path('academic_issue_new_book/', AcademicIssueNewBookView.as_view(), name='academic_issue_new_book'),
    path('academic_mark_book_returned/<int:issued_book_id>/', AcademicMarkBookReturnedView.as_view(), name='academic_mark_book_returned'),
    path('academic_mark_staff_returned/<int:issued_book_id>/', AcademicMarkStaffReturnedView.as_view(), name='academic_mark_staff_returned'),
    path('academic_view_issued_books/', AcademicViewIssuedBooksView.as_view(), name='academic_view_issued_books'),
    path('academic_delete_issued_book/<int:issued_book_id>/', views.academic_delete_issued_book, name='academic_delete_issued_book'),
    path('academic_delete_issued_staff/<int:issued_book_id>/', views.academic_delete_issued_staff, name='academic_delete_issued_staff'),
    path('academic_issue_new_staff/', AcademicIssueStaffBookView.as_view(), name='academic_issue_new_staff'),
    path('academic_view_issued_staffs/', AcademicViewIssuedStaffsView.as_view(), name='academic_view_issued_staffs'),

    # Book Management
    path('academic_update_book/<int:book_id>/', AcademicUpdateBookView.as_view(), name='academic_update_book'),
    path('academic_book_detail/<int:book_id>/', AcademicBookDetailView.as_view(), name='academic_book_detail'),
    path('academic_delete_book/<int:book_id>/', AcademicDeleteBookView.as_view(), name='academic_delete_book'),

    # Stationery Management
    path('academic_add_stationery/', AcademicAddStationeryView.as_view(), name='academic_add_stationery'),
    path('academic_stationery_list/', AcademicStationeryListView.as_view(), name='academic_stationery_list'),
    path('academic_stationery_detail/<int:stationery_id>/', AcademicStationeryDetailView.as_view(), name='academic_stationery_detail'),
    path('academic_stationery_update/<int:stationery_id>/', AcademicStationeryUpdateView.as_view(), name='academic_stationery_update'),
    path('academic_stationery_delete/<int:stationery_id>/', AcademicStationeryDeleteView.as_view(), name='academic_stationery_delete'),
    path('academic/properties/', views.academic_property_list, name='academic_property_list'),
    path('academic/properties/<int:pk>/', views.academic_property_detail, name='academic_property_detail'),
    
    # events
    path('academic/event/list/', AcademicEventListView.as_view(), name='academic_event_list'),
    path('academic-parent-comments/', views.academic_parent_comments_view, name='academic_parent_comments_view'),
    path('save-academic-answer/', views.save_academic_answer, name='save_academic_answer'),
    path('parent-comments/mark-read/<int:comment_id>/', mark_parent_comment_as_read, name='mark_parent_comment_as_read'),
    path('dashboard/academic/mark-attendance/', mark_academic_attendance, name='mark_academic_attendance'),
    path('edit-academic-answer/<int:answer_id>/', views.edit_academic_answer, name='edit_academic_answer'),
]
