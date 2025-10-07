from __future__ import annotations

import csv, io, logging
from django.conf import settings   
from django.http import JsonResponse
from collections import defaultdict
from typing import Iterator, List
from decimal import Decimal
from collections import OrderedDict
from django.db.models import Sum, Value, DecimalField, Q, F, Prefetch, ExpressionWrapper, functions as db_fn
from django.db.models.functions import Coalesce
from django.db import transaction
from datetime        import datetime, timedelta
from decimal         import Decimal, ROUND_HALF_UP
from typing          import Any, Dict, Iterable
from django.views.generic import TemplateView 
from django.contrib  import messages
from django.contrib.auth.decorators      import login_required
from django.contrib.auth.mixins          import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions              import ValidationError
from django.core.paginator               import Paginator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.functions import Lower
from django.http                         import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts                    import get_object_or_404, redirect, render
from django.template.loader              import get_template
from django.urls                         import reverse_lazy
from django.utils                        import timezone
from django.views.decorators.http        import require_GET
from django.views.generic                import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, View,
)

from django.contrib.messages.views import SuccessMessageMixin

from xhtml2pdf import pisa          # swap for WeasyPrint if preferred
from .ledger  import YearLedger   
# ─── local imports ──────────────────────────────────────────────────────────
from .forms     import (
    BudgetForm, SchoolFeesForm,
    SalaryInvoiceForm, DeductionFormSet,
    InvoiceForm, InvoiceReceiptFormSet,
    ReceiptForm,
    UniformForm, UniformFormSet, StudentUniformForm, UniformTypeForm,
)
from .ledger    import YearLedger
from .models    import (
    Budget, BudgetCategory,
    SchoolFees,
    SalaryInvoice, Deduction,
    Invoice, Receipt,
    Uniform, UniformType, StudentUniform,
)
from .utils     import _render_pdf

# ─── cross-app models ───────────────────────────────────────────────────────
from apps.corecode.models import AcademicSession, AcademicTerm, Installment, StudentClass
from apps.staffs.models   import Staff
from apps.students.models import Student, StudentTermAssignment
from expenditures.models  import Expenditure          # KPI tiles

logger = logging.getLogger(__name__)
DEC2 = Decimal("0.01")

DECIMAL  = DecimalField(max_digits=16, decimal_places=2)
DEC_ZERO = Value(Decimal("0"), output_field=DECIMAL)




def _r2(value) -> Decimal:
    """
    Bankers-round any numeric/None to 2-dp Decimal.
    Safe for int, float, Decimal or None.
    """
    return Decimal(value or 0).quantize(DEC2, ROUND_HALF_UP)

# ════════════════════════════════════════════════════════════════════════════
#  0.  Helper utilities
# ════════════════════════════════════════════════════════════════════════════
def _current_cycle() -> tuple[AcademicSession|None, AcademicTerm|None, Installment|None]:
    """Returns objects flagged `current=True` (or None if not set)."""
    return (
        AcademicSession.objects.filter(current=True).first(),
        AcademicTerm.objects.filter(current=True).first(),
        Installment.objects.filter(current=True).first(),
    )

def _paginate(qs: Iterable, request: HttpRequest, per_page: int = 20):
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get("page"))

class SelectLinkView(LoginRequiredMixin,
                     PermissionRequiredMixin,
                     TemplateView):
    """
    Minimal home screen: shows high-level counts and links the user onward
    to Invoices, Salaries and Expenditures.  Route name: **select_link**.
    """
    template_name       = "finance/select_link.html"
    permission_required = "finance.view_invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            total_invoices    = Invoice.objects.count(),
            salary_invoices   = SalaryInvoice.objects.count(),
            expenditures      = Expenditure.objects.aggregate(
                                   total=Sum("amount"))["total"] or 0,
        )
        return ctx

from decimal import Decimal

# apps/finance/views.py  – replace the whole class ↓
class BudgetDashboardView(LoginRequiredMixin,
                           PermissionRequiredMixin,
                           TemplateView):
    """
    Finance › Budget dashboard

    • KPI tiles (allocated / used / remaining)
    • Stacked-bar per-budget (allocated vs used vs remaining)
    • Cumulative utilisation line
    • Pie – allocation split by category
    """
    template_name       = "finance/budget/budget_dashboard.html"
    permission_required = "finance.view_budget"

    # ── helper: compute spend for one Budget ---------------------
    @staticmethod
    def _budget_used(b: Budget) -> Decimal:
        from apps.finance.models import SalaryInvoice
        from expenditures.models import (
            Expenditure, SeasonalPurchase, KitchenPurchase, ProcessingBatch,
        )

        EXP_COST = ExpressionWrapper(
            F("price_per_unit") * Coalesce(F("quantity"), Value(1)),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        )
        PUR_COST = ExpressionWrapper(
            F("quantity") * F("price_per_unit"),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        )

        salary   = SalaryInvoice.objects.filter(budget=b)           \
                                        .aggregate(t=Coalesce(Sum("net_salary"), DEC_ZERO))["t"]
        ops      = Expenditure.objects.filter(budget=b)             \
                                        .aggregate(t=Coalesce(Sum(EXP_COST), DEC_ZERO))["t"]
        seasonal = SeasonalPurchase.objects.filter(budget=b)        \
                                        .aggregate(t=Coalesce(Sum(PUR_COST), DEC_ZERO))["t"]
        kitchen  = KitchenPurchase.objects.filter(budget=b)         \
                                        .aggregate(t=Coalesce(Sum(PUR_COST), DEC_ZERO))["t"]
        fees     = ProcessingBatch.objects.filter(source_purchase__budget=b) \
                                        .aggregate(t=Coalesce(Sum("processing_fee"), DEC_ZERO))["t"]
        return _r2(salary + ops + seasonal + kitchen + fees)

    # ── view context --------------------------------------------
    def get_context_data(self, **kw):
        ctx  = super().get_context_data(**kw)
        g    = self.request.GET
        sess = g.get("session")
        cat  = g.get("category")

        qs = Budget.objects.select_related("session").order_by("-created_at")
        if sess: qs = qs.filter(session_id=sess)
        if cat:  qs = qs.filter(category=cat)

        labels, alloc_dec, used_dec, rem_dec = [], [], [], []
        by_cat_alloc: dict[str, Decimal] = defaultdict(Decimal)

        for b in qs:
            alloc  = _r2(b.allocated_amount)
            used   = self._budget_used(b)
            remain = _r2(alloc - used)

            labels.append(b.name)
            alloc_dec.append(alloc)
            used_dec .append(used)
            rem_dec  .append(remain)

            by_cat_alloc[b.category] += alloc

        total_alloc = sum(alloc_dec, Decimal(0))
        total_used  = sum(used_dec,  Decimal(0))

        # ── KPI tiles & tabular list ------------------------------------
        ctx["budgets"] = [dict(
            obj    = b,
            alloc  = _r2(b.allocated_amount),
            used   = self._budget_used(b),
            remain = _r2(b.allocated_amount - self._budget_used(b)),
        ) for b in qs]

        ctx.update(
            total_alloc  = _r2(total_alloc),
            total_used   = _r2(total_used),
            total_remain = _r2(total_alloc - total_used),
        )

        # ── charts ------------------------------------------------------
        ctx.update(
            labels       = labels,
            alloc_series = [float(a) for a in alloc_dec],
            used_series  = [float(u) for u in used_dec],
            rem_series   = [float(r) for r in rem_dec],

            line_labels  = labels[::-1],
            line_series  = [
                float(sum(used_dec[:i+1]) / total_alloc * 100) if total_alloc else 0
                for i in reversed(range(len(used_dec)))
            ],

            pie_labels   = [BudgetCategory(c).label for c in by_cat_alloc],
            pie_series   = [float(v) for v in by_cat_alloc.values()],

            filters      = dict(session=sess or "", category=cat or ""),
            now          = timezone.now(),
        )

        # ---------- Top-5 budget-lines (fixed) --------------------------
        EXP_COST = ExpressionWrapper(
            F("price_per_unit") * Coalesce(F("quantity"), Value(1)),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        )
        ctx["budget_totals"] = (
            Expenditure.objects
            .values("budget_line__name")
            .annotate(total=Coalesce(Sum(EXP_COST), DEC_ZERO))
            .order_by("-total")[:5]
        )

        return ctx


class BudgetListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model               = Budget
    permission_required = "finance.view_budget"
    template_name       = "finance/budget/budget_list.html"
    ordering            = ["-created_at"]
    paginate_by         = 30

    def get_queryset(self):
        qs = super().get_queryset().select_related("session","term","installment")
        g  = self.request.GET
        if s := g.get("session"):     qs = qs.filter(session_id=s)
        if t := g.get("term"):        qs = qs.filter(term_id=t)
        if i := g.get("installment"): qs = qs.filter(installment_id=i)
        if c := g.get("category"):    qs = qs.filter(category=c)
        return qs

class _BudgetBase(LoginRequiredMixin, PermissionRequiredMixin):
    model         = Budget
    form_class    = BudgetForm
    template_name = "finance/budget/budget_form.html"
    success_url   = reverse_lazy("budget-list")

    def form_valid(self, form):
        try:
            resp = super().form_valid(form)
            messages.success(self.request, "Budget saved.")
            return resp
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)

class BudgetCreateView(_BudgetBase, CreateView): permission_required = "finance.add_budget"
class BudgetUpdateView(_BudgetBase, UpdateView): permission_required = "finance.change_budget"
class BudgetDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Budget; permission_required="finance.delete_budget"
    template_name="finance/budget/budget_confirm_delete.html"; success_url=reverse_lazy("budget-list")

# ════════════════════════════════════════════════════════════════════════════
#  2.  School-Fees  •  CRUD
# ════════════════════════════════════════════════════════════════════════════
class SchoolFeesListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = SchoolFees
    permission_required = "finance.view_schoolfees"
    template_name = "finance/school_fees_list.html"
    ordering = ["session__name", "category"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("session").order_by("session__name", Lower("category"))
        if s := self.request.GET.get("session"):
            qs = qs.filter(session_id=s)
        return qs

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["sessions"] = AcademicSession.objects.all()
        return ctx

class _SchoolFeesBase(LoginRequiredMixin, PermissionRequiredMixin):
    model = SchoolFees
    form_class = SchoolFeesForm
    template_name = "finance/school_fees_form.html"
    success_url = reverse_lazy("school-fees-list")

    def form_valid(self, form):
        try:
            logger.debug(f"Saving school fees: session={form.cleaned_data['session']}, category={form.cleaned_data['category']}, amount={form.cleaned_data['annual_amount']}")
            resp = super().form_valid(form)
            messages.success(self.request, "School fees saved.")
            return resp
        except Exception as exc:
            logger.error(f"Error saving school fees: {exc}")
            form.add_error(None, str(exc))
            return self.form_invalid(form)

class SchoolFeesCreateView(_SchoolFeesBase, CreateView):
    permission_required = "finance.add_schoolfees"

class SchoolFeesUpdateView(_SchoolFeesBase, UpdateView):
    permission_required = "finance.change_schoolfees"

class SchoolFeesDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SchoolFees
    permission_required = "finance.delete_schoolfees"
    template_name = "finance/school_fees_confirm_delete.html"
    success_url = reverse_lazy("school-fees-list")

    def delete(self, req, *a, **kw):
        self.object = self.get_object()
        if self.object.invoices.exists():
            messages.error(req, "Cannot delete – invoices exist.")
            return redirect("school-fees-list")
        logger.debug(f"Deleting school fees: session={self.object.session}, category={self.object.category}")
        messages.success(req, "School-fees entry removed.")
        return super().delete(req, *a, **kw)


# apps/finance/views.py  – replace the current DetailView
class SalaryInvoiceDetailView(LoginRequiredMixin,
                               PermissionRequiredMixin,
                               DetailView):
    """
    Polished A5‑style payslip.

    Context extras:
        • deductions_list  – queryset, already ordered
        • statutory_lines  – [(label, amount), …]
        • earning_lines    – [(label, amount), …]
        • allow_print      – GET ?print=1 hides nav / buttons (CSS @media print)
    """
    model               = SalaryInvoice
    permission_required = "finance.view_salaryinvoice"
    template_name       = "finance/salary_detail.html"

    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        slip  = self.object

        ctx.update(
            deductions_list = slip.deductions.all(),    # keeps ordering
            earning_lines = [
                ("Basic salary",       slip.basic_salary),
                ("Special allowance",  slip.special_allowance),
                ("Other allowance",    slip.allowance),
            ],
            statutory_lines = [
                ("NSSF (10%)",  slip.nssf_amount),
                ("WCF (0%)",    slip.wcf_amount),
                ("PAYE",        slip.paye_amount),
                ("HELSB",       slip.helsb_amount),
            ],
            allow_print = self.request.GET.get("print") == "1",
            logo_url    = "/static/img/logo.jpg",        # adjust if you have a brand asset
        )
        return ctx

# apps/finance/views.py
class SalaryInvoiceListView(LoginRequiredMixin,
                             PermissionRequiredMixin,
                             ListView):
    """
    Salary ledger (KPI tiles • month buckets • gross / net stacked bar).
    No longer touches the Expenditure table at all.
    """
    model               = SalaryInvoice
    permission_required = "finance.view_salaryinvoice"
    template_name       = "finance/salary_list.html"
    paginate_by         = 50
    ordering            = ["-issued_date", "staff__surname"]

    # ---------- helpers ----------------------------------------------------
    @staticmethod
    def _parse_month(s: str | None):
        try:
            return datetime.strptime(s, "%Y-%m") if s else None
        except ValueError:
            return None

    # ---------- base queryset + filters -----------------------------------
    def get_queryset(self):
        qs = (super()
              .get_queryset()
              .select_related("staff", "budget")
              .prefetch_related("deductions")
              .annotate(
                  extra_ded_total=Coalesce(
                      Sum("deductions__amount"),
                      Value(0, output_field=DecimalField()),
                  ),
              ))

        g       = self.request.GET
        term    = g.get("q", "").strip()
        m_from  = self._parse_month(g.get("from"))
        m_to    = self._parse_month(g.get("to"))

        if term:
            qs = qs.filter(
                Q(staff__firstname__icontains=term) |
                Q(staff__surname__icontains=term)   |
                Q(staff__staff_id__icontains=term)
            )

        if m_from and m_to and m_to < m_from:
            m_from, m_to = m_to, m_from

        if m_from and m_to:
            last = (m_to + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            qs   = qs.filter(issued_date__range=[m_from.date(), last.date()])
        elif m_from:
            qs   = qs.filter(issued_date__year=m_from.year,
                             issued_date__month=m_from.month)
        return qs

    # ---------- context ----------------------------------------------------
    def get_context_data(self, **kw):
        ctx  = super().get_context_data(**kw)
        g    = self.request.GET
        qs   = self.get_queryset()                 # un-paginated

        # KPI tiles – just salary + allocation
        alloc  = Budget.objects.aggregate(t=Coalesce(Sum("allocated_amount"), DEC_ZERO))["t"]
        used   = qs.aggregate(t=Coalesce(Sum("net_salary"), DEC_ZERO))["t"]
        remain = alloc - used

        ctx.update(
            budget_total_allocated = _r2(alloc),
            budget_total_used      = _r2(used),
            budget_total_remaining = _r2(remain),
            budget_profit_loss     = _r2(remain),           # keep tile, drop chart
            budget_profit_loss_pct = _r2((remain/alloc*100) if alloc else 0),

            q      = g.get("q", ""),
            from_m = g.get("from", ""),
            to_m   = g.get("to",   ""),
        )

        # month buckets
        buckets = defaultdict(lambda: {
            "invoices": [], "gross_tot": Decimal(0), "net_tot": Decimal(0)
        })
        for inv in qs.order_by("-month"):
            key = inv.month.strftime("%Y-%m")
            b   = buckets[key]
            b["invoices"].append(inv)
            b["gross_tot"] += inv.gross_salary
            b["net_tot"]   += inv.net_salary
            b["month"]      = inv.month

        ctx["buckets"] = [
            {
                "month":     b["month"],
                "invoices":  b["invoices"],
                "gross_tot": _r2(b["gross_tot"]),
                "net_tot":   _r2(b["net_tot"]),
            }
            for b in sorted(buckets.values(), key=lambda x: x["month"], reverse=True)
        ]

        # stacked bar
        bar_labels = []
        bar_gross  = []
        bar_net    = []
        for b in ctx["buckets"][::-1]:
            bar_labels.append(b["month"].strftime("%b"))
            bar_gross.append(float(b["gross_tot"]))
            bar_net  .append(float(b["net_tot"]))
        ctx.update(bar_labels=bar_labels, bar_gross=bar_gross, bar_net=bar_net)

        # we **skip** ledger_profit_series (no expense component now)
        ctx.update(ledger_labels=[], ledger_profit_series=[])
        return ctx

# ──────────────────────────────────────────────────────────────
#  Payslip create / update helpers
# ──────────────────────────────────────────────────────────────
class _SalaryInvoiceMixin(LoginRequiredMixin, PermissionRequiredMixin):
    model         = SalaryInvoice
    form_class    = SalaryInvoiceForm
    template_name = "finance/salary_form.html"
    success_url   = reverse_lazy("salary-invoice-list")
    permission_required = "finance.change_salaryinvoice"   # override for create

    # ── shared context builder ──────────────────────────────────
    def _get_context(self, **extra):
        """
        Always supply a *bound* formset so the template can render existing
        deductions or blank rows on the very first GET.
        """
        if not hasattr(self, "object"):
            self.object = None
        fs = DeductionFormSet(
            self.request.POST or None,
            instance=self.object,
            prefix="deduction",                # ← same prefix as the template
        )
        ctx = dict(
            form              = extra.get("form", self.get_form()),
            deduction_formset = extra.get("deduction_formset", fs),
        )
        return self.get_context_data(**ctx)

    # ── POST handler reused by create / update ───────────────────
    def _handle_post(self):
        form = self.get_form()
        formset = DeductionFormSet(
            self.request.POST, instance=self.object,
            prefix="deduction",
        )
        if not (form.is_valid() and formset.is_valid()):
            return self.render_to_response(
                self._get_context(form=form, deduction_formset=formset)
            )

        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object         # make sure FK is set
            formset.save()                         # ⇦ every row now persists
            self.object.recalc_from_deductions()

        messages.success(self.request, "Salary invoice saved.")
        return redirect(self.success_url)


# ── concrete CBVs ──────────────────────────────────────────────
class SalaryInvoiceCreateView(_SalaryInvoiceMixin, CreateView):
    permission_required = "finance.add_salaryinvoice"

    def get(self, *a, **kw):
        return self.render_to_response(self._get_context())

    def post(self, request, *a, **kw):
        self.object = None
        return self._handle_post()


class SalaryInvoiceUpdateView(_SalaryInvoiceMixin, UpdateView):
    def get(self, request, *a, **kw):
        self.object = self.get_object()
        return self.render_to_response(self._get_context())

    def post(self, request, *a, **kw):
        self.object = self.get_object()
        return self._handle_post()


class SalaryInvoiceDeleteView(LoginRequiredMixin,
                               PermissionRequiredMixin,
                               DeleteView):
    model               = SalaryInvoice
    permission_required = "finance.delete_salaryinvoice"
    template_name       = "finance/salary_confirm_delete.html"
    success_url         = reverse_lazy("salary-invoice-list")

@login_required
def staff_defaults(request, pk):
    """
    Return the staff member’s salary, special allowance and HELSB settings
    so the form can auto-populate deductions.
    """
    s = get_object_or_404(Staff, pk=pk)
    return JsonResponse({
        "basic_salary":       str(s.salary or 0),
        "special_allowance":  str(s.special_allowance or 0),
        "has_helsb":          s.has_helsb,
        "helsb_rate":         float(s.helsb_rate_as_decimal),  # fraction (0-1)
    })

@login_required
def salary_pdf(request):
    qs=SalaryInvoice.objects.all()
    if m:=request.GET.get("month"):
        try:
            dt=datetime.strptime(m,"%Y-%m"); qs=qs.filter(month__year=dt.year, month__month=dt.month)
        except ValueError: pass
    pdf=_render_pdf("finance/salary_pdf_template.html",{"invoices":qs})
    return HttpResponse(pdf or "PDF generation failed.", content_type="application/pdf", status=200 if pdf else 500)

# ════════════════════════════════════════════════════════════════════════════
#  4.  Fees Invoices
# ════════════════════════════════════════════════════════════════════════════
# ─── helpers ──────────────────────────────────────────────────────────────
class _InvoiceFilters:
    def _base_qs(self):
        return (
            Invoice.objects.select_related(
                "student", "session", "class_for",
                "installment", "school_fees",
            )
            .prefetch_related("receipts")
        )

    def _filter(self, qs):
        g = self.request.GET
        term = g.get("q", "").strip()

        if term:
            qs = qs.filter(
                Q(student__firstname__icontains=term)      |
                Q(student__surname__icontains=term)        |
                Q(student__registration_number__icontains=term) |
                Q(invoice_number__icontains=term)
            )

        if cls := g.get("class_filter"):
            qs = qs.filter(class_for_id=cls)

        if ses := g.get("session"):
            qs = qs.filter(session_id=ses)

        if cat := g.get("fee_category"):
            qs = qs.filter(school_fees__category__iexact=cat)

        return qs




# apps/finance/views.py
class InvoiceListView(LoginRequiredMixin, PermissionRequiredMixin,
                      View, _InvoiceFilters):
    """
    One-row-per-student summary table

    • Collapses all invoice lines belonging to a learner into a single row  
    • Shows:
        – first fee *category* we hit (you can tweak)  
        – latest *installment* we hit (for quick context)  
        – Total Expected  = Σ invoice_amount  
        – Total Paid      = Σ receipts  
        – Balance         = Expected – Paid  
    • Search / filter / pagination still work
    """
    permission_required = "finance.view_invoice"
    template_name       = "finance/invoice_list.html"
    paginate_by         = 20

    # ──────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────
    def _summary_rows(self, invoices):
        """
        Collapse a queryset of Invoice objects into one OrderedDict row
        per student, preserving display order by student surname.
        """
        rows: "OrderedDict[int, dict]" = OrderedDict()

        for inv in invoices:
            sid = inv.student_id
            row = rows.setdefault(
                sid,
                dict(
                    student        = inv.student,
                    student_class  = inv.class_for,
                    category       = inv.school_fees.category,
                    latest_inst    = inv.installment,
                    total_expected = 0,
                    total_paid     = 0,
                ),
            )

            # accumulate
            row["total_expected"] += inv.invoice_amount
            row["total_paid"]     += inv.amount_paid()

            # keep whichever installment *id* is higher (latest)
            if inv.installment_id > row["latest_inst"].id:
                row["latest_inst"] = inv.installment
            # keep freshest class snapshot
            row["student_class"] = inv.class_for or row["student_class"]

        # compute balances
        for row in rows.values():
            row["balance"] = row["total_expected"] - row["total_paid"]

        return list(rows.values())

    # ──────────────────────────────────────────────────────────────
    # CSV exporter (summary version)
    # ──────────────────────────────────────────────────────────────
    def _export_csv(self, rows):
        def stream_rows():
            yield ["Student", "Class", "Category", "Latest Installment",
                   "Total Expected", "Total Paid", "Balance"]
            for r in rows:
                yield [
                    str(r["student"]),
                    r["student_class"].name if r["student_class"] else "",
                    r["category"],
                    r["latest_inst"].name,
                    f"{r['total_expected']}",
                    f"{r['total_paid']}",
                    f"{r['balance']}",
                ]

        buff, writer = io.StringIO(), csv.writer(buff)

        def stream():
            for row in stream_rows():
                buff.seek(0), buff.truncate(0)
                writer.writerow(row)
                yield buff.getvalue()

        resp = StreamingHttpResponse(stream(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="student_invoice_summary.csv"'
        return resp

    # ──────────────────────────────────────────────────────────────
    # GET
    # ──────────────────────────────────────────────────────────────
    def get(self, request: HttpRequest, *_, **__):
        # step 1 – raw invoice queryset with filters
        inv_qs = (
            self._filter(self._base_qs())
            .order_by("student__surname", "student__firstname", "installment__id")
        )

        # step 2 – collapse to summary dicts
        rows = self._summary_rows(inv_qs)

        # optional CSV
        if request.GET.get("export") == "csv":
            return self._export_csv(rows)

        # step 3 – paginate rows
        paginator = Paginator(rows, self.paginate_by)
        try:
            page = paginator.page(request.GET.get("page") or 1)
        except (PageNotAnInteger, EmptyPage):
            page = paginator.page(1)

        g = request.GET
        ctx = dict(
            students        = page,                 # <-- template loops over this
            page_obj        = page,
            sessions        = AcademicSession.objects.all(),
            classes         = StudentClass.objects.all(),
            # echo filters
            q               = g.get("q", ""),
            class_filter    = g.get("class_filter"),
            session_sel     = g.get("session"),
            # KPI tiles (page-level)
            total_expected  = sum(r["total_expected"] for r in page.object_list),
            total_paid      = sum(r["total_paid"]     for r in page.object_list),
            total_balance   = sum(r["balance"]       for r in page.object_list),
        )
        return render(request, self.template_name, ctx)

    # ──────────────────────────────────────────────────────────────
    # POST – bulk delete (still operates on *invoice* ids unchanged)
    # ──────────────────────────────────────────────────────────────
    def post(self, request: HttpRequest, *_, **__):
        if request.POST.get("action") != "bulk_delete":
            return redirect("invoice-list")

        ids = request.POST.getlist("ids")           # still invoice-ids
        marked_qs  = Invoice.objects.filter(id__in=ids).annotate(
            r_sum=Sum("receipts__amount_paid")
        )
        protected  = marked_qs.filter(r_sum__gt=0)
        deletable  = marked_qs.filter(r_sum=0)
        deleted, _ = deletable.delete()

        if protected.exists():
            messages.warning(
                request,
                f"Skipped {protected.count()} invoice(s) with receipts. "
                f"Deleted {deleted}.",
            )
        else:
            messages.success(request, f"Deleted {deleted} invoice(s).")

        return HttpResponseRedirect(request.path)


# ─── shared base for create & update ─────────────────────────────────────
class _InvoiceBase(LoginRequiredMixin, PermissionRequiredMixin):
    model         = Invoice
    form_class    = InvoiceForm
    template_name = "finance/invoice_form.html"
    success_url   = reverse_lazy("invoice-list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def form_valid(self, form):
        obj = form.save(commit=False)
        if not form.cleaned_data.get("school_fees"):
            form.add_error("school_fees", "Select a school-fees entry.")
            return self.form_invalid(form)
        obj.school_fees = form.cleaned_data["school_fees"]
        try:
            obj.save()
            messages.success(self.request, "Invoice saved.")
            return HttpResponseRedirect(self.success_url)
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)


# ─── CRUD views ──────────────────────────────────────────────────────────
class InvoiceCreateView(_InvoiceBase, CreateView):
    permission_required = "finance.add_invoice"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        term = AcademicTerm.objects.filter(current=True).first()
        if term:
            ctx["academic_term_id"] = term.id
        return ctx


class InvoiceUpdateView(_InvoiceBase, UpdateView):
    permission_required = "finance.change_invoice"

# apps/finance/views.py  – drop this class in place of the old one
from django.db.models import Prefetch, Sum
from django.contrib import messages

class InvoiceDetailView(LoginRequiredMixin,
                         PermissionRequiredMixin,
                         DetailView):
    """
    Shows one fee-invoice with **all** its receipts, items and KPI tiles.
    """
    model               = Invoice
    permission_required = "finance.view_invoice"
    template_name       = "finance/invoice_detail.html"

    # pull everything in a single hit
    def get_queryset(self):
        return (super()
                .get_queryset()
                .select_related("student", "class_for",
                                "session",  "installment")
                .prefetch_related(
                    "items",
                    Prefetch("receipts",
                             queryset=Receipt.objects.order_by("-date_paid")),
                ))

    def get_context_data(self, **kwargs):
        ctx     = super().get_context_data(**kwargs)
        inv     = self.object
        receipts = list(inv.receipts.all())        # ← ordered by date DESC

        total_paid = sum(r.amount_paid for r in receipts)
        balance    = inv.invoice_amount - total_paid

        pct = 0
        if inv.invoice_amount:
            pct = round(total_paid / inv.invoice_amount * 100, 2)

        ctx.update(
            receipts     = receipts,
            items        = list(inv.items.all()),
            total_paid   = total_paid,
            balance      = balance,
            pct          = pct,
        )
        return ctx


class InvoiceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model               = Invoice
    permission_required = "finance.delete_invoice"
    template_name       = "finance/invoice_confirm_delete.html"
    success_url         = reverse_lazy("invoice-list")


# ───────── RECEIPTS ─────────────────────────────────────────────────────────
class _ReceiptBase(LoginRequiredMixin, PermissionRequiredMixin):
    model         = Receipt
    form_class    = ReceiptForm
    template_name = "finance/receipt.html"
    success_url   = reverse_lazy("invoice-list")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["invoice"] = getattr(self, "invoice", None)
        kw["request"] = self.request          # ← keep or remove – both now safe
        return kw

# apps/finance/views.py
class ReceiptCreateView(_ReceiptBase, CreateView):
    permission_required = "finance.add_receipt"

    # 1️⃣  grab the invoice once at entry-point
    def dispatch(self, request, *args, **kwargs):
        inv_id = request.GET.get("invoice")          # ?invoice=2
        self.invoice = get_object_or_404(Invoice, pk=inv_id) if inv_id else None
        return super().dispatch(request, *args, **kwargs)

    # 2️⃣  give the template real numbers
    def get_context_data(self, **ctx):
        ctx = super().get_context_data(**ctx)
        if self.invoice:
            ctx.update(
                total_expected = self.invoice.expected_amount(),
                total_paid     = self.invoice.amount_paid(),
                max_payable    = self.invoice.overall_balance(),
                invoice        = self.invoice,            # template may need it
            )
        return ctx

    # 3️⃣  link the new receipt back to that invoice
    def form_valid(self, form):
        if not self.invoice:
            form.add_error(None, "Invoice ID missing in URL (?invoice=<id>).")
            return self.form_invalid(form)

        form.instance.invoice     = self.invoice
        form.instance.received_by = getattr(self.request.user, "staff", None)
        return super().form_valid(form)


class StudentReceiptCreateView(_ReceiptBase, CreateView):
    """
    Take **one** amount and automatically distribute it over the student’s
    oldest unpaid invoices (FIFO) until the money runs out.
    """
    permission_required = "finance.add_receipt"

    def dispatch(self, request, *args, **kwargs):
        self.student   = get_object_or_404(Student, pk=kwargs["student_id"])
        self.invoices  = (
            Invoice.objects
            .filter(student=self.student)
            .order_by("session__id", "installment__id")
        )
        self.outstanding_total = sum(i.overall_balance() for i in self.invoices)
        return super().dispatch(request, *args, **kwargs)

    # ── template context ---------------------------------------------------
    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(
            student      = self.student,
            invoices     = self.invoices,
            max_payable  = self.outstanding_total,
        )
        return ctx

    # ── allocate the cash --------------------------------------------------
    @transaction.atomic
    def form_valid(self, form):
        amount = form.cleaned_data["amount_paid"]
        if amount > self.outstanding_total:
            form.add_error("amount_paid",
                           f"Student owes only {self.outstanding_total:,} TZS.")
            return self.form_invalid(form)

        # cascade oldest-first
        for inv in self.invoices:
            if amount <= 0:
                break
            amount = inv.allocate_payment(amount)  # helper we added earlier

        messages.success(self.request, "Payment recorded across invoices.")
        return redirect(self.success_url)


class ReceiptUpdateView(_ReceiptBase, UpdateView):
    permission_required = "finance.change_receipt"


class ReceiptDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model               = Receipt
    permission_required = "finance.delete_receipt"
    template_name       = "finance/receipt_confirm_delete.html"
    success_url         = reverse_lazy("invoice-list")

# ────────────────────────────────────────────────────────────────────────────
#  UNIFORMS & STUDENT-UNIFORM PAYMENTS  –  RESTORED HELPERS
# ────────────────────────────────────────────────────────────────────────────
from django.db.models import Sum

def _current_cycle():
    """Return (current_session, current_term, current_installment)."""
    return (
        AcademicSession.objects.filter(current=True).first(),
        AcademicTerm.objects.filter(current=True).first(),
        Installment.objects.filter(current=True).first(),
    )

# 1️⃣  UNIFORM LIST  – one row per student / class
@login_required
def uniform_list(request: HttpRequest) -> HttpResponse:
    session, _, _   = _current_cycle()
    session_id      = request.GET.get("session") or getattr(session, "id", None)
    class_id        = request.GET.get("class")

    sessions        = AcademicSession.objects.all()
    classes         = StudentClass.objects.all()

    uniforms_qs     = Uniform.objects.none()
    if session_id:
        uniforms_qs = Uniform.objects.filter(session_id=session_id)
        if class_id:
            uniforms_qs = uniforms_qs.filter(student_class_id=class_id)
        uniforms_qs = (
            uniforms_qs
            .select_related("student", "student_class", "uniform_type")
            .order_by("student__surname", "student_class__name")
        )

    # roll-up per student-&-class
    summary: dict[str, dict[str, Any]] = {}
    for u in uniforms_qs:
        key = f"{u.student_id}_{u.student_class_id}"
        row = summary.setdefault(
            key,
            dict(
                student=u.student,
                student_class=u.student_class.name,
                total_paid=Decimal(0),
                total_payable=Decimal(0),
                balance=Decimal(0),
                types_bought=[],
                student_uniform_id=None,
            ),
        )
        row["total_payable"] += u.price
        row["types_bought"].append(
            dict(type=u.uniform_type.name, qty=u.quantity, id=str(u.id))
        )

    # attach payments
    payments = (
        StudentUniform.objects
        .filter(session_id=session_id)
        .select_related("student", "student_class")
    )
    for p in payments:
        k = f"{p.student_id}_{p.student_class_id}"
        if k in summary:
            summary[k]["total_paid"]      += p.amount
            summary[k]["student_uniform_id"] = str(p.id)

    # calc balances
    for row in summary.values():
        row["balance"] = row["total_paid"] - row["total_payable"]

    return render(
        request,
        "finance/uniform_list.html",
        dict(
            uniform_data      = summary,
            sessions          = sessions,
            selected_session  = AcademicSession.objects.filter(id=session_id).first(),
            student_classes   = classes,
            selected_class_id = class_id,
        ),
    )

# 2️⃣  STUDENT-UNIFORM LIST (payment ledger)
@login_required
def student_uniform_list(request: HttpRequest) -> HttpResponse:
    qs = (
        StudentUniform.objects
        .select_related("student", "student_class", "session", "term")
        .order_by("student__surname", "student__firstname", "-id")
    )

    if sid := request.GET.get("session"):
        qs = qs.filter(session_id=sid)
    if tid := request.GET.get("term"):
        qs = qs.filter(term_id=tid)
    if cid := request.GET.get("class"):
        qs = qs.filter(student_class_id=cid)

    ctx = dict(
        payments         = qs,
        sessions         = AcademicSession.objects.all(),
        terms            = AcademicTerm.objects.all(),
        student_classes  = StudentClass.objects.all(),
        selected_session = request.GET.get("session", ""),
        selected_term    = request.GET.get("term",    ""),
        selected_class   = request.GET.get("class",   ""),
    )
    return render(request, "finance/student_uniform_list.html", ctx)

# 3️⃣  CRUD SHORTCUTS  (create / update / delete)  – unchanged semantics
@login_required
def uniform_create(request: HttpRequest) -> HttpResponse:
    formset = UniformFormSet(request.POST or None)
    if request.method == "POST" and formset.is_valid():
        session, term, _ = _current_cycle()
        for frm in formset:
            if frm.cleaned_data:
                u = frm.save(commit=False)
                u.session = session
                u.term    = term
                u.save()
        messages.success(request, "Uniform entries created.")
        return redirect("uniform_list")

    student_class_map = {
        str(s.id): str(s.current_class_id)
        for s in Student.objects.filter(
            current_status="active", completed=False, current_class__isnull=False
        )
    }
    prices = {str(ut.id): float(ut.price) for ut in UniformType.objects.all()}
    return render(
        request,
        "finance/uniform_form.html",
        dict(
            formset = formset,
            is_update = false,
            student_class_map = student_class_map,
            uniform_type_prices = prices,
        ),
    )

@login_required
def uniform_update(request: HttpRequest, pk: int) -> HttpResponse:
    uniform = get_object_or_404(Uniform, pk=pk)
    form    = UniformForm(request.POST or None, instance=uniform)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Uniform updated.")
        return redirect("uniform_list")
    prices = {str(ut.id): float(ut.price) for ut in UniformType.objects.all()}
    return render(request, "finance/uniform_update.html", {"form": form, "uniform_type_prices": prices})

@login_required
def uniform_delete(request: HttpRequest, pk: int) -> HttpResponse:
    uniform = get_object_or_404(Uniform, pk=pk)
    if request.method == "POST":
        uniform.delete()
        messages.success(request, "Uniform deleted.")
        return redirect("uniform_list")
    return render(request, "finance/uniform_confirm_delete.html", {"uniform": uniform})

# 4️⃣  Student-Uniform payments CRUD (reuse original templates)  -------------
@login_required
def student_uniform_create(request: HttpRequest, student_id: int) -> HttpResponse:
    student          = get_object_or_404(Student, pk=student_id)
    student_class_id = request.GET.get("class") or getattr(student.current_class, "id", None)
    student_class    = get_object_or_404(StudentClass, pk=student_class_id)

    session, term, _ = _current_cycle()
    payment          = StudentUniform.objects.filter(
        student=student, session=session, term=term, student_class=student_class
    ).first()

    form = StudentUniformForm(request.POST or None, instance=payment)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.student       = student
        obj.session       = session
        obj.term          = term
        obj.student_class = student_class
        obj.save()
        messages.success(request, "Payment recorded.")
        return redirect("uniform_list")

    return render(
        request,
        "finance/student_uniform_form.html",
        dict(form=form, student=student, student_class=student_class),
    )

@login_required
def student_uniform_update(request: HttpRequest, pk: int) -> HttpResponse:
    payment = get_object_or_404(StudentUniform, pk=pk)
    form    = StudentUniformForm(request.POST or None, instance=payment)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Payment updated.")
        return redirect("uniform_list")
    return render(
        request, "finance/student_uniform_form.html",
        dict(form=form, student=payment.student, student_class=payment.student_class)
    )

@login_required
def student_uniform_delete(request: HttpRequest, pk: int) -> HttpResponse:
    payment = get_object_or_404(StudentUniform, pk=pk)
    if request.method == "POST":
        payment.delete()
        messages.success(request, "Payment deleted.")
        return redirect("uniform_list")
    return render(request, "finance/student_uniform_confirm_delete.html",
                  {"student_uniform": payment})

# Uniform-type CRUD – class-based for brevity
class UniformTypeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model=UniformType; permission_required="finance.view_uniformtype"
    template_name="finance/uniformtype_list.html"; ordering=["name"]

class _UTBase(LoginRequiredMixin, PermissionRequiredMixin):
    model=UniformType; form_class=UniformTypeForm; template_name="finance/uniformtype_form.html"; success_url=reverse_lazy("uniformtype_list")
class UniformTypeCreateView(_UTBase, CreateView): permission_required="finance.add_uniformtype"
class UniformTypeUpdateView(_UTBase, UpdateView): permission_required="finance.change_uniformtype"
class UniformTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model=UniformType; permission_required="finance.delete_uniformtype"
    template_name="finance/uniformtype_confirm_delete.html"; success_url=reverse_lazy("uniformtype_list")

# ════════════════════════════════════════════════════════════════════════════
#  7.  Lightweight JSON endpoints (AJAX helpers)
# ════════════════════════════════════════════════════════════════════════════
@require_GET
@login_required
def student_search(request):
    term=request.GET.get("q","").strip()
    sess=request.GET.get("session_id"); trm=request.GET.get("term_id")
    qs=Student.objects.filter(Q(firstname__icontains=term)|Q(surname__icontains=term),
                              current_status="active", completed=False, current_class__isnull=False)
    if sess and trm:
        ids=StudentTermAssignment.objects.filter(academic_session_id=sess, academic_term_id=trm).values_list("student_id",flat=True)
        qs=qs.filter(id__in=ids)
    return JsonResponse({"results":[{"id":s.id,"text":f"{s.firstname} {s.surname}"} for s in qs[:10]]})

@require_GET
@login_required
def get_school_fees(request):
    sess=request.GET.get("session_id"); cat=request.GET.get("category")
    if not (sess and cat): return JsonResponse({"error":"Missing parameters"},status=400)
    try:
        sf=SchoolFees.objects.get(session_id=sess, category=cat)
        return JsonResponse({"id":sf.id,"annual":float(sf.annual_amount),"installment":float(sf.installment_amount())})
    except SchoolFees.DoesNotExist:
        return JsonResponse({"error":"Not found"},status=404)

@require_GET
@login_required
def get_student_class(request):
    sid, sess, trm = (request.GET.get(k) for k in ("student_id","session_id","term_id"))
    if not all([sid,sess,trm]): return JsonResponse({"error":"Missing parameters"},status=400)
    try: student=Student.objects.get(id=sid)
    except Student.DoesNotExist: return JsonResponse({"error":"Student not found"},status=404)
    if not StudentTermAssignment.objects.filter(student_id=sid, academic_session_id=sess, academic_term_id=trm).exists():
        return JsonResponse({"error":"Student not registered"},status=400)
    cls=student.current_class
    if not cls: return JsonResponse({"error":"Student has no class"},status=400)
    return JsonResponse({"class_id":cls.id,"class_name":cls.name})

@require_GET
@login_required
def get_student_balance(request):
    sid, sess, inst = (
        request.GET.get("student_id"),
        request.GET.get("session_id"),
        request.GET.get("installment_id"),
    )
    if not all([sid, sess, inst]):
        return JsonResponse({"error": "Missing parameters"}, status=400)

    prev_qs = (
        Invoice.objects
        .filter(student_id=sid)
        .filter(
            Q(session__id__lt=sess) |
            Q(session_id=sess, installment__id__lt=inst)
        )
    )
    bal = (
        prev_qs.aggregate(exp=Sum("invoice_amount"), paid=Sum("receipts__amount_paid"))
        or {"exp": 0, "paid": 0}
    )
    balance = (bal["exp"] or 0) - (bal["paid"] or 0)
    return JsonResponse({"balance": float(balance)})


@require_GET
@login_required
def get_remaining_balance(request):
    sid=request.GET.get("student_id"); sess=request.GET.get("session_id")
    amount=Decimal(request.GET.get("invoice_amount","0") or 0); inv_id=request.GET.get("invoice_id")
    if not (sid and sess): return JsonResponse({"error":"Missing parameters"},status=400)
    qs=Invoice.objects.filter(student_id=sid, session_id=sess)
    if inv_id: qs=qs.exclude(id=inv_id)
    total=qs.aggregate(t=Sum("invoice_amount"))["t"] or 0
    try: sf=SchoolFees.objects.filter(session_id=sess).first()
    except SchoolFees.DoesNotExist: return JsonResponse({"error":"No School-fees"},status=404)
    remain=sf.annual_amount-total-amount
    return JsonResponse({"remaining_balance":max(0,float(remain))})

@require_GET
@login_required
def get_uniform_price(request):
    utid=request.GET.get("type")
    if not utid: return JsonResponse({"error":"Missing type"},status=400)
    try:
        ut=UniformType.objects.get(id=utid)
        return JsonResponse({"price":float(ut.price)})
    except UniformType.DoesNotExist:
        return JsonResponse({"error":"Not found"},status=404)

@require_GET
@login_required
def student_info_api(request, student_id):
    student=get_object_or_404(Student, pk=student_id)
    cls=student.current_class
    if not cls: return JsonResponse({"error":"No class assigned"},status=400)
    return JsonResponse(dict(
        id=student.id, full_name=f"{student.firstname} {student.surname}",
        registration=student.registration_number or "N/A",
        current_class=cls.name, gender=student.gender, status=student.current_status,
    ))

# ────────────────────────────────────────────────────────────────────────────
#  Missing plain-function views  •  add to apps/finance/views.py
# ────────────────────────────────────────────────────────────────────────────
from django.db.models import Sum

# 1)  Uniform → single-student detail (read-only) ────────────────────────────
@login_required
def uniform_detail(request: HttpRequest, student_id: int) -> HttpResponse:
    """Show one student’s uniform purchases vs payments in the *current* session."""
    session, term, _ = _current_cycle()
    student          = get_object_or_404(Student, pk=student_id)

    uniforms = (
        Uniform.objects
        .filter(student=student, session=session)
        .select_related("uniform_type")
        .order_by("uniform_type__name")
    )

    total_used  = sum(u.price for u in uniforms)
    total_paid  = (
        StudentUniform.objects
        .filter(student=student, session=session)
        .aggregate(t=Sum("amount"))["t"] or Decimal(0)
    )
    balance     = total_paid - total_used

    return render(
        request,
        "finance/uniform_detail.html",
        dict(
            student      = student,
            uniforms     = uniforms,
            total_used   = _r2(total_used),
            total_paid   = _r2(total_paid),
            balance      = _r2(balance),
            session      = session,
            term         = term,
        ),
    )

# 2)  Salary PDFs – print inline or download  ────────────────────────────────
@login_required
def print_pdf(request: HttpRequest) -> HttpResponse:
    """
    Inline PDF of **salary invoices**.
    Optional `?month=YYYY-MM` query narrows the list.
    """
    qs = SalaryInvoice.objects.all()
    if month := request.GET.get("month"):
        try:
            dt  = datetime.strptime(month, "%Y-%m")
            qs  = qs.filter(month__year=dt.year, month__month=dt.month)
        except ValueError:
            pass

    pdf_bytes = _render_pdf("finance/salary_pdf_template.html", {"invoices": qs})
    if not pdf_bytes:
        return HttpResponse("PDF generation failed.", status=500)
    return HttpResponse(pdf_bytes, content_type="application/pdf")

@login_required
def save_pdf(request: HttpRequest) -> HttpResponse:
    """Download *all* salary invoices as `salary_invoices.pdf`."""
    pdf_bytes = _render_pdf("finance/salary_pdf_template.html",
                            {"invoices": SalaryInvoice.objects.all()})
    if not pdf_bytes:
        return HttpResponse("PDF generation failed.", status=500)

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = "attachment; filename=salary_invoices.pdf"
    return resp

# 3)  Invoice + Receipt printable / downloadable PDFs  ───────────────────────
@login_required
def invoice_view(request: HttpRequest, pk: int) -> HttpResponse:
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, "finance/invoice_print.html",
                  {"invoice": invoice, "now": timezone.now()})

@login_required
def generate_invoice(request: HttpRequest, pk: int) -> HttpResponse:
    """Download a *single* invoice as PDF."""
    invoice   = get_object_or_404(Invoice, pk=pk)
    pdf_bytes = _render_pdf("finance/invoice_pdf_template.html",
                            {"invoice": invoice, "now": timezone.now()})
    if not pdf_bytes:
        return HttpResponse("PDF generation failed.", status=500)

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename=invoice_{invoice.invoice_number}.pdf'
    )
    return resp

@login_required
def receipt_view(request: HttpRequest, receipt_id: int) -> HttpResponse:
    receipt = get_object_or_404(Receipt, pk=receipt_id)
    return render(request, "finance/receipt_print.html", {"receipt": receipt})

@login_required
def generate_receipt(request: HttpRequest, pk: int) -> HttpResponse:
    """Download a receipt PDF."""
    receipt   = get_object_or_404(Receipt, pk=pk)
    pdf_bytes = _render_pdf("finance/receipt_pdf_template.html", {"receipt": receipt})
    if not pdf_bytes:
        return HttpResponse("PDF generation failed.", status=500)

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename=receipt_{receipt.receipt_number}.pdf'
    )
    return resp