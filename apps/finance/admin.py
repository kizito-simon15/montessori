from django.contrib import admin
from .models import SalaryInvoice, Invoice, Receipt, InvoiceItem

admin.site.register(SalaryInvoice)
admin.site.register(Invoice)
admin.site.register(Receipt)
admin.site.register(InvoiceItem)


