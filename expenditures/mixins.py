from __future__ import annotations
from decimal import Decimal
from typing import Final

from django.contrib import messages

from .models import SeasonalProduct, ProcessedProduct


class SuccessMessageMixin:
    """Adds a Bootstrap success flash after a valid form save."""
    success_message: str | None = None

    def form_valid(self, form):         # type: ignore[override]
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


class LowStockMixin:
    """
    Calculates low-stock items on every request and drops a yellow alert
    if *any* raw or processed product falls below its reorder threshold.
    """
    LOW_BASE:  Final = Decimal("50")
    LOW_PERC:  Final = Decimal("0.10")

    def _compute_low_stock(self) -> None:
        self.low_raw, self.low_processed = [], []

        for p in SeasonalProduct.objects.all():
            threshold = max(self.LOW_BASE, p.total_purchased * self.LOW_PERC)
            if p.stock_raw <= threshold:
                self.low_raw.append(p)

        for pp in ProcessedProduct.objects.all():
            threshold = max(self.LOW_BASE, pp.total_produced * self.LOW_PERC)
            if pp.stock_on_hand <= threshold:
                self.low_processed.append(pp)

        if self.low_raw or self.low_processed:
            messages.warning(
                self.request,
                "⚠️  Stock alert: some items are below the reorder level."
            )

    # hook into CBV lifecycle
    def dispatch(self, *args, **kwargs):            # type: ignore[override]
        self._compute_low_stock()
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):           # type: ignore[override]
        ctx = super().get_context_data(**kwargs)
        ctx["low_raw"]       = getattr(self, "low_raw", [])
        ctx["low_processed"] = getattr(self, "low_processed", [])
        return ctx

@property
def total_produced(self) -> Decimal:
    """Backward-compat alias required by LowStockMixin."""
    return self.produced


