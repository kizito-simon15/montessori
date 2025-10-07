# apps/expenditures/models.py
# ✨ updated 07 Jul 2025  – single authoritative version
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid    import uuid4
from typing  import Final

from django.conf            import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db               import models
from django.db.models        import (
    Sum, Min, Max, F, Q,
    DecimalField, ExpressionWrapper,
)
from django.utils            import timezone

# ─── finance side – envelopes & receipts ──────────────────────────
from apps.finance.models import Budget, Receipt            # noqa: I202  (isort)

# ─── helpers & constants ──────────────────────────────────────────
D2:   Final = Decimal("0.01")   # 2-dp quantise helper
D1:   Final = Decimal("0.1")    # 1-dp helper
DEC2: Final = Decimal("0.01")   # alias (readability)


# ════════════════════════════════════════════════════════════════════════════
# 0.  Abstract timestamp helper
# ════════════════════════════════════════════════════════════════════════════
class TimeStampedModel(models.Model):
    created  = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created"]


# ════════════════════════════════════════════════════════════════════════════
# 1.  Cash-flow  (budget lines, OPEX expenditures)
# ════════════════════════════════════════════════════════════════════════════
class BudgetLine(TimeStampedModel):
    """Chart-of-accounts bucket (Fuel, Repairs, Stationery …)."""
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering            = ["name"]
        verbose_name        = "Budget line"
        verbose_name_plural = "Budget lines"

    def __str__(self) -> str: return self.name

# ─── expenditures/models.py ──────────────────────────────────────────────
class Expenditure(TimeStampedModel):
    """
    Operating cash-outflow backed by a Budget envelope.

    • `price_per_unit`  → TZS for ONE unit (required, > 0)
    • `quantity`        → how many units (optional; 1   if blank)
    • `total_cost`      → price_per_unit × quantity  (auto-filled, indexed)
    """

    # funding … unchanged …
    budget       = models.ForeignKey(Budget,       on_delete=models.PROTECT, related_name="operating_expenditures")
    receipt      = models.ForeignKey(Receipt,      on_delete=models.PROTECT, related_name="expenditures",
                                     null=True, blank=True)
    budget_line  = models.ForeignKey(BudgetLine,   on_delete=models.PROTECT, related_name="expenditures")

    # ─── amounts ────────────────────────────────────────────────────────
    item_name       = models.CharField(max_length=120)

    price_per_unit  = models.DecimalField("Price @ unit (TZS)",
                                          max_digits=14, decimal_places=2,
                                          validators=[MinValueValidator(D2)])
    quantity        = models.DecimalField(max_digits=14, decimal_places=2,
                                          validators=[MinValueValidator(D2)],
                                          blank=True, null=True)
    total_cost      = models.DecimalField(editable=False, max_digits=16, decimal_places=2)

    unit            = models.CharField(max_length=20, blank=True, null=True)

    date        = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)
    attachment  = models.FileField(upload_to="expenditure_docs/%Y/%m/", blank=True)

    class Meta:
        ordering = ["-date"]
        indexes  = [
            models.Index(fields=["date"]),
            models.Index(fields=["budget_line"]),
            models.Index(fields=["budget"]),
            models.Index(fields=["receipt"]),
            models.Index(fields=["total_cost"]),
        ]

    # ─── life-cycle helpers ────────────────────────────────────────────
    def clean(self):
        super().clean()

        if self.price_per_unit <= 0:
            raise ValidationError({"price_per_unit": "Must be positive."})

        qty = self.quantity or Decimal("1")
        self.total_cost = (self.price_per_unit * qty).quantize(DEC2)

        # overspend check on INSERT only
        if self.pk is None and self.total_cost > self.budget.remaining:
            raise ValidationError({
                "budget": (
                    f"Insufficient funds in “{self.budget.name}”. "
                    f"Remaining {self.budget.remaining:,.2f} TZS."
                )
            })

    def save(self, *a, **kw):
        # (clean() already sets total_cost)
        if self.quantity is None:
            self.quantity = Decimal("1")          #  default to “1 @ price”
        super().save(*a, **kw)

    # ─── niceties ──────────────────────────────────────────────────────
    def __str__(self):
        qty = f" × {self.quantity}" if self.quantity else ""
        return f"{self.item_name} – {self.total_cost:,.2f}{qty}"

# ════════════════════════════════════════════════════════════════════════════
# 2.  Seasonal inventory  (raw commodities, purchases, processing)
# ════════════════════════════════════════════════════════════════════════════
def _receipt_upload(instance: "SeasonalPurchase", fn: str) -> str:
    return f"purchases/{timezone.now():%Y}/{uuid4().hex}{Path(fn).suffix.lower()}"




# ─────────────────────────────────────────────────────────────────────────────
# 2.  Seasonal inventory  – products & purchases
# ─────────────────────────────────────────────────────────────────────────────
# apps/expenditures/models.py  – Seasonal products & purchases
# ──────────────────────────────────────────────────────────────


from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid    import uuid4

from django.conf                import settings
from django.core.exceptions     import ValidationError
from django.core.validators     import MinValueValidator
from django.db                  import models
from django.db.models           import (
    DecimalField, ExpressionWrapper, F, Min, Max, Sum,
)
from django.db.models.functions import Coalesce
from django.utils               import timezone

from apps.finance.models import Budget                      # late import is OK here

# ---------------------------------------------------------------------------
# shared helpers / constants
# ---------------------------------------------------------------------------
DEC2      = Decimal("0.01")
D2        = Decimal("0.01")                                # used in MinValueValidator
DECIMAL16 = DecimalField(max_digits=16, decimal_places=2)

def _r2(value: Decimal | int | float | str | None) -> Decimal:
    """Bankers–round anything to 2 dp."""
    return Decimal(value or 0).quantize(DEC2, ROUND_HALF_UP)

def _receipt_upload(instance, filename) -> str:
    """Uploads/receipts/<budget-id>/<uuid4>.<ext>"""
    ext = Path(filename).suffix
    return f"uploads/receipts/{instance.budget_id}/{uuid4().hex}{ext}"


# ──────────────────────────────────────────────────────────────────────────
# 1. Seasonal products (commodity master)
# ──────────────────────────────────────────────────────────────────────────
class SeasonalProduct(models.Model):
    """
    Commodity bought seasonally (maize, paddy, sunflower …).
    Stock is counted in bags unless `bag_weight` is supplied on a purchase –
    then we track kilograms as well.
    """
    name        = models.CharField(max_length=80, unique=True)
    unit        = models.CharField(max_length=20, default="kg")
    processable = models.BooleanField(
        default=True,
        help_text="Untick for items that will never be processed.",
    )

    class Meta:
        ordering = ["name"]

    # ── quick category flag (UI badge) ────────────────────────────
    @property
    def category(self) -> str:
        return "Processable" if self.processable else "Raw"

    # ── stock maths ------------------------------------------------
    total_purchased = property(
        lambda s: s.purchases.aggregate(q=Sum("quantity"))["q"] or Decimal(0)
    )

    # batches that refer to *any* purchase of this product
    @property
    def purchases_related_batches(self):
        from .models import ProcessingBatch                  # late import
        return ProcessingBatch.objects.filter(source_purchase__product=self)

    total_processed = property(
        lambda s: s.purchases_related_batches
                    .aggregate(q=Sum("input_quantity"))["q"] or Decimal(0)
    )

    stock_raw = property(
        lambda s: _r2(s.total_purchased - s.total_processed)
    )

    # ── FIFO stock value (TZS) ------------------------------------
    @property
    def stock_value(self) -> Decimal:
        remain = self.stock_raw
        val    = Decimal(0)
        # newest-first – cheaper than Python-side sorting
        for p in self.purchases.order_by("-date", "-pk"):
            take = min(remain, p.quantity)
            val += take * p.price_per_unit
            remain -= take
            if remain <= 0:
                break
        return _r2(val)

    # ── price helpers ---------------------------------------------
    def _cost_expr(self):
        return ExpressionWrapper(
            F("quantity") * F("price_per_unit"),
            output_field=DECIMAL16,
        )

    def _price_aggr(self, lookup) -> Decimal:
        return _r2(self.purchases.aggregate(v=lookup)["v"])

    @property
    def latest_price(self) -> Decimal:
        last = self.purchases.order_by("-date", "-pk").first()
        return _r2(last.price_per_unit) if last else Decimal(0)

    @property
    def avg_price(self) -> Decimal:
        data = self.purchases.aggregate(
            q=Sum("quantity"),
            v=Sum(self._cost_expr()),
        )
        return (
            _r2(data["v"]) / data["q"] if data["q"] else Decimal(0)
        )

    min_price = property(lambda s: s._price_aggr(Min("price_per_unit")))
    max_price = property(lambda s: s._price_aggr(Max("price_per_unit")))

    def __str__(self) -> str:
        return self.name


# ──────────────────────────────────────────────────────────────────────────
# 2. Seasonal purchase  (every spend line now carries `total_cost`)
# ──────────────────────────────────────────────────────────────────────────
class SeasonalPurchase(models.Model):
    """
    A single seasonal purchase funded by a **Budget** envelope.

    Bags-first rules
    ────────────────
    • `bags_count` **required** – represents stock units.  
    • If `bag_weight` is given → quantity = bags × kg.  
    • Else → quantity = bags (unit = “bag”).
    """

    # funding & commodity -----------------------------------------------------
    budget  = models.ForeignKey(
        Budget, on_delete=models.PROTECT, related_name="seasonal_purchases"
    )
    product = models.ForeignKey(
        SeasonalProduct, on_delete=models.PROTECT, related_name="purchases"
    )

    # quantities --------------------------------------------------------------
    bags_count = models.PositiveIntegerField()
    bag_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Weight per bag (kg, optional)",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(D2)],
    )

    # money & meta ------------------------------------------------------------
    price_per_unit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(D2)],
        help_text="TZS / kg or TZS / bag",
    )
    total_cost = models.DecimalField(                     # <-- NEW PERSISTED FIELD
        max_digits=16,
        decimal_places=2,
        editable=False,
        default=0,
    )

    date         = models.DateField(default=timezone.now)
    invoice_file = models.FileField(upload_to=_receipt_upload, blank=True)
    notes        = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]
        indexes  = [models.Index(fields=["product", "date"])]

    # ----------------------------- validation -------------------------------
    def clean(self):
        super().clean()

        if self.bags_count <= 0:
            raise ValidationError({"bags_count": "Enter number of bags (> 0)."})

        # overspend guard (insert only)
        if self.pk is None and self.total_cost > self.budget.remaining:
            raise ValidationError(
                {
                    "budget": (
                        f"Insufficient funds in “{self.budget.name}” "
                        f"(remaining {self.budget.remaining:,.2f} TZS)."
                    )
                }
            )

    # ----------------------------- persistence ------------------------------
    def save(self, *args, **kwargs):
        # derive quantity (kg OR bags) ---------------------------------------
        if self.bag_weight:                              # kg mode
            self.quantity = _r2(Decimal(self.bags_count) * self.bag_weight)
        else:                                            # 1 bag = 1 unit
            self.quantity = Decimal(self.bags_count)

        # compute & persist total_cost ---------------------------------------
        self.total_cost = _r2(self.quantity * self.price_per_unit)

        super().save(*args, **kwargs)

    # ----------------------------- helpers ----------------------------------
    raw_remaining = property(
        lambda s: _r2(
            s.quantity
            - (s.batches.aggregate(q=Sum("input_quantity"))["q"] or Decimal(0))
        )
    )
    processed_quantity = property(
        lambda s: _r2(s.quantity - s.raw_remaining)
    )
    status = property(
        lambda s: (
            "Unprocessed"   if s.raw_remaining == s.quantity else
            "Processed"     if s.raw_remaining == 0          else
            "Part-processed"
        )
    )

    def __str__(self):
        return f"{self.product} – {self.bags_count} bag(s) on {self.date:%d %b %Y}"



# ════════════════════════════════════════════════════════════════════════════
# 3.  Processing (finished goods & batches)
# ════════════════════════════════════════════════════════════════════════════
# ─── Processed inventory  (fixes for legacy mixins) ─────────────────────────
class ProcessedProduct(TimeStampedModel):
    name           = models.CharField(max_length=80, unique=True)
    source_product = models.ForeignKey(SeasonalProduct, on_delete=models.PROTECT,
                                       related_name="outputs")
    unit = models.CharField(max_length=20, default="kg")

    class Meta:
        ordering = ["name"]

    # modern property names
    produced      = property(lambda s: s.batches.aggregate(
                                q=Sum("output_quantity"))["q"] or Decimal(0))
    consumed      = property(lambda s: s.daily_consumptions.aggregate(
                                q=Sum("quantity_used"))["q"] or Decimal(0))
    stock_on_hand = property(lambda s: (s.produced - s.consumed).quantize(DEC2))
    remaining_raw = property(lambda s: s.source_product.stock_raw)

    # ── compatibility aliases for old mixins / templates ---------------
    total_produced = property(lambda s: s.produced)
    total_consumed = property(lambda s: s.consumed)
    total_balance  = property(lambda s: s.stock_on_hand)   # if ever referenced

    def __str__(self) -> str:
        return self.name


# expenditures/models.py  –  Patch for ProcessingBatch
# ----------------------------------------------------
class ProcessingBatch(TimeStampedModel):
    # ── relations ────────────────────────────────────────────────
    source_purchase   = models.ForeignKey(
        SeasonalPurchase,
        on_delete=models.PROTECT,
        related_name="batches",
    )
    processed_product = models.ForeignKey(
        ProcessedProduct,
        on_delete=models.PROTECT,
        related_name="batches",
    )

    # ── quantities & cost ────────────────────────────────────────
    input_quantity  = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(D2)],
        help_text="Kg (raw) fed into the mill / press",
    )
    output_quantity = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(D2)],
        help_text="Kg/L produced",
    )
    processing_fee  = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=0, validators=[MinValueValidator(0)],
        help_text="TZS spent on milling / pressing",
    )
    date = models.DateField(default=timezone.now)

    # ── meta ─────────────────────────────────────────────────────
    class Meta:
        ordering    = ["-date"]
        indexes     = [models.Index(fields=["processed_product", "date"])]
        constraints = [
            models.CheckConstraint(
                check=Q(output_quantity__lte=F("input_quantity")),
                name="output_le_input",
            )
        ]

    # ── clean() guards ───────────────────────────────────────────
    def clean(self):
        raw_left = self.source_purchase.raw_remaining
        if self.input_quantity > raw_left:
            raise ValidationError({
                "input_quantity":
                    f"Only {raw_left} {self.source_purchase.product.unit} left in purchase"
            })
        if self.output_quantity > self.input_quantity:
            raise ValidationError(
                {"output_quantity": "Cannot exceed input quantity"}
            )

    # ── helpers ──────────────────────────────────────────────────
    @property
    def yield_pct(self) -> Decimal:
        """% yield, rounded to 0.1 % (safe when input == 0)."""
        if self.input_quantity == 0:
            return Decimal("0")
        return (self.output_quantity / self.input_quantity * Decimal(100)).quantize(D1)

    def __str__(self) -> str:            # ← fixed: use self, not “s”
        return f"Batch {self.pk} – {self.processed_product.name}"


# ════════════════════════════════════════════════════════════════════════════
# 4.  Kitchen inventory (purchases & usage)
# ════════════════════════════════════════════════════════════════════════════
class DailyConsumption(TimeStampedModel):
    """
    One line per product per calendar-day.
    """
    product       = models.ForeignKey(
        ProcessedProduct, on_delete=models.PROTECT,
        related_name="daily_consumptions"
    )
    quantity_used = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(D2)],
        help_text="How much of the processed item was eaten / used."
    )
    date          = models.DateField(default=timezone.now)
    recorded_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    remarks       = models.TextField(blank=True)

    class Meta:
        ordering        = ["-date"]
        unique_together = ("product", "date")
        indexes         = [models.Index(fields=["product", "date"])]

    # ─── global guards ------------------------------------------------------
    def clean(self):
        super().clean()
        if self.quantity_used <= 0:
            raise ValidationError({"quantity_used": "Quantity must be > 0."})
        if self.quantity_used > self.product.stock_on_hand:
            raise ValidationError(
                {"quantity_used": "Not enough stock in store"}
            )

    # ─── small helpers ------------------------------------------------------
    def __str__(self):
        return (f"{self.product.name} – "
                f"{self.quantity_used}{self.product.unit} on {self.date}")

    # — stats shortcuts (used by new views) —
    @staticmethod
    def last_30d():
        today   = timezone.localdate()
        thirty  = today - timedelta(days=29)
        return (
            DailyConsumption.objects
            .filter(date__gte=thirty, date__lte=today)
        )


class KitchenProduct(TimeStampedModel):
    UNIT_CHOICES = [
        ("kg",  "Kilogram"), ("g",  "Gram"), ("l",   "Litre"),
        ("pcs", "Pieces"),   ("bag","Bag"),
    ]

    name = models.CharField(max_length=80, unique=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="kg")

    class Meta: ordering = ["name"]

    purchased      = property(
        lambda s: s.purchases.aggregate(q=Sum("quantity"))["q"] or Decimal(0)
    )
    used           = property(
        lambda s: s.usages.aggregate(q=Sum("quantity_used"))["q"] or Decimal(0)
    )
    stock_on_hand  = property(lambda s: (s.purchased - s.used).quantize(DEC2))

    def __str__(self) -> str: return self.name


class KitchenPurchase(TimeStampedModel):
    budget  = models.ForeignKey(Budget, on_delete=models.PROTECT,
                                related_name="kitchen_purchases")
    product = models.ForeignKey(KitchenProduct, on_delete=models.PROTECT,
                                related_name="purchases")
    quantity       = models.DecimalField(max_digits=14, decimal_places=2,
                                         validators=[MinValueValidator(D2)])
    price_per_unit = models.DecimalField(max_digits=14, decimal_places=2,
                                         validators=[MinValueValidator(D2)])
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["-date"]
        indexes  = [models.Index(fields=["product", "date"])]

    def clean(self):
        super().clean()
        if self.pk is None and self.total_cost > self.budget.remaining:
            raise ValidationError({
                "budget": (
                    f"Insufficient funds in “{self.budget.name}”. "
                    f"Remaining {self.budget.remaining:,.2f} TSh."
                )
            })

    total_cost = property(lambda s: (s.quantity * s.price_per_unit).quantize(DEC2))

    def __str__(self) -> str:
        return f"{self.product} – {s.quantity}{self.product.unit}"


class KitchenUsage(TimeStampedModel):
    product       = models.ForeignKey(KitchenProduct, on_delete=models.PROTECT,
                                      related_name="usages")
    quantity_used = models.DecimalField(max_digits=14, decimal_places=2,
                                        validators=[MinValueValidator(D2)])
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering        = ["-date"]
        unique_together = ("product", "date")
        indexes         = [models.Index(fields=["product", "date"])]

    def clean(self):
        if self.quantity_used > self.product.stock_on_hand:
            raise ValidationError("Not enough stock in store")

    def __str__(self) -> str:
        return f"{self.product.name} – {self.quantity_used}{self.product.unit}"
