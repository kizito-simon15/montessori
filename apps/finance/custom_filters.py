from django import template

register = template.Library()

@register.filter
def total_gross(invoices):
    return sum(invoice.gross_salary for invoice in invoices)

@register.filter
def total_deductions(invoices):
    return sum(invoice.deductions for invoice in invoices)

@register.filter
def total_net(invoices):
    return sum(invoice.net_salary for invoice in invoices)

