from django.urls import path
from .views import (
    parent_student_details, parent_student_invoices, parent_dashboard,
    parent_invoice_detail, parent_student_details_all, update_comment,
    delete_comment, edit_student_comment, delete_student_comment, edit_comment,
    delete_result_comment, all_parents_comments_view, parent_uniform_list, help_view
)

from . import views

urlpatterns = [
    path('dashboard/', parent_dashboard, name='parent_dashboard'),
    path('parent/student/details/<int:student_id>/', parent_student_details, name='parent_student_details'),
    path('invoice/<int:pk>/', parent_invoice_detail, name='parent_invoice_detail'),
    path('student/invoices/', parent_student_invoices, name='parent_student_invoices'),
    path('parent/student/details/all/', parent_student_details_all, name='parent_student_details_all'),
    path('parents/update_comment/<int:comment_id>/', update_comment, name='update_comment'),
    path('parents/delete_comment/<int:comment_id>/', delete_comment, name='delete_comment'),
    path('edit_student_comment/<int:comment_id>/', edit_student_comment, name='edit_student_comment'),
    path('delete_student_comment/<int:comment_id>/', delete_student_comment, name='delete_student_comment'),
    path('results/edit_comment/<int:comment_id>/', edit_comment, name='edit_comment'),
    path('results/delete_comment/<int:comment_id>/', delete_result_comment, name='delete_result_comment'),
    path('update_comment/<int:comment_id>/', views.update_details_comment, name='update_details_comment'),
    path('delete_comment/<int:comment_id>/', views.delete_details_comment, name='delete_details_comment'),
    path('update_invoice_comment/<int:comment_id>/', views.update_invoice_comment, name='update_invoice_comment'),
    path('delete_invoice_comment/<int:comment_id>/', views.delete_invoice_comment, name='delete_invoice_comment'),
    path('all_comments/<int:student_id>/', views.all_comments_view, name='all_comments_view'),
    path('all/parents/comments', all_parents_comments_view, name='all_parents_comments'),
    path('parent/uniform/list', parent_uniform_list, name='parent_uniform_list'),
    path('mark-secretary-comment-as-read/<int:comment_id>/', views.mark_secretary_comment_as_read, name='mark_secretary_comment_as_read'),
    path('mark-academic-comment-as-read/<int:comment_id>/', views.mark_academic_comment_as_read, name='mark_academic_comment_as_read'),
    path('mark-invoice-comment-as-read/<int:comment_id>/', views.mark_invoice_comment_as_read, name='mark_invoice_comment_as_read'),
    path('help/', help_view, name='help_view'),
    path('update-invoice-comment/<int:comment_id>/', views.update_invoice_comment, name='update_invoice_comment'),
    path('update-student-comment/<int:comment_id>/', views.update_student_comment, name='update_student_comment'),
    path('delete-text-comment/<int:comment_id>/', views.delete_text_comment, name='delete_text_comment'),
    path('delete-audio-comment/<int:comment_id>/', views.delete_audio_comment, name='delete_audio_comment'),
]
