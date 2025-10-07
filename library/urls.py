from django.urls import path
from .views import (
    LibraryActionView, AddBookView, ViewAvailableBooksView, 
    IssueNewBookView, MarkBookReturnedView, IssuedStudentsView, 
    ViewIssuedBooksView, IssueStaffBookView, 
    IssuedStaffsView, ViewIssuedStaffsView, MarkStaffReturnedView, 
    UpdateBookView, BookDetailView, 
    DeleteBookView, AddStationeryView, StationeryListView, 
    StationeryDetailView, StationeryUpdateView, StationeryDeleteView,
)

from . import views

urlpatterns = [
    path('library_action/', LibraryActionView.as_view(), name='library_action'),
    path('issued_students/', IssuedStudentsView.as_view(), name='issued_students'),
    path('issued_staffs/', IssuedStaffsView.as_view(), name='issued_staffs'),
    path('add_stationery/', AddStationeryView.as_view(), name='add_stationery'),
    path('add_book/', AddBookView.as_view(), name='add_book'),
    path('view_available_books/', ViewAvailableBooksView.as_view(), name='view_available_books'),
    path('issue_new_book/', IssueNewBookView.as_view(), name='issue_new_book'),
    path('mark_book_returned/<int:issued_book_id>/', MarkBookReturnedView.as_view(), name='mark_book_returned'),
    path('mark_staff_returned/<int:issued_book_id>/', MarkStaffReturnedView.as_view(), name='mark_staff_returned'),
    path('view_issued_books/', ViewIssuedBooksView.as_view(), name='view_issued_books'),
    path('delete_issued_book/<int:issued_book_id>/', views.delete_issued_book, name='delete_issued_book'),
    path('delete_issued_staff/<int:issued_book_id>/', views.delete_issued_staff, name='delete_issued_staff'),
    path('issue_new_staff/', IssueStaffBookView.as_view(), name='issue_new_staff'),
    path('view_issued_staffs/', ViewIssuedStaffsView.as_view(), name='view_issued_staffs'),
    path('update_book/<int:book_id>/', UpdateBookView.as_view(), name='update_book'),
    path('book_detail/<int:book_id>/', BookDetailView.as_view(), name='book_detail'),
    path('delete_book/<int:book_id>/', DeleteBookView.as_view(), name='delete_book'),
    #path('student_detail/<int:student_id>/', views.student_detail, name='student_detail'),
    path('stationery_list/', StationeryListView.as_view(), name='stationery_list'),
    path('stationery_detail/<int:stationery_id>/', StationeryDetailView.as_view(), name='stationery_detail'),
    path('stationery_update/<int:stationery_id>/', StationeryUpdateView.as_view(), name='stationery_update'),
    path('stationery_delete/<int:stationery_id>/', StationeryDeleteView.as_view(), name='stationery_delete'),
]
