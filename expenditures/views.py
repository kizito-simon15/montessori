
from __future__ import annotations

import calendar
from datetime   import date, datetime, timedelta
from decimal    import Decimal
from typing     import Any, Dict, Final

# ─── Django ORM helpers ─────────────────────────────────────────────────────
from django.db.models import (
    Case, When,                                  # conditional expressions
    DecimalField, ExpressionWrapper, F, Q, Sum,  # maths / look-ups
    Value,                                       # literal wrapper
)
from django.db.models.functions import (
    Cast,        # ⇦ NEW – cast ints → Decimal to avoid “mixed types” errors
    Coalesce,
    ExtractMonth,
)
from django.db.models import IntegerField
from django.db.models.functions import Cast

# ─── Django core / CBV plumbing ─────────────────────────────────────────────
from django.contrib.auth.mixins  import LoginRequiredMixin
from django.http                 import JsonResponse
from django.urls                 import reverse_lazy
from django.utils                import timezone
from django.utils.decorators     import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic        import (
    CreateView, DeleteView, DetailView, ListView,
    TemplateView, UpdateView, View,
)

# ─── app-level imports ──────────────────────────────────────────────────────
from apps.finance.models import Budget, Receipt, SalaryInvoice
from .mixins  import LowStockMixin, SuccessMessageMixin
from .forms   import (
    BudgetLineForm, DailyConsumptionForm, ExpenditureForm,
    KitchenProductForm, KitchenPurchaseForm, KitchenUsageForm,
    ProcessedProductForm, ProcessingBatchForm,
    SeasonalProductForm, SeasonalPurchaseForm,
)
from .models  import (
    BudgetLine, DailyConsumption, Expenditure,
    KitchenProduct, KitchenPurchase, KitchenUsage,
    ProcessedProduct, ProcessingBatch,
    SeasonalProduct, SeasonalPurchase,
)

# ─── reusable DECIMAL helpers ───────────────────────────────────────────────
DECIMAL:  Final = DecimalField(max_digits=16, decimal_places=2)
DEC_ZERO: Final = Value(Decimal("0"), output_field=DECIMAL)

# short aliases used in several views
DEC:  Final = DecimalField(max_digits=16, decimal_places=2)
ZERO: Final = Value(Decimal("0"), output_field=DEC)


###############################################################################
# 0. Tiny JSON endpoints (AJAX helpers)
###############################################################################
@method_decorator(csrf_exempt, name="dispatch")
class RawStockJSON(LoginRequiredMixin, View):
    """GET ?product_id=PK → {"stock_raw": float}"""
    def get(self, request, *_a, **_kw):
        prod = SeasonalProduct.objects.filter(pk=request.GET.get("product_id")).first()
        return JsonResponse({"stock_raw": float(prod.stock_raw if prod else 0)})


@method_decorator(csrf_exempt, name="dispatch")
class ProcessedStockJSON(LoginRequiredMixin, View):
    """GET ?product_id=PK → {"stock_on_hand": float}"""
    def get(self, request, *_a, **_kw):
        prod = ProcessedProduct.objects.filter(pk=request.GET.get("product_id")).first()
        return JsonResponse({"stock_on_hand": float(prod.stock_on_hand if prod else 0)})





# -----------------------------------------------------------------------------
class ExpenditureDashboardView(LoginRequiredMixin, LowStockMixin, TemplateView):
    """
    Finance › Expenditure dashboard – now ‘amount’-free.
    """
    template_name = "expenditures/dashboard.html"

    # ───────────────────────────────────────────────────────── helpers ──
    @staticmethod
    def _money_expr() -> ExpressionWrapper:
        """
        Coalesce(quantity, 1) × price_per_unit → works for both
        single-item spends and line-items that already carry quantity.
        """
        return ExpressionWrapper(
            Coalesce(F("quantity"), Value(1)) * F("price_per_unit"),
            output_field=DECIMAL,
        )

    @staticmethod
    def _monthly(qs, expr) -> Dict[int, Decimal]:
        """Return { month → total } for the current calendar year."""
        yr = timezone.localdate().year
        rows = (
            qs.filter(date__year=yr)
              .annotate(m=ExtractMonth("date"))
              .values("m")
              .annotate(v=Coalesce(Sum(expr, output_field=DECIMAL), DEC_ZERO))
        )
        return {r["m"]: r["v"] for r in rows}

    # ─────────────────────────────────────────────────── main context ──
    def get_context_data(self, **kw):
        ctx      = super().get_context_data(**kw)
        money_op = self._money_expr()             # operating spends
        money_inv= ExpressionWrapper(             # inventory purchases
                        F("quantity") * F("price_per_unit"),
                        output_field=DECIMAL)

        # ── 1 ▸ compute per-budget ‘used’ without calling Budget.used ──
        budgets, total_alloc, total_used, red = [], Decimal(0), Decimal(0), []
        for b in Budget.objects.all():
            salary  = SalaryInvoice   .objects.filter(budget=b)\
                      .aggregate(t=Coalesce(Sum("net_salary"), DEC_ZERO))["t"]
            op      = Expenditure     .objects.filter(budget=b)\
                      .aggregate(t=Coalesce(Sum(money_op),     DEC_ZERO))["t"]
            season  = SeasonalPurchase.objects.filter(budget=b)\
                      .aggregate(t=Coalesce(Sum(money_inv),    DEC_ZERO))["t"]
            kitch   = KitchenPurchase .objects.filter(budget=b)\
                      .aggregate(t=Coalesce(Sum(money_inv),    DEC_ZERO))["t"]
            procfee = ProcessingBatch .objects.filter(
                         source_purchase__budget=b)\
                      .aggregate(t=Coalesce(Sum("processing_fee"), DEC_ZERO))["t"]

            used = salary + op + season + kitch + procfee
            remaining = b.allocated_amount - used

            total_alloc += b.allocated_amount
            total_used  += used
            if remaining < 0:
                red.append(b)

            budgets.append({"obj": b, "used": used, "remaining": remaining})

        ctx.update(
            total_allocated = total_alloc,
            spent_total     = total_used,
            remaining_all   = total_alloc - total_used,
            budgets_red     = [b["obj"] for b in budgets if b["remaining"] < 0],
        )

        # ── 2 ▸ Top-5 tables (operating / seasonal / kitchen) ───────────
        ctx["budget_totals"] = (
            Expenditure.objects
            .values("budget_line__name")
            .annotate(total=Sum(money_op))
            .order_by("-total")[:5]
        )
        ctx["top_seasonal"] = (
            SeasonalPurchase.objects
            .values("product__name")
            .annotate(total=Sum(money_inv))
            .order_by("-total")[:5]
        )
        ctx["top_kitchen"] = (
            KitchenPurchase.objects
            .values("product__name")
            .annotate(total=Sum(money_inv))
            .order_by("-total")[:5]
        )

        # ── 3 ▸ Monthly stacked-bar data ───────────────────────────
        labels = [calendar.month_abbr[i] for i in range(1, 13)]

        exp_m  = self._monthly(Expenditure.objects.all(),      money_op)
        pur_m  = self._monthly(SeasonalPurchase.objects.all(), money_inv)
        proc_m = self._monthly(ProcessingBatch.objects.all(),  F("processing_fee"))

        ctx.update(
            chart_labels = labels,
            chart_exp    = [float(exp_m .get(m, 0)) for m in range(1, 13)],
            chart_pur    = [float(pur_m .get(m, 0)) for m in range(1, 13)],
            chart_proc   = [float(proc_m.get(m, 0)) for m in range(1, 13)],
        )

        # ── 4 ▸ Low-stock banner (raw + kitchen) ───────────────────────
        RAW_LIMIT, KIT_LIMIT = Decimal("50"), Decimal("10")
        ctx["low_stock"] = [
            *(p for p in SeasonalProduct.objects.all() if p.stock_raw      <= RAW_LIMIT),
            *(k for k in KitchenProduct .objects.all() if k.stock_on_hand <= KIT_LIMIT),
        ]

        ctx["now"] = timezone.now()
        return ctx
###############################################################################
# 2. Budget-line & Expenditure CRUD
###############################################################################
class BudgetLineListView(LoginRequiredMixin, LowStockMixin, ListView):
    model               = BudgetLine
    template_name       = "expenditures/budgetline_list.html"
    context_object_name = "rows"


class BudgetLineCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = BudgetLine
    form_class = BudgetLineForm
    template_name = "expenditures/budgetline_form.html"
    success_url = reverse_lazy("budgetline_list")
    success_message = "Budget line added."


class BudgetLineUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = BudgetLine
    form_class = BudgetLineForm
    template_name = "expenditures/budgetline_form.html"
    success_url = reverse_lazy("budgetline_list")
    success_message = "Budget line updated."


class BudgetLineDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = BudgetLine
    template_name = "expenditures/budgetline_confirm_delete.html"
    success_url = reverse_lazy("budgetline_list")
    success_message = "Budget line deleted."


# ─────────────────── expenditures ───────────────────────────────────────────


class ExpenditureListView(LoginRequiredMixin, LowStockMixin, TemplateView):
    """
    One table per Budget-line.
    Optional GET params:
        ?budget=<envelope_id>&start=YYYY-MM-DD&end=YYYY-MM-DD
    """
    template_name = "expenditures/expenditure_list.html"

    # ─── private -----------------------------------------------------------
    def _filtered_qs(self):
        qs = (
            Expenditure.objects
            .select_related("budget_line", "budget")
            .order_by("date")                       # chrono inside each table
        )

        env   = self.request.GET.get("budget")
        start = self.request.GET.get("start")
        end   = self.request.GET.get("end")
        blk   = self.request.GET.get("budget_line")     # still allow deep-links

        if env:
            qs = qs.filter(budget_id=env)
        if start:
            qs = qs.filter(date__gte=datetime.strptime(start, "%Y-%m-%d"))
        if end:
            qs = qs.filter(date__lte=datetime.strptime(end, "%Y-%m-%d"))
        if blk:
            qs = qs.filter(budget_line_id=blk)

        # -------- annotate derived total (qty × price @) -------------------
        total_expr = ExpressionWrapper(
            Coalesce(F("quantity"), Value(1)) * F("price_per_unit"),
            output_field=DECIMAL,
        )
        return qs.annotate(total_amount=total_expr)

    # ─── public -----------------------------------------------------------
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        qs = self._filtered_qs()

        # one bucket per budget-line
        groups, grand = [], Decimal("0")
        for bl in (
            qs.values("budget_line_id", "budget_line__name")
              .distinct()
              .order_by("budget_line__name")
        ):
            rows = qs.filter(budget_line_id=bl["budget_line_id"])
            subtotal = rows.aggregate(t=Coalesce(Sum("total_amount"), Decimal(0)))["t"]
            grand   += subtotal
            groups.append({
                "name":     bl["budget_line__name"],
                "rows":     rows,
                "subtotal": subtotal,
            })

        ctx.update(
            groups       = groups,
            grand_total  = grand,
            budgets      = Budget.objects.order_by("-created_at"),
            current_env  = self.request.GET.get("budget", ""),
            start_date   = self.request.GET.get("start", ""),
            end_date     = self.request.GET.get("end",   ""),
        )
        return ctx



class ExpenditureCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Expenditure
    form_class = ExpenditureForm
    template_name = "expenditures/expenditure_form.html"
    success_url = reverse_lazy("expenditure_list")
    success_message = "Expenditure recorded."


class ExpenditureUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Expenditure
    form_class = ExpenditureForm
    template_name = "expenditures/expenditure_form.html"
    success_url = reverse_lazy("expenditure_list")
    success_message = "Expenditure updated."


class ExpenditureDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Expenditure
    template_name = "expenditures/expenditure_confirm_delete.html"
    success_url = reverse_lazy("expenditure_list")
    success_message = "Expenditure deleted."


class ExpenditureDetailView(LoginRequiredMixin, LowStockMixin, DetailView):
    model = Expenditure
    template_name = "expenditures/expenditure_detail.html"
    context_object_name = "obj"


class ExpenditureReportView(LoginRequiredMixin, LowStockMixin, ListView):
    """
    /expenditures/report/<daily|weekly|monthly>/
    """
    model               = Expenditure
    template_name       = "expenditures/expenditure_report.html"
    context_object_name = "rows"

    def get_queryset(self):
        qs     = super().get_queryset().select_related("budget_line", "budget")
        period = self.kwargs["period"]
        today  = date.today()

        if period == "daily":
            qs = qs.filter(date=today)
        elif period == "weekly":
            monday = today - timedelta(days=today.weekday())
            qs = qs.filter(date__range=(monday, today))
        else:  # monthly
            qs = qs.filter(date__year=today.year, date__month=today.month)

        return qs.order_by("budget_line__name")

    def get_context_data(self, **kw):
        ctx   = super().get_context_data(**kw)
        total = self.get_queryset().aggregate(t=Coalesce(Sum("amount"), DEC_ZERO))["t"]
        ctx.update(period=self.kwargs["period"], total=total)
        return ctx


###############################################################################
# 3. Inventory CRUD (Seasonal, Processed, Batches, Consumption)
###############################################################################
# ───── Seasonal products ────────────────────────────────────────────────────


class SeasonalPurchaseListView(LoginRequiredMixin, LowStockMixin, ListView):
   
    model               = SeasonalPurchase
    template_name       = "expenditures/seasonalpurchases_list.html"
    context_object_name = "rows"
    paginate_by         = 50   # keep pages light

    # ── base queryset + filters ───────────────────────────────────
    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("product", "budget")
            .annotate(
                processed = Coalesce(
                    Sum("batches__input_quantity", output_field=DEC), ZERO
                ),
            )
            .annotate(
                remaining = ExpressionWrapper(
                    F("quantity") - F("processed"), output_field=DEC
                )
            )
            .order_by("-date")
        )

        # ---------- filters
        g = self.request.GET
        if prod := g.get("product"):
            qs = qs.filter(product_id=prod)
        if env := g.get("budget"):
            qs = qs.filter(budget_id=env)
        if status := g.get("status"):
            cond = {
                "unprocessed": Q(remaining=F("quantity")),
                "processed":   Q(remaining=ZERO),
                "partial":     Q(remaining__gt=ZERO, remaining__lt=F("quantity")),
            }.get(status)
            if cond:
                qs = qs.filter(cond)
        return qs

    # ── page-level aggregates for header KPIs ─────────────────────
    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        qs  = self.get_queryset()

        ctx.update(
            # bag / kg splits
            total_bags = qs.aggregate(t=Coalesce(Sum("bags_count"), 0))["t"],
            total_kg   = qs.aggregate(t=Coalesce(Sum("quantity"),   ZERO))["t"],

            # money
            total_spent = qs.aggregate(
                t=Coalesce(Sum(ExpressionWrapper(
                    F("quantity") * F("price_per_unit"), output_field=DEC
                )), ZERO)
            )["t"],

            # filters for the <select>s
            products     = SeasonalProduct.objects.all(),
            budgets      = Budget.objects.order_by("-created_at"),
            current_env  = self.request.GET.get("budget", ""),
            current_stat = self.request.GET.get("status", ""),
        )
        return ctx
    

# ═════════════════════════ CREATE ════════════════════════════
class SeasonalPurchaseCreateView(LoginRequiredMixin,
                                 SuccessMessageMixin,
                                 CreateView):
    model               = SeasonalPurchase
    form_class          = SeasonalPurchaseForm
    template_name       = "expenditures/seasonalpurchase_form.html"
    permission_required = "expenditures.add_seasonalpurchase"
    success_url         = reverse_lazy("seasonalpurchase_list")
    success_message     = "Purchase recorded."

    # we do *all* calculations here so even plain `ModelForm` works
    def form_valid(self, form):
        obj = form.save(commit=False)

        # quantity  &  total_cost ------------------------------------------------
        bags = obj.bags_count or 0
        obj.quantity   = Decimal(bags) * obj.bag_weight if obj.bag_weight else Decimal(bags)
        obj.total_cost = obj.quantity * obj.price_per_unit

        # overspend guard (helpful when form is bypassed by API or CSV import)
        if obj.budget and obj.total_cost > obj.budget.remaining:
            form.add_error(
                "budget",
                f"Not enough money in “{obj.budget.name}”; "
                f"{obj.budget.remaining:,.2f} TZS left."
            )
            return self.form_invalid(form)

        obj.save()
        return super().form_valid(form)


# ═════════════════════════ UPDATE ════════════════════════════
class SeasonalPurchaseUpdateView(LoginRequiredMixin,
                                 SuccessMessageMixin,
                                 UpdateView):
    model               = SeasonalPurchase
    form_class          = SeasonalPurchaseForm
    template_name       = "expenditures/seasonalpurchase_form.html"
    permission_required = "expenditures.change_seasonalpurchase"
    success_url         = reverse_lazy("seasonalpurchase_list")
    success_message     = "Purchase updated."

    def form_valid(self, form):
        obj = form.save(commit=False)

        # recalc qty & cost every edit
        bags = obj.bags_count or 0
        obj.quantity   = Decimal(bags) * obj.bag_weight if obj.bag_weight else Decimal(bags)
        obj.total_cost = obj.quantity * obj.price_per_unit

        # overspend guard **only** when budget is changed or cost increases
        if obj.budget and obj.total_cost > obj.budget.remaining + self.object.total_cost:
            form.add_error(
                "budget",
                "Budget can’t cover the new total cost."
            )
            return self.form_invalid(form)

        obj.save()
        return super().form_valid(form)



class SeasonalProductCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = SeasonalProduct
    form_class = SeasonalProductForm
    template_name = "expenditures/seasonalproduct_form.html"
    success_url = reverse_lazy("seasonalproduct_list")
    success_message = "Seasonal product added."


class SeasonalProductUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = SeasonalProduct
    form_class = SeasonalProductForm
    template_name = "expenditures/seasonalproduct_form.html"
    success_url = reverse_lazy("seasonalproduct_list")
    success_message = "Seasonal product updated."


class SeasonalProductDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = SeasonalProduct
    template_name = "expenditures/seasonalproduct_confirm_delete.html"
    success_url = reverse_lazy("seasonalproduct_list")
    success_message = "Seasonal product deleted."


# ───── Processed products ───────────────────────────────────────────────────
class ProcessedProductListView(LoginRequiredMixin, LowStockMixin, ListView):
    """
    Inventory › Finished goods (flour, rice, oil …).

    Adds three runtime columns:
        • produced   – total kg/L made so far
        • consumed   – kitchen usage
        • balance    – stock-on-hand
    """
    model               = ProcessedProduct
    template_name       = "expenditures/processedproduct_list.html"
    context_object_name = "rows"

    def get_queryset(self):
        DEC = DecimalField(max_digits=16, decimal_places=2)
        zero = Value(Decimal("0"), output_field=DEC)

        return (
            super()
            .get_queryset()            # → ProcessedProduct base
            .annotate(
                produced = Coalesce(    # all output from batches
                    Sum("batches__output_quantity"),
                    zero,
                ),
                consumed = Coalesce(    # kitchen usages
                    Sum("daily_consumptions__quantity_used"),
                    zero,
                ),
            )
            .annotate(                  # working stock
                balance = ExpressionWrapper(
                    F("produced") - F("consumed"),
                    output_field=DEC
                )
            )
            .order_by("name")
        )

    # KPI tiles (optional ─ keep if you show them in template)
    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        qs  = self.get_queryset()
        ctx.update(
            total_produced = qs.aggregate(t=Coalesce(Sum("produced"),  Decimal(0)))["t"],
            total_consumed = qs.aggregate(t=Coalesce(Sum("consumed"),  Decimal(0)))["t"],
            total_balance  = qs.aggregate(t=Coalesce(Sum("balance"),   Decimal(0)))["t"],
        )
        return ctx

class ProcessedProductCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = ProcessedProduct
    form_class = ProcessedProductForm
    template_name = "expenditures/processedproduct_form.html"
    success_url = reverse_lazy("processedproduct_list")
    success_message = "Processed product added."


class ProcessedProductUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ProcessedProduct
    form_class = ProcessedProductForm
    template_name = "expenditures/processedproduct_form.html"
    success_url = reverse_lazy("processedproduct_list")
    success_message = "Processed product updated."


class ProcessedProductDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ProcessedProduct
    template_name = "expenditures/processedproduct_confirm_delete.html"
    success_url = reverse_lazy("processedproduct_list")
    success_message = "Processed product deleted."

class SeasonalProductListView(LoginRequiredMixin, LowStockMixin, ListView):
    """
    Inventory › Seasonal products (raw commodities).

    Per-row annotations:
        • bags_total    – # bags purchased
        • kg_total      – total kg purchased (bag-based rows only)
        • kg_processed  – kg milled / pressed
        • kg_remaining  – kg still in store
    """
    model               = SeasonalProduct
    template_name       = "expenditures/seasonalproduct_list.html"
    context_object_name = "rows"

    # ─────────────────────────────────────────────────────────────
    # helpers
    # ─────────────────────────────────────────────────────────────
    DEC   = DecimalField(max_digits=16, decimal_places=2)
    ZERO  = Value(Decimal("0"), output_field=DEC)

    def _kg_expr(self) -> Case:
        """Quantity in kg – only where bag_weight is not null."""
        return Case(
            When(
                purchases__bag_weight__isnull=False,
                then=Cast(F("purchases__quantity"), output_field=self.DEC),
            ),
            default=Value(None),
            output_field=self.DEC,
        )

    def _kg_proc_expr(self) -> Case:
        """Processed kg – only where bag_weight is not null."""
        return Case(
            When(
                purchases__bag_weight__isnull=False,
                then=Cast(F("purchases__batches__input_quantity"),
                          output_field=self.DEC),
            ),
            default=Value(None),
            output_field=self.DEC,
        )

    # ─────────────────────────────────────────────────────────────
    # queryset
    # ─────────────────────────────────────────────────────────────
    def get_queryset(self):
        bags_sum_dec = Cast(
            Sum("purchases__bags_count", output_field=IntegerField()),
            output_field=self.DEC,
        )

        return (
            super()
            .get_queryset()
            .annotate(
                bags_total   = Coalesce(bags_sum_dec,          self.ZERO),
                kg_total     = Coalesce(Sum(self._kg_expr()),  self.ZERO),
                kg_processed = Coalesce(Sum(self._kg_proc_expr()), self.ZERO),
            )
            .annotate(
                kg_remaining = ExpressionWrapper(
                    F("kg_total") - F("kg_processed"),
                    output_field=self.DEC,
                )
            )
            .order_by("name")
        )

    # ─────────────────────────────────────────────────────────────
    # context (KPI tiles)
    # ─────────────────────────────────────────────────────────────
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs  = self.get_queryset()

        ctx.update(
            total_bags      = qs.aggregate(t=Coalesce(Sum("bags_total"),   Decimal(0)))["t"],
            total_kg        = qs.aggregate(t=Coalesce(Sum("kg_total"),     Decimal(0)))["t"],
            total_processed = qs.aggregate(t=Coalesce(Sum("kg_processed"), Decimal(0)))["t"],
            total_remaining = qs.aggregate(t=Coalesce(Sum("kg_remaining"), Decimal(0)))["t"],
        )
        return ctx

# ───── Seasonal purchases ────────────────────────────────────────────────────
class SeasonalPurchaseListView(LoginRequiredMixin, LowStockMixin, ListView):
    model               = SeasonalPurchase
    template_name       = "expenditures/seasonalpurchase_list.html"
    context_object_name = "rows"
    paginate_by         = 50

    def get_queryset(self):
        zero = Value(Decimal("0"), output_field=DECIMAL)

        qs = (
            super()
            .get_queryset()
            .select_related("product", "budget")
            .annotate(
                processed = Coalesce(
                    Sum("batches__input_quantity", output_field=DECIMAL),
                    zero
                )
            )
            .annotate(
                remaining = ExpressionWrapper(
                    F("quantity") - F("processed"),
                    output_field=DECIMAL
                )
            )
            .order_by("-date")
        )

        if prod := self.request.GET.get("product"):
            qs = qs.filter(product_id=prod)
        if env := self.request.GET.get("budget"):
            qs = qs.filter(budget_id=env)
        if status := self.request.GET.get("status"):
            cond = {
                "unprocessed": Q(remaining=F("quantity")),
                "processed":   Q(remaining=zero),
                "partial":     Q(remaining__gt=zero, remaining__lt=F("quantity")),
            }.get(status)
            if cond:
                qs = qs.filter(cond)
        return qs

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        qs  = self.get_queryset()

        money = ExpressionWrapper(
            F("quantity") * F("price_per_unit"),
            output_field=DECIMAL
        )

        ctx.update(
            total_spent   = qs.aggregate(t=Coalesce(Sum(money), DEC_ZERO))["t"],
            total_raw     = qs.aggregate(q=Coalesce(Sum("quantity"),  DEC_ZERO))["q"],
            total_used    = qs.aggregate(q=Coalesce(Sum("processed"), DEC_ZERO))["q"],
            total_balance = qs.aggregate(q=Coalesce(Sum("remaining"), DEC_ZERO))["q"],
            products      = SeasonalProduct.objects.all(),
            budgets       = Budget.objects.order_by("-created_at"),
            current_env   = self.request.GET.get("budget", ""),
            current_status= self.request.GET.get("status", ""),
        )
        return ctx

class SeasonalPurchaseDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = SeasonalPurchase
    template_name = "expenditures/seasonalpurchase_confirm_delete.html"
    success_url = reverse_lazy("seasonalpurchase_list")
    success_message = "Seasonal purchase deleted."


# ───── Processing batches ───────────────────────────────────────────────────
class ProcessingBatchListView(LoginRequiredMixin, LowStockMixin, ListView):
    model               = ProcessingBatch
    template_name       = "expenditures/processingbatch_list.html"
    context_object_name = "rows"
    paginate_by         = 50

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                "source_purchase",
                "processed_product",
                "source_purchase__product",
            )
            .order_by("-date")
        )
        if prod := self.request.GET.get("product"):
            qs = qs.filter(processed_product_id=prod)
        return qs


class ProcessingBatchCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = ProcessingBatch
    form_class = ProcessingBatchForm
    template_name = "expenditures/processingbatch_form.html"
    success_url = reverse_lazy("processingbatch_list")
    success_message = "Processing batch added."


class ProcessingBatchUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ProcessingBatch
    form_class = ProcessingBatchForm
    template_name = "expenditures/processingbatch_form.html"
    success_url = reverse_lazy("processingbatch_list")
    success_message = "Processing batch updated."


class ProcessingBatchDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ProcessingBatch
    template_name = "expenditures/processingbatch_confirm_delete.html"
    success_url = reverse_lazy("processingbatch_list")
    success_message = "Processing batch deleted."


# ───── Daily kitchen consumption ─────────────────────────────────────────────
class DailyConsumptionListView(LoginRequiredMixin, LowStockMixin, ListView):
    """
    Kitchen › Daily consumption (with 30-day KPI & sparkline).
    """
    model               = DailyConsumption
    template_name       = "expenditures/dailyconsumption_list.html"
    context_object_name = "rows"
    paginate_by         = 50

    # --- filters -----------------------------------------------------------
    def _base_qs(self):
        qs    = (super().get_queryset()
                         .select_related("product")
                         .order_by("-date"))
        start = self.request.GET.get("start")
        end   = self.request.GET.get("end")
        prod  = self.request.GET.get("product")
        if start:
            qs = qs.filter(date__gte=datetime.strptime(start, "%Y-%m-%d"))
        if end:
            qs = qs.filter(date__lte=datetime.strptime(end, "%Y-%m-%d"))
        if prod:
            qs = qs.filter(product_id=prod)
        return qs

    def get_queryset(self):
        return self._base_qs()

    # --- KPI + sparkline payload ------------------------------------------
    def get_context_data(self, **kw):
        ctx   = super().get_context_data(**kw)
        base  = self._base_qs()
        ctx["total_used"] = base.aggregate(
            t=Coalesce(Sum("quantity_used"), Decimal(0))
        )["t"]

        # 30-day aggregate for chart
        today   = timezone.localdate()
        thirty  = today - timedelta(days=29)
        series  = [0]*30
        for d in base.filter(date__gte=thirty, date__lte=today):
            idx = (today - d.date).days
            series[29-idx] += float(d.quantity_used)
        ctx["chart_series"] = series
        ctx["chart_labels"] = [(thirty + timedelta(n)).strftime("%d %b")
                               for n in range(30)]
        ctx["products"]     = ProcessedProduct.objects.all()
        return ctx
    

class DailyConsumptionCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = DailyConsumption
    form_class = DailyConsumptionForm
    template_name = "expenditures/dailyconsumption_form.html"
    success_url = reverse_lazy("dailyconsumption_list")
    success_message = "Daily consumption added."

    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        return super().form_valid(form)


class DailyConsumptionUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = DailyConsumption
    form_class = DailyConsumptionForm
    template_name = "expenditures/dailyconsumption_form.html"
    success_url = reverse_lazy("dailyconsumption_list")
    success_message = "Daily consumption updated."


class DailyConsumptionDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = DailyConsumption
    template_name = "expenditures/dailyconsumption_confirm_delete.html"
    success_url = reverse_lazy("dailyconsumption_list")
    success_message = "Daily consumption deleted."


###############################################################################
# 4. Stock dashboard
###############################################################################
class StockDashboardView(LoginRequiredMixin, LowStockMixin, ListView):
    """Shows processed & raw stock levels side-by-side."""
    model               = ProcessedProduct
    template_name       = "expenditures/stock_dashboard.html"
    context_object_name = "rows"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["raw_rows"] = SeasonalProduct.objects.all()
        ctx["today"]    = timezone.localdate()
        return ctx


###############################################################################
# 5. Kitchen products, purchases, usage, dashboard
###############################################################################
class KitchenProductListView(LoginRequiredMixin, LowStockMixin, ListView):
    """
    Inventory › Kitchen products.

    Adds on-the-fly helpers:
        • p.usage_30d   →  list[float]  (daily qty used – last 30 days)
        • p.remaining_pct → Decimal     (% of purchased still on-hand)
    """
    model               = KitchenProduct
    template_name       = "expenditures/kitchen/kitchenproduct_list.html"
    context_object_name = "rows"

    def get_queryset(self):
        today   = timezone.localdate()
        thirty  = today - timedelta(days=29)
        qs = (
            super()
            .get_queryset()
            .prefetch_related("purchases", "usages")
        )

        for p in qs:
            # ---- 30-day consumption sparkline ------------------------------
            series = [0]*30    # index 0 == 29 days ago
            for u in p.usages.filter(date__gte=thirty, date__lte=today):
                idx = (today - u.date).days
                series[29-idx] += float(u.quantity_used)
            p.usage_30d = series

            # ---- remaining % (0-100) --------------------------------------
            p.remaining_pct = (
                Decimal("0") if p.purchased == 0
                else (p.stock_on_hand / p.purchased * 100).quantize(Decimal("0.1"))
            )
        return qs

    # KPI tiles stay the same
    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        qs  = ctx["rows"]
        ctx.update(
            total_purchased = sum(p.purchased     for p in qs),
            total_consumed  = sum(p.used          for p in qs),
            total_balance   = sum(p.stock_on_hand for p in qs),
            today           = timezone.localdate(),   # for tooltip
        )
        return ctx

class KitchenProductCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = KitchenProduct
    form_class = KitchenProductForm
    template_name = "expenditures/kitchen/kitchenproduct_form.html"
    success_url = reverse_lazy("kitchenproduct_list")
    success_message = "Kitchen product added."


class KitchenProductUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = KitchenProduct
    form_class = KitchenProductForm
    template_name = "expenditures/kitchen/kitchenproduct_form.html"
    success_url = reverse_lazy("kitchenproduct_list")
    success_message = "Kitchen product updated."


class KitchenProductDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = KitchenProduct
    template_name = "expenditures/kitchen/kitchenproduct_confirm_delete.html"
    success_url = reverse_lazy("kitchenproduct_list")
    success_message = "Kitchen product deleted."


# ───── Kitchen purchases ─────────────────────────────────────────────────────
class KitchenPurchaseListView(LoginRequiredMixin, LowStockMixin, ListView):
    model               = KitchenPurchase
    template_name       = "expenditures/kitchen/kitchenpurchase_list.html"
    context_object_name = "rows"
    paginate_by         = 50

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("product", "budget")
            .order_by("-date")
        )
        if prod := self.request.GET.get("product"):
            qs = qs.filter(product_id=prod)
        if env := self.request.GET.get("budget"):
            qs = qs.filter(budget_id=env)
        return qs

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        qs  = self.get_queryset()
        money = ExpressionWrapper(F("quantity") * F("price_per_unit"), output_field=DECIMAL)
        ctx.update(
            total_spent = qs.aggregate(t=Coalesce(Sum(money), DEC_ZERO))["t"],
            total_qty   = qs.aggregate(q=Coalesce(Sum("quantity"), DEC_ZERO))["q"],
            products    = KitchenProduct.objects.all(),
            budgets     = Budget.objects.order_by("-created_at"),
            current_env = self.request.GET.get("budget", ""),
        )
        return ctx


class KitchenPurchaseCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = KitchenPurchase
    form_class = KitchenPurchaseForm
    template_name = "expenditures/kitchen/kitchenpurchase_form.html"
    success_url = reverse_lazy("kitchenpurchase_list")
    success_message = "Kitchen purchase recorded."


class KitchenPurchaseUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = KitchenPurchase
    form_class = KitchenPurchaseForm
    template_name = "expenditures/kitchen/kitchenpurchase_form.html"
    success_url = reverse_lazy("kitchenpurchase_list")
    success_message = "Kitchen purchase updated."


class KitchenPurchaseDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = KitchenPurchase
    template_name = "expenditures/kitchen/kitchenpurchase_confirm_delete.html"
    success_url = reverse_lazy("kitchenpurchase_list")
    success_message = "Kitchen purchase deleted."


# ───── Kitchen usages (consumption) ──────────────────────────────────────────
class KitchenUsageListView(LoginRequiredMixin, LowStockMixin, ListView):
    model               = KitchenUsage
    template_name       = "expenditures/kitchen/kitchenusage_list.html"
    context_object_name = "rows"
    paginate_by         = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related("product").order_by("-date")
        if prod := self.request.GET.get("product"):
            qs = qs.filter(product_id=prod)
        return qs

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        qs  = self.get_queryset()
        ctx.update(
            total_used = qs.aggregate(t=Coalesce(Sum("quantity_used"), DEC_ZERO))["t"],
            products   = KitchenProduct.objects.all(),
        )
        return ctx


class KitchenUsageCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = KitchenUsage
    form_class = KitchenUsageForm
    template_name = "expenditures/kitchen/kitchenusage_form.html"
    success_url = reverse_lazy("kitchenusage_list")
    success_message = "Kitchen usage recorded."


class KitchenUsageUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = KitchenUsage
    form_class = KitchenUsageForm
    template_name = "expenditures/kitchen/kitchenusage_form.html"
    success_url = reverse_lazy("kitchenusage_list")
    success_message = "Kitchen usage updated."


class KitchenUsageDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = KitchenUsage
    template_name = "expenditures/kitchen/kitchenusage_confirm_delete.html"
    success_url = reverse_lazy("kitchenusage_list")
    success_message = "Kitchen usage deleted."

class KitchenDashboardView(LoginRequiredMixin, LowStockMixin, TemplateView):
    """Kitchen dashboard – KPI + monthly cost/usage analytics."""
    template_name = "expenditures/kitchen/kitchen_dashboard.html"

    @staticmethod
    def _monthly(model, expr):
        yr = timezone.localdate().year
        rows = (model.objects.filter(date__year=yr)
                .annotate(m=ExtractMonth("date"))
                .values("m")
                .annotate(v=Coalesce(Sum(expr, output_field=DECIMAL), DEC_ZERO)))
        return {r["m"]: r["v"] for r in rows}

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        cost = ExpressionWrapper(F("quantity") * F("price_per_unit"),
                                 output_field=DECIMAL)

        # KPI tiles
        spent  = KitchenPurchase.objects.aggregate(s=Coalesce(Sum(cost), DEC_ZERO))["s"]
        used   = KitchenUsage.objects.aggregate(q=Coalesce(Sum("quantity_used"), DEC_ZERO))["q"]
        stock  = sum(p.stock_on_hand for p in KitchenProduct.objects.all())

        # monthly data (labels already in order 1-12 for Chart.js)
        labels = [calendar.month_abbr[i] for i in range(1, 13)]
        m_buy  = self._monthly(KitchenPurchase, cost)
        m_use  = self._monthly(KitchenUsage,   F("quantity_used"))

        # context
        ctx.update(
            total_spent    = spent,
            total_used_qty = used,
            total_stock    = stock,
            chart_labels   = labels,
            chart_buy      = [float(m_buy.get(i, 0)) for i in range(1, 13)],
            chart_use      = [float(m_use.get(i, 0)) for i in range(1, 13)],
            top_used       = (KitchenUsage.objects
                              .values("product__name", "product__unit")
                              .annotate(q=Sum("quantity_used"))
                              .order_by("-q")[:5]),
            low_kitchen    = [p for p in KitchenProduct.objects.all()
                              if p.stock_on_hand <= Decimal("10")],
            now            = timezone.now(),
        )
        return ctx