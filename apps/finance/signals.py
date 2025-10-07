# apps/finance/signals.py
from __future__ import annotations

import logging
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch          import receiver
from django.utils             import timezone

from .models import Invoice, Receipt

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# 1.  Invoice-creation hook
#    • closes older invoices for the same session
#    • (re)computes carry-forward on the *new* invoice
# ════════════════════════════════════════════════════════════════════════
@receiver(post_save, sender=Invoice)
def after_creating_invoice(
    sender, instance: Invoice, created: bool, **kwargs
) -> None:
    """Fire once, right after an invoice is first saved."""
    if not created:
        return

    now = timezone.now()
    st  = instance.student
    sess = instance.session
    inst = instance.installment

    logger.info(
        "Invoice %s created for %s / %s / %s at %s",
        instance.pk, st, sess, inst, now,
    )

    # ─── close *earlier* invoices within the same session ─────────────
    previous_qs = (
        Invoice.objects
        .filter(student=st, session=sess, installment__id__lt=inst.id)
        .order_by("installment__id")
    )
    for prev in previous_qs:
        # mark paid-off invoices as closed
        if prev.overall_balance() <= 0:
            prev.status = "closed"
            prev.save(update_fields=["status"])
            logger.debug("Marked invoice %s as closed", prev.pk)

    # ─── ensure brand-new invoice carries the correct forward balance ──
    # save() already sets this, but in case business rules evolve we
    # recompute and persist once more.
    cf = instance._outstanding_before()
    if instance.balance_from_previous_install != cf:
        instance.balance_from_previous_install = cf
        instance.save(update_fields=["balance_from_previous_install"])
        logger.debug(
            "Invoice %s carry-forward adjusted to %s", instance.pk, cf
        )


# ════════════════════════════════════════════════════════════════════════
# 2.  Receipt-creation hook
#    • updates current invoice’s status / balance
#    • pushes any over-payment into the *next* invoice
# ════════════════════════════════════════════════════════════════════════
@receiver(post_save, sender=Receipt)
def update_balances_after_receipt(
    sender, instance: Receipt, created: bool, **kwargs
) -> None:
    """Whenever a receipt is posted, refresh invoice balances."""
    if not created:
        return

    now      = timezone.now()
    invoice  = instance.invoice
    paid_amt = instance.amount_paid

    logger.info(
        "Receipt %s (%s TZS) posted for invoice %s at %s",
        instance.pk, paid_amt, invoice.pk, now
    )

    # ─── 1. Re-evaluate the invoice just paid ──────────────────────────
    if invoice.overall_balance() <= 0:
        invoice.status = "closed"
    invoice.save(update_fields=["status"])

    # ─── 2. If there’s *over-payment*, push it to the first later invoice
    overpay: Decimal = -invoice.overall_balance()  # positive if over-paid
    if overpay <= 0:
        return  # nothing to cascade

    logger.debug("Over-payment detected: %s TZS", overpay)

    later_invoices = (
        Invoice.objects
        .filter(student=invoice.student,
                session=invoice.session,
                installment__id__gt=invoice.installment.id)
        .order_by("installment__id")
    )
    for nxt in later_invoices:
        # apply only to the very next invoice
        nxt.balance_from_previous_install += overpay
        nxt.save(update_fields=["balance_from_previous_install"])
        logger.debug(
            "Added %s TZS carry-forward to invoice %s",
            overpay, nxt.pk
        )
        break  # stop after first subsequent invoice
