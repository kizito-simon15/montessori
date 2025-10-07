# apps/finance/ledger.py
# Updated  05 Jul 2025 — now exposes month_profit for dashboards
"""
YearLedger ➜ income, budget allocations & costs for a calendar year
-------------------------------------------------------------------
NEW  • tracks how much cash is ear-marked each month via Budget,
     • stores per-month profit so UI code can read it directly.
UNCH • receipts, salary cost and all other expense buckets.
"""

from __future__ import annotations

from calendar import month_abbr
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, ExtractMonth
from django.utils import timezone

# ── local-app models ───────────────────────────────────────────────
from apps.finance.models import Budget, Receipt, SalaryInvoice
from expenditures.models import (
    Expenditure,
    KitchenPurchase,
    ProcessingBatch,
    SeasonalPurchase,
)

# ── constants ──────────────────────────────────────────────────────
DECIMAL: DecimalField = DecimalField(max_digits=16, decimal_places=2)
THIS_YEAR: int = timezone.localdate().year


def _year_map() -> dict[int, Decimal]:
    """Return {1:0, …, 12:0} filled with `Decimal` zeros."""
    return {m: Decimal("0") for m in range(1, 13)}


# ══════════════════════════════════════════════════════════════════
#  Main façade
# ══════════════════════════════════════════════════════════════════
class YearLedger:
    """
    Aggregates *all* money in/out + stock movement for one calendar year.

    v2.1 (05 Jul 2025)
    ──────────────────
    •   Adds `month_profit` so views can access `ledger.month_profit[m]`
        without re-calculating on the fly.
    """

    # ── construction ────────────────────────────────────────────
    def __init__(self, year: int | None = None) -> None:
        self.year = year or THIS_YEAR

        # month ➜ Decimal maps
        self.month_income = _year_map()        # Σ receipts
        self.month_salary_cost = _year_map()   # Σ net salaries
        self.month_expense = _year_map()       # Σ other outgoings
        self.month_budget_alloc = _year_map()  # Σ Budget.allocated_amount
        self.month_processed = _year_map()     # Σ processed qty
        self.month_remaining = _year_map()     # Σ remaining raw qty
        self.month_profit = _year_map()        # Σ profit (NEW)

        self._load()

    # ── quick totals ────────────────────────────────────────────
    @property
    def total_income(self) -> Decimal:
        return sum(self.month_income.values())

    @property
    def total_cost(self) -> Decimal:
        return sum(self.month_salary_cost.values()) + sum(
            self.month_expense.values()
        )

    @property
    def profit(self) -> Decimal:
        return self.total_income - self.total_cost

    @property
    def total_budget_allocated(self) -> Decimal:
        return sum(self.month_budget_alloc.values())

    # ── data loader (private) ───────────────────────────────────
    def _load(self) -> None:  # noqa: C901 – long but straight-forward
        # 1⃣ Income (student receipts)
        for row in (
            Receipt.objects.filter(date_paid__year=self.year)
            .annotate(m=ExtractMonth("date_paid"))
            .values("m")
            .annotate(v=Coalesce(Sum("amount_paid"), Decimal("0")))
        ):
            self.month_income[row["m"]] = row["v"]

        # 2⃣ Salary cost (net salaries actually paid)
        for row in (
            SalaryInvoice.objects.filter(month__year=self.year)
            .annotate(m=ExtractMonth("month"))
            .values("m")
            .annotate(v=Coalesce(Sum("net_salary"), Decimal("0")))
        ):
            self.month_salary_cost[row["m"]] = row["v"]

        # 3⃣ Budget allocations (ear-marked each month)
        for row in (
            Budget.objects.filter(created_at__year=self.year)
            .annotate(m=ExtractMonth("created_at"))
            .values("m")
            .annotate(v=Coalesce(Sum("allocated_amount"), Decimal("0")))
        ):
            self.month_budget_alloc[row["m"]] = row["v"]

        # 4⃣ Other operating expenses  (direct + derived)
        exp_map = _year_map()

        # 4-a  direct expenditures
        for row in (
            Expenditure.objects.filter(date__year=self.year)
            .annotate(m=ExtractMonth("date"))
            .values("m")
            .annotate(v=Coalesce(Sum("amount"), Decimal("0")))
        ):
            exp_map[row["m"]] += row["v"]

        # 4-b  kitchen purchases  – qty × price/unit
        kp_cost = ExpressionWrapper(
            F("quantity") * F("price_per_unit"), output_field=DECIMAL
        )
        for row in (
            KitchenPurchase.objects.filter(date__year=self.year)
            .annotate(m=ExtractMonth("date"))
            .values("m")
            .annotate(v=Coalesce(Sum(kp_cost), Decimal("0")))
        ):
            exp_map[row["m"]] += row["v"]

        # 4-c  seasonal/raw commodity purchases
        sp_cost = ExpressionWrapper(
            F("quantity") * F("price_per_unit"), output_field=DECIMAL
        )
        for row in (
            SeasonalPurchase.objects.filter(date__year=self.year)
            .annotate(m=ExtractMonth("date"))
            .values("m")
            .annotate(v=Coalesce(Sum(sp_cost), Decimal("0")))
        ):
            exp_map[row["m"]] += row["v"]

        # 4-d  mill / press processing fees
        for row in (
            ProcessingBatch.objects.filter(date__year=self.year, processing_fee__gt=0)
            .annotate(m=ExtractMonth("date"))
            .values("m")
            .annotate(v=Coalesce(Sum("processing_fee"), Decimal("0")))
        ):
            exp_map[row["m"]] += row["v"]

        self.month_expense = exp_map

        # 5⃣ Quantities (processed + remaining raw)
        for row in (
            ProcessingBatch.objects.filter(date__year=self.year)
            .annotate(m=ExtractMonth("date"))
            .values("m")
            .annotate(v=Coalesce(Sum("output_quantity"), Decimal("0")))
        ):
            self.month_processed[row["m"]] = row["v"]

        for m in range(1, 13):
            total_purchased = SeasonalPurchase.objects.filter(
                date__year=self.year, date__month=m
            ).aggregate(t=Coalesce(Sum("quantity"), Decimal("0")))["t"]
            total_used = ProcessingBatch.objects.filter(
                source_purchase__date__year=self.year,
                source_purchase__date__month=m,
            ).aggregate(t=Coalesce(Sum("input_quantity"), Decimal("0")))["t"]
            self.month_remaining[m] = total_purchased - total_used

        # 6⃣ Profit per month (NEW)
        for m in range(1, 13):
            self.month_profit[m] = (
                self.month_income[m]
                - self.month_salary_cost[m]
                - self.month_expense[m]
            )

    # ── helpers for charts / JSON ───────────────────────────────
    @property
    def chart_labels(self) -> list[str]:
        """['Jan', 'Feb', … 'Dec']"""
        return [month_abbr[m] for m in range(1, 13)]

    def as_dict(self) -> dict[str, list[float] | int]:
        """Convenient serialisation for Chart.js / API responses."""
        return {
            "year": self.year,
            "labels": self.chart_labels,
            "income": [float(self.month_income[m]) for m in range(1, 13)],
            "budget": [float(self.month_budget_alloc[m]) for m in range(1, 13)],
            "salary": [float(self.month_salary_cost[m]) for m in range(1, 13)],
            "expense": [float(self.month_expense[m]) for m in range(1, 13)],
            "profit": [float(self.month_profit[m]) for m in range(1, 13)],
            "processed": [float(self.month_processed[m]) for m in range(1, 13)],
            "remaining_raw": [
                float(self.month_remaining[m]) for m in range(1, 13)
            ],
        }
