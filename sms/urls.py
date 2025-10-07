from django.urls import path
from .views import (
    SendSMSFormView, CheckBalanceView,
    SMSHistoryView,
    DeleteSMSView
)

urlpatterns = [
    path('send-sms-form/', SendSMSFormView.as_view(), name='send_sms_form'),
    path('check-balance/', CheckBalanceView.as_view(), name='check_balance'),
    path('sms-history/', SMSHistoryView.as_view(), name='sms_history'),
    path('delete-sms/', DeleteSMSView.as_view(), name='delete_sms'),
    # Other URL patterns
]

