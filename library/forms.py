from django import forms
from apps.students.models import Student
from .models import Book, Stationery, IssuedBook, IssuedStaff

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['book_name', 'quantity', 'author', 'category', 'description', 'student_class', 'date_buyed']
        widgets = {
            'book_name': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%;'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 100%;'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%;'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 100%;'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'style': 'width: 100%;'}),
            'student_class': forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%;'}),
            'date_buyed': forms.DateInput(attrs={'class': 'form-control', 'style': 'width: 100%;', 'type': 'date'}),
        }

class StationeryForm(forms.ModelForm):
    class Meta:
        model = Stationery
        fields = ['name', 'quantity', 'type', 'description', 'date_buyed', 'office_department']  # Include 'type' below 'quantity'
        labels = {
            'name': 'Name',
            'quantity': 'Quantity',
            'type': 'Type',  # Label for the new field
            'description': 'Description',
            'date_buyed': 'Date Bought',  # Updated label for 'date_buyed'
            'office_department': 'Department',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),  # Widget for the new field
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'date_buyed': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'office_department': forms.TextInput(attrs={'class': 'form-control'}),
        }


class IssueBookForm(forms.ModelForm):
    class Meta:
        model = IssuedBook
        fields = ['student', 'book', 'book_number', 'date_issued', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'date_issued': forms.DateInput(attrs={'type': 'date'})
        }


class IssueStaffForm(forms.ModelForm):
    class Meta:
        model = IssuedStaff
        fields = ['staff', 'book', 'book_number', 'date_issued', 'expiry_date']  # Include issue_number field
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'date_issued': forms.DateInput(attrs={'type': 'date'})  # Add this line
        }