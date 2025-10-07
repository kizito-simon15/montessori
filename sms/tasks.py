from celery import shared_task
from .beem_service import get_delivery_report
from .models import SentSMS
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_sms_delivery_status():
    sms_messages = SentSMS.objects.filter(status='Pending')  # or another logic to select messages
    for sms in sms_messages:
        response = get_delivery_report(sms.dest_addr, sms.request_id)
        if response and 'status' in response:
            sms.status = response['status']
            sms.save()
        else:
            logger.error(f"Failed to update status for SMS ID {sms.id}")

