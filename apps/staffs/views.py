"""Staff app – class-based views (June 2025)
––––––––––––––––––––––––––––––––––––––––––––
• shared mixin handles KPI counters + URL filters
• Inactive list now re-uses same helpers (no more _apply_filters / _kpi_context NameErrors)
• uses STAFF_CATEGORIES & DEPARTMENT_CHOICES from new models
"""

from datetime import time
from typing import Dict, Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from .models import Staff, StaffAttendance
from .forms import StaffForm, StaffAttendanceForm


# ───────────────────────────────────
# helpers / mixins
# ───────────────────────────────────
class StaffFilterMixin:
    """Add GET-filtering & KPI counters to any Staff ListView."""

    staff_qs_status: str = "active"          # override in subclasses

    # ---------------- filters ----------------
    def _apply_filters(self, qs):
        """?category=teaching&department=…&helsb=1"""
        get   = self.request.GET
        cat   = get.get("category")
        dept  = get.get("department")
        helsb = get.get("helsb") == "1"

        if cat in dict(Staff.STAFF_CATEGORIES):
            qs = qs.filter(staff_category=cat)
        if dept:
            qs = qs.filter(department=dept)
        if helsb:
            qs = qs.filter(has_helsb=True)
        return qs

    # ---------------- queryset ----------------
    def get_queryset(self):
        qs = Staff.objects.filter(current_status=self.staff_qs_status)
        return self._apply_filters(qs).order_by("surname", "firstname")

    # ---------------- context -----------------
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        base_qs = Staff.objects.filter(current_status=self.staff_qs_status)
        ctx.update(
            # KPI counters
            total_male      = base_qs.filter(gender="male").count(),
            total_female    = base_qs.filter(gender="female").count(),
            overall_total   = base_qs.count(),

            # for <select> filters
            categories      = Staff.STAFF_CATEGORIES,
            departments     = Staff.DEPARTMENT_CHOICES,

            selected_cat    = self.request.GET.get("category", ""),
            selected_dept   = self.request.GET.get("department", ""),
            helsb_filter    = "1" if self.request.GET.get("helsb") == "1" else "",
        )
        return ctx


# ═══════════════════════════ LISTS ════════════════════════════
class StaffListView(LoginRequiredMixin,
                    PermissionRequiredMixin,
                    StaffFilterMixin,
                    ListView):
    """Active employees."""
    model               = Staff
    template_name       = "staffs/staff_list.html"
    context_object_name = "staff_list"
    permission_required = "staffs.view_staff_list"
    permission_denied_message = "Access Denied"


class InactiveStaffListView(LoginRequiredMixin,
                            PermissionRequiredMixin,
                            StaffFilterMixin,
                            ListView):
    """Inactive / resigned employees."""
    staff_qs_status     = "inactive"
    model               = Staff
    template_name       = "staffs/inactive_staff_list.html"
    context_object_name = "staff_list"
    permission_required = "staffs.view_staff_list"
    permission_denied_message = "Access Denied"


# ═══════════════════════════ DETAIL ═══════════════════════════
class StaffDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Modern profile card."""
    model                     = Staff
    template_name             = "staffs/staff_detail.html"
    permission_required       = "staffs.view_staff_detail"
    permission_denied_message = "Access Denied"

    def get_context_data(self, **kwargs):
        staff = self.object
        ctx   = super().get_context_data(**kwargs)

        ctx["bank_details"] = {
            "bank_name":      staff.bank_name,
            "account_number": staff.bank_account_number,
            "branch":         staff.bank_branch,
        }
        ctx["emergency_contact"] = {
            "name":   staff.emergency_contact_name,
            "number": staff.emergency_contact_number,
        }

        # HELSB summary
        if staff.has_helsb:
            pct = staff.helsb_rate          # stored in percent
            amt = staff.salary * staff.helsb_rate_as_decimal
            ctx["helsb_display"] = f"{pct:.0f}% ( {amt:,.0f} TZS )"
        else:
            ctx["helsb_display"] = "None"

        return ctx


# ═════════════════ CREATE / UPDATE ════════════════════════════
class StaffCreateView(LoginRequiredMixin,
                      PermissionRequiredMixin,
                      SuccessMessageMixin,
                      CreateView):
    model             = Staff
    form_class        = StaffForm
    template_name     = "staffs/staff_form.html"
    permission_required = "staffs.add_staff"
    success_message   = "New staff member added."

    def form_valid(self, form):
        staff = form.save(commit=False)
        if self.request.FILES.get("passport_photo"):
            staff.passport_photo = self.request.FILES["passport_photo"]
        staff.save()
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("staff-list")


class StaffUpdateView(LoginRequiredMixin,
                      PermissionRequiredMixin,
                      SuccessMessageMixin,
                      UpdateView):
    model               = Staff
    form_class          = StaffForm
    template_name       = "staffs/staff_form.html"
    permission_required = "staffs.change_staff"
    success_message     = "Record successfully updated."

    def form_valid(self, form):
        staff = form.save(commit=False)
        if self.request.FILES.get("passport_photo"):
            staff.passport_photo = self.request.FILES["passport_photo"]
        staff.save()
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("staff-list")


# ═══════════════════════════ DELETE ════════════════════════════
class StaffDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model                     = Staff
    template_name             = "staffs/staff_confirm_delete.html"
    success_url               = reverse_lazy("staff-list")
    permission_required       = "staffs.delete_staff"
    permission_denied_message = "Access Denied"


# ═══════════════════ Attendance report (function view) ═══════════════════
def staff_attendance_report(request):
    records = (
        StaffAttendance.objects.select_related("user")
        .all()
        .order_by("-date", "time_of_arrival")
    )

    grouped = {}
    for rec in records:
        grouped.setdefault(rec.date, [])
        rec.tick_color = (
            "blue-ticks"
            if rec.time_of_arrival and time(0, 0) <= rec.time_of_arrival < time(7, 30)
            else "red-ticks" if rec.time_of_arrival else None
        )
        grouped[rec.date].append(rec)

    return render(request,
                  "staffs/staff_attendance_report.html",
                  {"grouped_attendance": grouped})
