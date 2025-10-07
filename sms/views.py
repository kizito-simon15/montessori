# apps/sms/views.py  – July 2025 overhaul
"""SMS module views – guardian/staff blast, history, balance.
Compatible with Student.guardian{1,2}_mobile_number and Staff.mobile_number.
"""
from __future__ import annotations

from typing import List, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import Window, F
from django.db.models.functions import RowNumber
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from apps.corecode.models import StudentClass
from apps.students.models import Student
from apps.staffs.models import Staff

from .beem_service import send_sms, check_balance
from .models import SentSMS

# ════════════════════════════════════════════════════════════════
# Helper utilities
# ════════════════════════════════════════════════════════════════
def _tz(num: str) -> str:
    """Return number in +255XXXXXXXXX format (empty string if invalid)."""
    if num.startswith("+255"):
        return num
    digits = "".join(filter(str.isdigit, num))[-9:]
    return "+255" + digits if digits else ""


def _collect_guardian_numbers(stu: Student) -> List[Dict]:
    recs: list[dict] = []
    for num in (stu.guardian1_mobile_number, stu.guardian2_mobile_number):
        num = _tz(num or "")
        if num:
            recs.append(
                {
                    "dest_addr": num,
                    "first_name": stu.firstname,
                    "last_name": stu.surname,
                }
            )
    return recs


def _collect_staff_numbers(qs) -> List[Dict]:
    uniq: dict[str, dict] = {}
    for s in qs:
        num = _tz(s.mobile_number or "")
        if num:
            uniq[num] = {
                "dest_addr": num,
                "first_name": s.firstname,
                "last_name": s.surname,
            }
    return list(uniq.values())


# ════════════════════════════════════════════════════════════════
# 1  Send SMS
# ════════════════════════════════════════════════════════════════
class SendSMSFormView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "sms.send_sms"
    template_name = "sms/send_sms.html"

    def get(self, request):
        students = Student.objects.filter(current_status="active", completed=False)
        staff_qs = Staff.objects.filter(current_status="active")
        classes = StudentClass.objects.all()
        return render(
            request,
            self.template_name,
            {"students": students, "staff": staff_qs, "classes": classes},
        )

    def post(self, request):
        message = (request.POST.get("message") or "").strip()
        recipient_type = request.POST.get("recipient_type")  # students | staff
        recipients: List[Dict] = []

        # students
        if recipient_type == "students":
            class_id = request.POST.get("class_id")
            if class_id:
                for stu in Student.objects.filter(
                    current_status="active", completed=False, current_class_id=class_id
                ):
                    recipients.extend(_collect_guardian_numbers(stu))
            for sid in request.POST.getlist("student_recipients"):
                stu = get_object_or_404(Student, id=sid)
                recipients.extend(_collect_guardian_numbers(stu))

        # staff
        elif recipient_type == "staff":
            staff_ids = request.POST.getlist("staff_recipients")
            staff_qs = Staff.objects.filter(id__in=staff_ids, current_status="active")
            recipients = _collect_staff_numbers(staff_qs)

        # validation
        if not message:
            messages.error(request, "Message body cannot be empty.")
            return redirect("send_sms_form")
        if not recipients:
            messages.error(request, "No valid recipients selected.")
            return redirect("send_sms_form")

        recipients = list({r["dest_addr"]: r for r in recipients}.values())  # dedupe

        # send
        try:
            resp = send_sms(message, recipients)
            if resp.get("error") or not resp.get("successful"):
                msg = resp.get("error", resp.get("message", "Unknown error"))
                messages.error(request, f"Failed to send SMS: {msg}")
            else:
                messages.success(request, f"SMS sent to {len(recipients)} recipient(s).")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Unexpected error: {exc}")

        return redirect("send_sms_form")


# ════════════════════════════════════════════════════════════════
# 2  History  (works on all DBs)
# ════════════════════════════════════════════════════════════════

class SMSHistoryView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "sms.view_sms_history"
    template_name = "sms/sms_history.html"

    def get(self, request):
        qs = (
            SentSMS.objects.filter(status__iexact="Sent")
            .annotate(
                rn=Window(
                    RowNumber(),
                    partition_by=[F("dest_addr"), F("message")],
                    order_by=[F("sent_date").desc()],
                )
            )
            .filter(rn=1)
            .order_by("-sent_date")
        )

        ctx = {
            "messages": qs,
            "total_sms": qs.count(),
            "total_sent": qs.filter(status__iexact="Sent").count(),
            "total_failed": qs.exclude(status__iexact="Sent").count(),
            "unique_recipients": qs.values("dest_addr").distinct().count(),
        }
        return render(request, self.template_name, ctx)

# ════════════════════════════════════════════════════════════════
# 3  Balance
# ════════════════════════════════════════════════════════════════
class CheckBalanceView(LoginRequiredMixin, View):
    template_name = "sms/check_balance.html"

    def get(self, request):
        resp = check_balance()
        ctx = (
            {"error": resp.get("error")}
            if "error" in resp
            else {"balance": resp.get("data", {}).get("credit_balance", "N/A")}
        )
        return render(request, self.template_name, ctx)


# ════════════════════════════════════════════════════════════════
# 4  Bulk Delete
# ════════════════════════════════════════════════════════════════
@method_decorator(require_POST, name="dispatch")
class DeleteSMSView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "sms.delete_sent_sms"

    def post(self, request):
        ids = request.POST.getlist("sms_ids")
        if ids:
            with transaction.atomic():
                deleted, _ = SentSMS.objects.filter(id__in=ids).delete()
                messages.success(request, f"Deleted {deleted} messages.")
        else:
            messages.error(request, "No messages selected.")
        return redirect("sms_history")
