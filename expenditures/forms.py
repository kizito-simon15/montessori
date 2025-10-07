from __future__ import annotations

from decimal import Decimal

from typing  import Any, Dict
from django import forms
from django.core.exceptions import ValidationError
from django.forms            import widgets

from apps.finance.models import Receipt, Budget      # Budget for type hints only
from django.db.models import Sum 
from .models import (
    BudgetLine, Expenditure,
    SeasonalProduct, SeasonalPurchase,
    ProcessedProduct, ProcessingBatch,
    DailyConsumption,
    KitchenProduct, KitchenPurchase, KitchenUsage,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────
DATE_WIDGET = widgets.DateInput(attrs={"type": "date"})
BASE_ATTRS  = {"class": "form-control"}


class _BaseModelForm(forms.ModelForm):
    """Inject Bootstrap class into every widget."""
    def __init__(self, *a: Any, **k: Any) -> None:        # noqa: D401 (simple doc)
        super().__init__(*a, **k)
        for f in self.fields.values():
            f.widget.attrs = {**BASE_ATTRS, **f.widget.attrs}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Cash-flow
# ─────────────────────────────────────────────────────────────────────────────
class BudgetLineForm(_BaseModelForm):
    class Meta:
        model  = BudgetLine
        fields = ["name"]


class ExpenditureForm(_BaseModelForm):
    """
    • User types **price @ unit** and (optionally) quantity.
    • Form populates `total_cost` and enforces envelope guard.
    """
    class Meta:
        model  = Expenditure
        fields = [
            "budget", "budget_line",
            "item_name",
            "price_per_unit", "quantity", "unit",
            "date", "description", "attachment",
        ]
        widgets = {"date": DATE_WIDGET}

    # price must be > 0  (field-level)
    def clean_price_per_unit(self):
        p = self.cleaned_data["price_per_unit"]
        if p <= 0:
            raise ValidationError("Price must be above zero.")
        return p

    # derive total + overspend check  (form-wide)
    def clean(self):
        c   = super().clean()
        qty = c.get("quantity") or Decimal("1")
        tot = (c.get("price_per_unit") or Decimal("0")) * qty
        c["total_cost"] = tot

        bud = c.get("budget")
        if bud and self.instance.pk is None and tot > bud.remaining:
            self.add_error("budget",
                f"Not enough money in “{bud.name}”; {bud.remaining:,.2f} TZS left.")
        return c

# ─────────────────────────────────────────────────────────────────────────────
# 2. Inventory – Seasonal
# ─────────────────────────────────────────────────────────────────────────────
class SeasonalProductForm(_BaseModelForm):
    class Meta:
        model  = SeasonalProduct
        fields = ["name", "unit", "processable"]


class SeasonalPurchaseForm(_BaseModelForm):
    """
    Validate:
        • price > 0
        • bags_count > 0
        • sufficient money left in the chosen Budget envelope
    On update we *exclude* the current row from the running-total query so
    users can edit a purchase without false “overspend” errors.
    """

    class Meta:
        model  = SeasonalPurchase
        fields = [
            "budget",          # envelope paying for the purchase
            "product",
            "bags_count",      # mandatory
            "bag_weight",      # optional (kg / bag)
            "price_per_unit",  # TZS / kg  *or*  TZS / bag
            "date",
            "invoice_file",
            "notes",
        ]
        widgets = {"date": DATE_WIDGET}

    # --------------------------------------------------------------------- #
    #  Field-level checks
    # --------------------------------------------------------------------- #
    def clean_price_per_unit(self):
        val = self.cleaned_data["price_per_unit"]
        if val <= 0:
            raise ValidationError("Price must be above zero.")
        return val

    def clean_bags_count(self):
        bags = self.cleaned_data["bags_count"]
        if bags <= 0:
            raise ValidationError("Enter number of bags (> 0).")
        return bags

    # --------------------------------------------------------------------- #
    #  Form-level checks (budget overspend, compute quantity)
    # --------------------------------------------------------------------- #
    def clean(self):
        cleaned = super().clean()

        bags        = cleaned.get("bags_count") or 0
        bag_weight  = cleaned.get("bag_weight")
        price       = cleaned.get("price_per_unit") or Decimal(0)
        budget      = cleaned.get("budget")

        # Quantity exactly the way the model does it in save()
        qty = Decimal(bags) * bag_weight if bag_weight else Decimal(bags)
        cleaned["quantity"] = qty                       # push into instance

        if not budget:
            return cleaned

        # ------------------------------------------------------------------
        #  How much is already committed in this Budget *excluding* me?
        # ------------------------------------------------------------------
        spent = (
            SeasonalPurchase.objects.filter(budget=budget)
            .exclude(pk=self.instance.pk or 0)
            .aggregate(t=Sum("total_cost"))["t"] or Decimal(0)
        )

        projected_spend = spent + (qty * price)

        if projected_spend > budget.allocated_amount:
            self.add_error(
                "budget",
                (
                    f"Overspend detected – envelope “{budget.name}” has "
                    f"only {(budget.allocated_amount - spent):,.2f} TZS left."
                ),
            )

        return cleaned

# ─────────────────────────────────────────────────────────────────────────────
# 3. Inventory – Processing
# ─────────────────────────────────────────────────────────────────────────────
class ProcessedProductForm(_BaseModelForm):
    class Meta:
        model  = ProcessedProduct
        fields = ["name", "source_product", "unit"]

    def clean_name(self) -> str:  # case-insensitive uniqueness
        name = self.cleaned_data["name"].strip()
        qs   = ProcessedProduct.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A processed product with this name exists.")
        return name

    def clean(self) -> dict[str, Any]:
        c   = super().clean()
        src = c.get("source_product")
        if self.instance.pk and src and src != self.instance.source_product:
            if self.instance.batches.exists():
                self.add_error("source_product",
                               "Cannot change source product – batches already recorded.")
        return c


class ProcessingBatchForm(_BaseModelForm):
    class Meta:
        model  = ProcessingBatch
        fields = [
            "source_purchase", "processed_product",
            "input_quantity", "output_quantity",
            "date", "processing_fee",
        ]
        widgets = {"date": DATE_WIDGET}

    def __init__(self, *a: Any, **k: Any) -> None:
        super().__init__(*a, **k)
        src_purchase = (
            self.initial.get("source_purchase")
            or self.data.get("source_purchase")
            or self.instance.source_purchase_id
        )
        if src_purchase:
            purchase = SeasonalPurchase.objects.filter(pk=src_purchase).first()
            if purchase:
                self.fields["processed_product"].queryset = ProcessedProduct.objects.filter(
                    source_product=purchase.product
                )

    def clean(self) -> dict[str, Any]:
        c = super().clean()
        in_q  = c.get("input_quantity")  or Decimal("0")
        out_q = c.get("output_quantity") or Decimal("0")
        pur   = c.get("source_purchase")
        if in_q <= 0:
            self.add_error("input_quantity", "Input qty must be > 0.")
        if out_q <= 0:
            self.add_error("output_quantity", "Output qty must be > 0.")
        if out_q > in_q:
            self.add_error("output_quantity", "Output cannot exceed input.")
        if pur and in_q:
            available = pur.raw_remaining
            if in_q > available:
                self.add_error("input_quantity",
                               f"Only {available} {pur.product.unit} left in this purchase.")
        return c

# ─────────────────────────────────────────────────────────────────────────────
# 4. Inventory – Daily consumption
# ─────────────────────────────────────────────────────────────────────────────
class DailyConsumptionForm(_BaseModelForm):
    """
    Bootstrap-ready form for a single kitchen-usage line.
    """
    class Meta:
        model   = DailyConsumption
        fields  = ["product", "quantity_used", "date", "remarks"]
        widgets = {"date": DATE_WIDGET}

    def clean_quantity_used(self):
        val = self.cleaned_data["quantity_used"]
        if val <= 0:
            raise ValidationError("Quantity must be above zero.")
        return val

    def clean(self):
        c   = super().clean()
        prod = c.get("product")
        qty  = c.get("quantity_used") or Decimal(0)
        if prod and qty > prod.stock_on_hand:
            self.add_error(
                "quantity_used",
                f"Not enough stock; only {prod.stock_on_hand} {prod.unit} left."
            )
        return c



# ───────────────────────── Kitchen products & usage ─────────────────────────
class KitchenProductForm(_BaseModelForm):
    class Meta:
        model  = KitchenProduct
        fields = ["name", "unit"]

    def clean_name(self):  # case-insensitive uniqueness
        name = self.cleaned_data["name"].strip()
        qs   = KitchenProduct.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A kitchen product with this name already exists.")
        return name


class KitchenPurchaseForm(_BaseModelForm):
    class Meta:
        model  = KitchenPurchase
        fields = ["budget",           # NEW
                  "product", "quantity", "price_per_unit", "date"]
        widgets = {"date": DATE_WIDGET}

    def clean(self):
        c = super().clean()
        q  = c.get("quantity") or Decimal("0")
        pu = c.get("price_per_unit") or Decimal("0")
        bud: Budget | None = c.get("budget")
        if q <= 0:
            self.add_error("quantity", "Quantity must be above zero.")
        if pu <= 0:
            self.add_error("price_per_unit", "Price per unit must be above zero.")
        if bud and q and pu and self.instance.pk is None:
            total = q * pu
            if total > bud.remaining:
                self.add_error("budget",
                               f"Not enough money in “{bud.name}”; "
                               f"{bud.remaining:,.2f} TSh left.")
        return c


class KitchenUsageForm(_BaseModelForm):
    class Meta:
        model   = KitchenUsage
        fields  = ["product", "quantity_used", "date"]
        widgets = {"date": DATE_WIDGET}

    def clean(self):
        c   = super().clean()
        qty = c.get("quantity_used") or Decimal("0")
        prod= c.get("product")
        if qty <= 0:
            self.add_error("quantity_used", "Quantity must be above zero.")
        elif prod and qty > prod.stock_on_hand:
            self.add_error("quantity_used",
                           f"Not enough stock; only {prod.stock_on_hand} {prod.unit} left.")
        return c
