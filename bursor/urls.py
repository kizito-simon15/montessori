from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/",                    views.dashboard,                   name="bursor_dashboard"),

    # invoices & receipts
    path("invoices/",                    views.InvoiceListView.as_view(),   name="bursor-invoice-list"),
    path("invoices/create/",             views.InvoiceCreateView.as_view(), name="bursor-invoice-create"),
    path("invoices/<int:pk>/",           views.InvoiceDetailView.as_view(), name="bursor-invoice-detail"),
    path("invoices/<int:pk>/edit/",      views.InvoiceUpdateView.as_view(), name="bursor-invoice-update"),
    path("invoices/<int:pk>/delete/",    views.InvoiceDeleteView.as_view(), name="bursor-invoice-delete"),

    path("receipts/add/",                views.ReceiptCreateView.as_view(), name="bursor-receipt-create"),
    path("receipts/<int:pk>/",           views.ReceiptDetailView.as_view(), name="bursor-receipt-detail"),

    # salary
    path("my-salary/",                   views.my_salary,                   name="bursor-my-salary"),

    # expenditures
    path("expenditures/",                views.ExpenditureListView.as_view(),   name="bursor-expenditure-list"),
    path("expenditures/create/",         views.ExpenditureCreateView.as_view(), name="bursor-expenditure-create"),
    path("expenditures/<int:pk>/",       views.ExpenditureDetailView.as_view(), name="bursor-expenditure-detail"),
    path("expenditures/<int:pk>/edit/",  views.ExpenditureUpdateView.as_view(), name="bursor-expenditure-update"),
    path("expenditures/<int:pk>/delete/",views.ExpenditureDeleteView.as_view(), name="bursor-expenditure-delete"),
]
