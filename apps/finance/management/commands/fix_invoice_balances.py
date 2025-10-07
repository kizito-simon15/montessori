from django.core.management.base import BaseCommand
from apps.finance.models import Invoice
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Recalculates balance_from_previous_install for all invoices'

    def handle(self, *args, **kwargs):
        invoices = Invoice.objects.all().order_by('session__id', 'student__id', 'installment__id')
        total_updated = 0
        for invoice in invoices:
            previous_balance = invoice.get_previous_balance()
            if invoice.balance_from_previous_install != previous_balance:
                invoice.balance_from_previous_install = previous_balance
                invoice.save(skip_balance_update=True)
                total_updated += 1
                logger.info(f"Updated invoice {invoice.id} for student {invoice.student} with balance {previous_balance}")
        self.stdout.write(self.style.SUCCESS(f"Updated {total_updated} invoices"))
