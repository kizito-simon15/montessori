from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View
from django.urls import reverse
from .models import Book, IssuedBook, IssuedStaff, Stationery
from .forms import BookForm, IssueBookForm, IssueStaffForm, StationeryForm
from apps.students.models import Student
from apps.staffs.models import Staff
from apps.corecode.models import AcademicSession, StudentClass
from django.shortcuts import render
from .models import Book
from collections import defaultdict
from django.db.models import Sum
from itertools import groupby
from operator import attrgetter
from datetime import datetime

class LibraryActionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'library.view_book'

    def get(self, request):
        return render(request, 'library_actions.html')

class AddBookView(View):
    def get(self, request):
        form = BookForm()
        return render(request, 'add_book.html', {'form': form})

    def post(self, request):
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            current_session = AcademicSession.objects.get(current=True)
            book.session = current_session
            book.save()
            messages.success(request, 'New book added successfully')
            return redirect('add_book')
        return render(request, 'add_book.html', {'form': form})

class ViewAvailableBooksView(View):
    def get(self, request):
        books_by_class = Book.objects.all().order_by('student_class')
        grouped_books = {}
        for book in books_by_class:
            if book.student_class.name not in grouped_books:
                grouped_books[book.student_class.name] = []
            grouped_books[book.student_class.name].append(book)
        return render(request, 'view_books.html', {'grouped_books': grouped_books})



class IssueNewBookView(View):
    def get(self, request):
        students = Student.objects.all()
        books = Book.objects.all()
        form = IssueBookForm()
        return render(request, 'issue_book.html', {'form': form, 'students': students, 'books': books})

    def post(self, request):
        students = Student.objects.all()
        books = Book.objects.all()
        form = IssueBookForm(request.POST)
        if form.is_valid():
            issued_book = form.save(commit=False)
            issued_book.save()
            messages.success(request, 'The book was issued successfully')
            return redirect('issue_new_book')
        return render(request, 'issue_book.html', {'form': form, 'students': students, 'books': books})

class MarkBookReturnedView(View):
    def get(self, request, issued_book_id):
        issued_book = get_object_or_404(IssuedBook, id=issued_book_id)
        issued_book.returned = True
        issued_book.save()
        return redirect('view_issued_books')

class IssuedStudentsView(View):
    def get(self, request):
        issued_once_students = Student.objects.filter(issuedbook__isnull=False).distinct()
        return render(request, 'all_issued.html', {'issued_once_students': issued_once_students})

class ViewIssuedBooksView(View):
    def get(self, request):
        student_id = request.GET.get('student_id')
        student_name = None
        if student_id:
            student = Student.objects.get(pk=student_id)
            student_name = student.firstname + ' ' + student.other_name + ' ' + student.surname
            issued_books = IssuedBook.objects.filter(student=student)
        else:
            issued_books = IssuedBook.objects.all()
        return render(request, 'issued_books.html', {'issued_books': issued_books, 'student_name': student_name})

def delete_issued_book(request, issued_book_id):
    # Retrieve the issued book object or return 404 if not found
    issued_book = get_object_or_404(IssuedBook, id=issued_book_id)

    # Delete the issued book
    issued_book.delete()

    # Redirect to a success URL or any other page
    return redirect('view_issued_books')  # Redirect to the view_issued_books page after deletion

def delete_issued_staff(request, issued_book_id):
    # Retrieve the issued book object or return 404 if not found
    issued_books = get_object_or_404(IssuedStaff, id=issued_book_id)

    # Delete the issued book
    issued_books.delete()

    # Redirect to a success URL or any other page
    return redirect('view_issued_staffs')  # Redirect to the view_issued_staffs page after deletion

class IssueStaffBookView(View):
    def get(self, request):
        staffs = Staff.objects.all()
        books = Book.objects.all()
        student_classes = StudentClass.objects.all()
        authors = Book.objects.values_list('author', flat=True).distinct()
        form = IssueStaffForm()
        return render(request, 'issue_staff.html', {'form': form, 'staffs': staffs, 'books': books, 'student_classes': student_classes, 'authors': authors})

    def post(self, request):
        staffs = Staff.objects.all()
        student_classes = StudentClass.objects.all()
        book_name = request.POST.get('book_name')
        student_class_id = request.POST.get('student_class')
        author = request.POST.get('author')
        staff_name = request.POST.get('staff_name')
        books = Book.objects.all()
        authors = Book.objects.values_list('author', flat=True).distinct()

        if book_name:
            books = books.filter(book_name__icontains=book_name)
        if student_class_id:
            books = books.filter(student_class_id=student_class_id)
        if author:
            books = books.filter(author__icontains=author)
        if staff_name:
            staffs = staffs.filter(surname__icontains=staff_name) | staffs.filter(firstname__icontains=staff_name)

        form = IssueStaffForm(request.POST)
        if form.is_valid():
            issued_staff = form.save(commit=False)
            issued_staff.save()
            messages.success(request, 'The book was issued successfully')
            return redirect('issue_new_staff')
        return render(request, 'issue_staff.html', {'form': form, 'staffs': staffs, 'books': books, 'student_classes': student_classes, 'authors': authors})


class IssuedStaffsView(View):
    def get(self, request):
        issued_once_staffs = Staff.objects.filter(issuedstaff__isnull=False).distinct()
        return render(request, 'all_staff.html', {'issued_once_staffs': issued_once_staffs})

class ViewIssuedStaffsView(View):
    def get(self, request):
        staff_id = request.GET.get('staff_id')
        staff_name = None
        if staff_id:
            staff = Staff.objects.get(pk=staff_id)
            staff_name = staff.firstname + ' ' + staff.middle_name + ' ' + staff.surname
            issued_books = IssuedStaff.objects.filter(staff=staff)
        else:
            issued_books = IssuedStaff.objects.all()
        return render(request, 'issued_staffs.html', {'issued_books': issued_books, 'staff_name': staff_name})

class MarkStaffReturnedView(View):
    def get(self, request, issued_book_id):
        issued_book = get_object_or_404(IssuedStaff, id=issued_book_id)
        issued_book.returned = True
        issued_book.save()
        return redirect('view_issued_staffs')

class UpdateBookView(View):
    def get(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        student_classes = StudentClass.objects.all()
        return render(request, 'update_book.html', {'book': book, 'student_classes': student_classes})

    def post(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        book.description = request.POST.get('description')
        book.quantity = request.POST.get('quantity')
        book.category = request.POST.get('category')
        book.date_buyed = request.POST.get('date_buyed')  # Add this line to handle date_buyed
        class_id = request.POST.get('class')
        if class_id:
            book.student_class = StudentClass.objects.get(pk=class_id)
        book.save()
        student_classes = StudentClass.objects.all()
        return render(request, 'update_book.html', {'book': book, 'student_classes': student_classes, 'message': 'Book updated successfully'})

class BookDetailView(View):
    def get(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        return render(request, 'book_details.html', {'book': book})

class DeleteBookView(View):
    def get(self, request, book_id):
        book = get_object_or_404(Book, pk=book_id)
        return render(request, 'delete_book.html', {'book': book})

    def post(self, request, book_id):
        book = get_object_or_404(Book, pk=book_id)
        book.delete()
        messages.success(request, 'Book deleted successfully')
        return redirect('library_action')

class AddStationeryView(View):
    def get(self, request):
        form = StationeryForm()
        return render(request, 'add_stationery.html', {'form': form})

    def post(self, request):
        form = StationeryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'New stationery added successfully')
            return redirect('add_stationery')
        return render(request, 'add_stationery.html', {'form': form})

class StationeryListView(View, PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = 'library.view_stationery'

    def get(self, request):
        stationeries = Stationery.objects.all().order_by('-date_buyed')  # Order by date_buyed descending
        total_quantity = stationeries.aggregate(total_quantity=Sum('quantity'))['total_quantity']

        # Group stationeries by month and year, handling None date_buyed
        grouped_stationeries = {}
        for key, group in groupby(stationeries, key=lambda x: x.date_buyed.strftime('%Y-%m') if x.date_buyed else 'No Date'):
            if key != 'No Date':
                year_month = datetime.strptime(key, '%Y-%m')
            else:
                year_month = key
            grouped_stationeries[year_month] = list(group)

        # Sort grouped stationeries by month in descending order
        sorted_grouped_stationeries = dict(sorted(grouped_stationeries.items(), key=lambda x: (x[0] != 'No Date', x[0]), reverse=True))

        return render(request, 'stationery_list.html', {
            'grouped_stationeries': sorted_grouped_stationeries,
            'total_quantity': total_quantity
        })

class StationeryDetailView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        return render(request, 'stationery_details.html', {'stationery': stationery})

class StationeryUpdateView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        form = StationeryForm(instance=stationery)
        return render(request, 'stationery_update.html', {'form': form, 'stationery': stationery})

    def post(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        form = StationeryForm(request.POST, instance=stationery)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stationery updated successfully')
            return redirect('stationery_detail', stationery_id=stationery.id)
        return render(request, 'stationery_update.html', {'form': form, 'stationery': stationery})


class StationeryDeleteView(View):
    def get(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        return render(request, 'stationery_delete.html', {'stationery': stationery})

    def post(self, request, stationery_id):
        stationery = get_object_or_404(Stationery, pk=stationery_id)
        stationery.delete()
        return redirect('stationery_list')
