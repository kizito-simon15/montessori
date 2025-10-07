"""
bursor/views.py – finance-only endpoints (no bespoke forms)
===========================================================
• Dashboard (KPIs from finance + expenditures)
• Invoice / Receipt CRUD (using apps.finance.forms)
• “My Salary” list
• Expenditure CRUD (using expenditures.forms)
"""
# ─── stdlib / django ───────────────────────────────────────────
import calendar
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncMonth, ExtractMonth
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

# ─── finance & expenditure apps ───────────────────────────────
from apps.finance.models import Invoice, Receipt, SalaryInvoice
from apps.finance.forms  import InvoiceForm, ReceiptForm, InvoiceReceiptFormSet
from expenditures.models import Expenditure
from expenditures.forms  import ExpenditureForm


# ══════════════════════════════════════════════════════════════
# 1. DASHBOARD
# ══════════════════════════════════════════════════════════════
@login_required
def dashboard(request):
    today = timezone.localdate()
    inv   = Invoice.objects.filter(created_at__year=today.year)
    rcpt  = Receipt.objects.filter(date_paid__year=today.year)
    exp   = Expenditure.objects.filter(date__year=today.year)

    total_inv = inv.aggregate(t=Sum("invoice_amount"))["t"] or Decimal(0)
    total_rcp = rcpt.aggregate(t=Sum("amount_paid"))["t"]   or Decimal(0)
    total_exp = exp.aggregate(t=Sum("amount"))["t"]         or Decimal(0)

    labels = [calendar.month_abbr[m] for m in range(1, 13)]
    inv_series = [inv.filter(created_at__month=m).aggregate(t=Sum("invoice_amount"))["t"] or 0 for m in range(1, 13)]
    rcp_series = [rcpt.filter(date_paid__month=m).aggregate(t=Sum("amount_paid"))["t"]     or 0 for m in range(1, 13)]

    return render(request, "bursor/dashboard.html", {
        "kpis": [
            {"label": "Invoiced",    "value": total_inv},
            {"label": "Collected",   "value": total_rcp},
            {"label": "Outstanding", "value": total_inv - total_rcp},
            {"label": "Spent",       "value": total_exp},
        ],
        "month_labels":   labels,
        "invoice_series": inv_series,
        "receipt_series": rcp_series,
    })


# ══════════════════════════════════════════════════════════════
# 2. INVOICES  (uses apps.finance.forms.InvoiceForm)
# ══════════════════════════════════════════════════════════════
class InvoiceListView(LoginRequiredMixin, ListView):
    model               = Invoice
    template_name       = "bursor/invoice_list.html"
    context_object_name = "invoices"
    paginate_by         = 50

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        qs = super().get_queryset().select_related(
            "student", "session", "installment"
        )
        if q:
            qs = qs.filter(
                student__surname__icontains=q
            ) | qs.filter(student__firstname__icontains=q)
        return qs.order_by("-created_at")


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model         = Invoice
    form_class    = InvoiceForm
    template_name = "bursor/invoice_form.html"
    success_url   = reverse_lazy("bursor-invoice-list")


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model         = Invoice
    form_class    = InvoiceForm
    template_name = "bursor/invoice_form.html"
    success_url   = reverse_lazy("bursor-invoice-list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # allow inline receipt edits but NO custom item formset
        ctx["receipt_fs"] = InvoiceReceiptFormSet(
            self.request.POST or None,
            instance=self.object,
            prefix="receipts",
        )
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data(form=form)
        if ctx["receipt_fs"].is_valid():
            resp = super().form_valid(form)
            ctx["receipt_fs"].save()
            messages.success(self.request, "Invoice & receipts updated.")
            return resp
        return self.form_invalid(form)


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model         = Invoice
    template_name = "bursor/invoice_detail.html"


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model         = Invoice
    template_name = "bursor/invoice_confirm_delete.html"
    success_url   = reverse_lazy("bursor-invoice-list")


# ─── Receipts (finance.forms.ReceiptForm) ─────────────────────
class ReceiptCreateView(LoginRequiredMixin, CreateView):
    model         = Receipt
    form_class    = ReceiptForm
    template_name = "bursor/receipt_form.html"

    def dispatch(self, request, *a, **kw):
        self.invoice = get_object_or_404(Invoice, pk=request.GET.get("invoice"))
        return super().dispatch(request, *a, **kw)

    def form_valid(self, form):
        form.instance.invoice = self.invoice
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("bursor-receipt-detail", args=[self.object.pk])


class ReceiptDetailView(LoginRequiredMixin, DetailView):
    model         = Receipt
    template_name = "bursor/receipt_detail.html"


# ══════════════════════════════════════════════════════════════
# 3. “MY” SALARY SLIPS
# ══════════════════════════════════════════════════════════════
@login_required
def my_salary(request):
    me = request.user.bursoruser  # one-to-one
    slips = (SalaryInvoice.objects
             .filter(staff=me.staff)
             .order_by("-month"))

    buckets = (slips.annotate(m=TruncMonth("month"))
                     .values("m")
                     .annotate(net=Sum("net_salary"))
                     .order_by("-m"))
    return render(request, "bursor/my_salary.html",
                  {"slips": slips, "buckets": buckets})


# ══════════════════════════════════════════════════════════════
# 4. EXPENDITURES  (expenditures.forms.ExpenditureForm)
# ══════════════════════════════════════════════════════════════
class ExpenditureListView(LoginRequiredMixin, ListView):
    model               = Expenditure
    template_name       = "bursor/expenditure_list.html"
    context_object_name = "rows"
    paginate_by         = 50

    def get_queryset(self):
        qs = (super()
              .get_queryset()
              .select_related("budget", "budget_line")
              .order_by("-date"))
        start, end = self.request.GET.get("start"), self.request.GET.get("end")
        if start: qs = qs.filter(date__gte=start)
        if end:   qs = qs.filter(date__lte=end)
        return qs


class ExpenditureCreateView(LoginRequiredMixin, CreateView):
    model         = Expenditure
    form_class    = ExpenditureForm
    template_name = "bursor/expenditure_form.html"
    success_url   = reverse_lazy("bursor-expenditure-list")


class ExpenditureUpdateView(LoginRequiredMixin, UpdateView):
    model         = Expenditure
    form_class    = ExpenditureForm
    template_name = "bursor/expenditure_form.html"
    success_url   = reverse_lazy("bursor-expenditure-list")


class ExpenditureDetailView(LoginRequiredMixin, DetailView):
    model         = Expenditure
    template_name = "bursor/expenditure_detail.html"


class ExpenditureDeleteView(LoginRequiredMixin, DeleteView):
    model         = Expenditure
    template_name = "bursor/expenditure_confirm_delete.html"
    success_url   = reverse_lazy("bursor-expenditure-list")
