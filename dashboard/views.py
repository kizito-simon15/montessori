# dashboard/views.py
from __future__ import annotations

import calendar, json
from decimal    import Decimal
from typing     import Any, Dict, Final, List

from django.db.models import (
    Sum, F, Count, DecimalField, ExpressionWrapper, Value
)
from django.db.models.functions import ExtractMonth        # ← correct import
from django.utils                import timezone
from django.views.generic        import TemplateView

# ─── core / finance / inventory models ──────────────────────────────────────
from apps.students.models  import Student
from apps.staffs.models    import Staff
from apps.corecode.models  import AcademicSession, Installment
from apps.finance.models   import Invoice, Receipt, SalaryInvoice, StudentUniform
from expenditures.models   import (
    Expenditure,
    SeasonalProduct, ProcessedProduct,
    SeasonalPurchase, ProcessingBatch,
    KitchenProduct, KitchenPurchase,
)

# ─── constants & helper expressions ────────────────────────────────────────
DECIMAL : Final = DecimalField(max_digits=16, decimal_places=2)
MONTHS  : Final = [calendar.month_abbr[i] for i in range(1, 13)]
YEAR    : Final = timezone.localdate().year

COST_PURCHASE  = ExpressionWrapper(F("quantity") * F("price_per_unit"), output_field=DECIMAL)
COST_EXP       = ExpressionWrapper(F("quantity") * F("price_per_unit"), output_field=DECIMAL)
INV_ONE        = Value(1, output_field=DECIMAL)     # each invoice counts as 1 (Decimal)

# ─── view ───────────────────────────────────────────────────────────────────
class DashboardView(TemplateView):
    template_name = "dashboard.html"

    # ── helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _series(model, date_field: str, expr) -> List[float]:
        """Return float[12] – monthly sums for current calendar year."""
        base = [0.0] * 12
        rows = (
            model.objects
                 .filter(**{f"{date_field}__year": YEAR})
                 .annotate(m=ExtractMonth(date_field))
                 .values("m")
                 .annotate(v=Sum(expr, output_field=DECIMAL))
        )
        for r in rows:
            base[r["m"] - 1] = float(r["v"] or 0)
        return base

    @staticmethod
    def _student_pie() -> tuple[list[str], list[int]]:
        qs = (
            Student.objects
                   .filter(current_status="active", completed=False)
                   .values("current_class__name")
                   .annotate(c=Count("id"))
                   .order_by()
        )
        return (
            [d["current_class__name"] or "N/A" for d in qs],
            [d["c"] for d in qs],
        )

    # ── context ─────────────────────────────────────────────────────────
    def get_context_data(self, **kw) -> Dict[str, Any]:
        ctx   = super().get_context_data(**kw)
        today = timezone.localdate()

        # ── KPI tiles ---------------------------------------------------
        students = Student.objects.count()
        staff    = Staff.objects.count()

        sess = AcademicSession.objects.filter(current=True).first()
        inst = Installment.objects.filter(current=True).first()
        inv_qs = Invoice.objects.all()
        if sess and inst:
            inv_qs = inv_qs.filter(session=sess, installment=inst)

        inv_cnt   = inv_qs.count()
        inv_total = inv_qs.aggregate(t=Sum("invoice_amount"))["t"] or Decimal(0)
        inv_paid  = Receipt.objects.filter(invoice__in=inv_qs)\
                                   .aggregate(t=Sum("amount_paid"))["t"] or Decimal(0)
        inv_bal   = inv_total - inv_paid

        payroll_qs    = SalaryInvoice.objects.filter(month__year=today.year,
                                                     month__month=today.month)
        payroll_slips = payroll_qs.count()
        payroll_total = payroll_qs.aggregate(t=Sum("net_salary"))["t"] or Decimal(0)

        spent_exp     = Expenditure.objects.aggregate(t=Sum(COST_EXP))["t"] or Decimal(0)
        spent_kitch   = KitchenPurchase .objects.aggregate(t=Sum(COST_PURCHASE))["t"] or Decimal(0)
        spent_season  = SeasonalPurchase.objects.aggregate(t=Sum(COST_PURCHASE))["t"] or Decimal(0)
        spent_procfee = ProcessingBatch .objects.aggregate(t=Sum("processing_fee"))["t"] or Decimal(0)
        spent_total   = spent_exp + spent_kitch + spent_season + spent_procfee + payroll_total

        income_total  = Receipt.objects.aggregate(t=Sum("amount_paid"))["t"] or Decimal(0)
        net_balance   = income_total - spent_total

        stock_raw   = sum(p.stock_raw      for p in SeasonalProduct.objects.all())
        stock_proc  = sum(p.stock_on_hand  for p in ProcessedProduct.objects.all())
        stock_kitch = sum(p.stock_on_hand  for p in KitchenProduct .objects.all())

        ctx["kpi_cards"] = [
            ("Students",      students,             "",                        "🎓"),
            ("Staff",         staff,                "",                        "👔"),
            ("Invoices",      inv_cnt,              f"{inv_total:,.0f}",       "💳"),
            ("Fees Paid",     f"{inv_paid:,.0f}",   f"Bal {inv_bal:,.0f}",     "💰"),
            ("Payroll",       payroll_slips,        f"{payroll_total:,.0f}",   "🧾"),
            ("Expenditure",   f"{spent_total:,.0f}",f"Net {net_balance:,.0f}", "💸"),
            ("Raw Stock",     f"{stock_raw:,.0f}",  "kg",                      "🌾"),
            ("Processed",     f"{stock_proc:,.0f}", "kg/lt",                   "🏭"),
            ("Kitchen Stock", f"{stock_kitch:,.0f}","mixed",                   "🍲"),
        ]

        # ── Monthly series --------------------------------------------
        income_m   = self._series(Receipt,         "date_paid",  F("amount_paid"))
        exp_m      = self._series(Expenditure,     "date",       COST_EXP)
        kbuy_m     = self._series(KitchenPurchase, "date",       COST_PURCHASE)
        sbuy_m     = self._series(SeasonalPurchase,"date",       COST_PURCHASE)
        fee_m      = self._series(ProcessingBatch, "date",       F("processing_fee"))
        payroll_m  = self._series(SalaryInvoice,   "month",      F("net_salary"))
        invcnt_m   = self._series(Invoice,         "created_at", INV_ONE)

        cash_out_m = [sum(x) for x in zip(exp_m, kbuy_m, sbuy_m, fee_m, payroll_m)]
        net_m      = [inc - out for inc, out in zip(income_m, cash_out_m)]

        # ── Pie --------------------------------------------------------
        pie_labels, pie_vals = self._student_pie()

        # ── inject to template ----------------------------------------
        ctx.update(
            THIS_YEAR                = YEAR,
            bar_labels_income        = json.dumps(MONTHS),
            bar_vals_income          = json.dumps(income_m),
            bar_vals_kitchen         = json.dumps(kbuy_m),
            bar_vals_seasonal_buy    = json.dumps(sbuy_m),
            bar_vals_processing_fee  = json.dumps(fee_m),
            bar_vals_payroll         = json.dumps(payroll_m),
            bar_vals_invoices        = json.dumps(invcnt_m),

            line_vals_expense  = json.dumps(exp_m),
            line_vals_cash_out = json.dumps(cash_out_m),
            line_vals_net      = json.dumps(net_m),

            pie_labels  = json.dumps(pie_labels),
            pie_values  = json.dumps(pie_vals),

            total_income   = f"{sum(income_m):,.0f}",
            total_expense  = f"{sum(cash_out_m):,.0f}",
            net_balance    = f"{net_balance:,.0f}",
        )
        return ctx
