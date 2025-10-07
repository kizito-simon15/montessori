from __future__ import annotations

import base64
import calendar
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.base import ContentFile
from django.db.models import Count, Sum, Value, DecimalField, F, ExpressionWrapper, functions as db_fn
from django.db.models.functions import ExtractMonth, Coalesce
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import HttpResponseRedirect, get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView, TemplateView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from apps.finance.models import Invoice, InvoiceItem, Receipt
from apps.result.models import Result
from apps.staffs.models import Staff
from apps.students.models import Student
from expenditures.models import SeasonalProduct, ProcessedProduct, Expenditure, SeasonalPurchase, KitchenPurchase
from library.models import Book, IssuedBook, Stationery
from location.models import SchoolLocation
from parents.models import ParentComments, StudentComments, InvoiceComments
from school_properties.models import Property

from .forms import (
    AcademicSessionForm,
    AcademicTermForm,
    ExamTypeForm,
    InstallmentForm,
    CurrentSessionForm,
    SiteConfigForm,
    StudentClassForm,
    SubjectForm,
    SignatureForm,
)
from .models import (
    AcademicSession,
    AcademicTerm,
    ExamType,
    SiteConfig,
    StudentClass,
    Subject,
    Installment,
    Signature,
    # NEW:
    ProjectAlbum,
    ProjectPhoto,
)

# ──────────────────────────────────────────────────────────────────────────────
# Decimal helpers
# ──────────────────────────────────────────────────────────────────────────────

DECIMAL = DecimalField(max_digits=16, decimal_places=2)
ZERO_D = Value(Decimal("0"), output_field=DECIMAL)
DEC2 = Decimal("0.01")
DEC_ZERO = Value(Decimal("0"), output_field=DECIMAL)


def _r2(x) -> Decimal:
    """Bankers-round → 2-dp Decimal (handles None)."""
    return Decimal(x or 0).quantize(DEC2, ROUND_HALF_UP)


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard / Index
# ──────────────────────────────────────────────────────────────────────────────

class ManagementHomeView(TemplateView):
    template_name = "corecode/management_home.html"


class IndexView(LoginRequiredMixin, TemplateView):
    """Modern landing dashboard."""
    template_name = "index.html"

    # ───────────── helper: month buckets ─────────────
    @staticmethod
    def _monthly(model, date_field: str, year: int) -> list[int]:
        base = [0] * 12
        rows = (
            model.objects
            .filter(**{f"{date_field}__year": year})
            .annotate(m=ExtractMonth(date_field))
            .values("m")
            .annotate(c=Count("id"))
        )
        for r in rows:
            base[r["m"] - 1] = r["c"]
        return base

    # ───────────── page context ─────────────────────
    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)

        # core counts
        students = Student.objects.count()
        staff = Staff.objects.count()
        books = Book.objects.count()

        session = AcademicSession.objects.filter(current=True).first()
        installment = Installment.objects.filter(current=True).first()
        invoices_qs = (
            Invoice.objects.filter(session=session, installment=installment)
            if session and installment else Invoice.objects.none()
        )
        invoices = invoices_qs.count()

        ctx["summary_cards"] = [
            {"label": "Students", "count": students},
            {"label": "Staff", "count": staff},
            {"label": "Books", "count": books},
            {"label": "Invoices", "count": invoices},
        ]

        # charts
        year = timezone.localdate().year
        months = [calendar.month_abbr[i] for i in range(1, 13)]

        ctx.update(
            bar_labels=json.dumps(months),
            bar_vals_students=json.dumps(self._monthly(Student, "date_of_admission", year)),
            bar_vals_staff=json.dumps(self._monthly(Staff, "date_of_admission", year)),
            bar_vals_invoices=json.dumps(self._monthly(Invoice, "created_at", year)),
            line_labels=json.dumps(months),
            line_vals=json.dumps(self._monthly(Student, "date_of_admission", year)),
            pie_labels=json.dumps(["Students", "Staff", "Invoices", "Books"]),
            pie_vals=json.dumps([students, staff, invoices, books]),
        )

        # finance summary
        EXP_COST = ExpressionWrapper(
            F("price_per_unit") * Coalesce(F("quantity"), Value(1)),
            output_field=DECIMAL,
        )
        revenue = Receipt.objects.aggregate(s=Coalesce(Sum("amount_paid"), DEC_ZERO))["s"]
        expenses = Expenditure.objects.aggregate(s=Coalesce(Sum(EXP_COST), DEC_ZERO))["s"]
        ctx.update(
            total_revenue=_r2(revenue),
            total_expenses=_r2(expenses),
            net_balance=_r2(revenue - expenses),
        )

        # low stock
        base, pct = Decimal("50"), Decimal("0.10")
        ctx["low_raw"] = [
            p for p in SeasonalProduct.objects.all()
            if p.stock_raw <= max(base, p.total_purchased * pct)
        ]
        ctx["low_processed"] = [
            pp for pp in ProcessedProduct.objects.all()
            if pp.stock_on_hand <= max(base, pp.total_produced * pct)
        ]

        # misc
        ctx["announcements"] = []
        site = SiteConfig.objects.first()
        ctx["school_name"] = getattr(site, "name", None) or "Victory School"

        return ctx


# ──────────────────────────────────────────────────────────────────────────────
# Site Config CRUD
# ──────────────────────────────────────────────────────────────────────────────

class SiteConfigView(LoginRequiredMixin, View):
    form_class = SiteConfigForm
    template_name = "corecode/siteconfig.html"

    def get(self, request, *args, **kwargs):
        formset = self.form_class(queryset=SiteConfig.objects.all())
        context = {"formset": formset}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        formset = self.form_class(request.POST)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Configurations successfully updated")
        context = {"formset": formset, "title": "Configuration"}
        return render(request, self.template_name, context)


# ──────────────────────────────────────────────────────────────────────────────
# Academic session / term / examtype / installment / class / subject CRUD
# (unchanged except for tidy imports)
# ──────────────────────────────────────────────────────────────────────────────

class SessionListView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ListView):
    model = AcademicSession
    template_name = "corecode/session_list.html"
    permission_required = "corecode.view_academicsession"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AcademicSessionForm()
        return context


class SessionCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = AcademicSession
    form_class = AcademicSessionForm
    template_name = "corecode/mgt_form.html"
    success_url = reverse_lazy("sessions")
    success_message = "New session successfully added"
    permission_required = "corecode.add_academicsession"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add new session"
        return context


class SessionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AcademicSession
    form_class = AcademicSessionForm
    success_url = reverse_lazy("sessions")
    success_message = "Session successfully updated. Students have been promoted to the next class if applicable."
    template_name = "corecode/mgt_form.html"
    permission_required = "corecode.change_academicsession"

    def form_valid(self, form):
        obj = self.object
        if not obj.current:
            terms = AcademicSession.objects.filter(current=True).exclude(name=obj.name).exists()
            if not terms:
                messages.warning(self.request, "You must set a session to current.")
                return redirect("session-list")
        if form.cleaned_data["current"]:
            messages.info(self.request, "Setting this session as current will promote active students to the next class.")
        return super().form_valid(form)


class SessionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AcademicSession
    success_url = reverse_lazy("sessions")
    template_name = "corecode/core_confirm_delete.html"
    success_message = "The session {} has been deleted with all its attached content"
    permission_required = "corecode.delete_academicsession"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.current is True:
            messages.warning(request, "Cannot delete session as it is set to current")
            return redirect("sessions")
        messages.success(self.request, self.success_message.format(obj.name))
        return super().delete(request, *args, **kwargs)


class TermListView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ListView):
    model = AcademicTerm
    template_name = "corecode/term_list.html"
    permission_required = "corecode.view_academicterm"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AcademicTermForm()
        return context


class TermCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = AcademicTerm
    form_class = AcademicTermForm
    template_name = "corecode/mgt_form.html"
    success_url = reverse_lazy("terms")
    success_message = "New term successfully added"
    permission_required = "corecode.add_academicterm"


class TermUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AcademicTerm
    form_class = AcademicTermForm
    success_url = reverse_lazy("terms")
    success_message = "Term successfully updated."
    template_name = "corecode/mgt_form.html"
    permission_required = "corecode.change_academicterm"

    def form_valid(self, form):
        obj = self.object
        if obj.current is False:
            terms = AcademicTerm.objects.filter(current=True).exclude(name=obj.name).exists()
            if not terms:
                messages.warning(self.request, "You must set a term to current.")
                return redirect("term")
        return super().form_valid(form)


class TermDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AcademicTerm
    success_url = reverse_lazy("terms")
    template_name = "corecode/core_confirm_delete.html"
    success_message = "The term {} has been deleted with all its attached content"
    permission_required = "corecode.delete_academicterm"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.current is True:
            messages.warning(request, "Cannot delete term as it is set to current")
            return redirect("terms")
        messages.success(self.request, self.success_message.format(obj.name))
        return super().delete(request, *args, **kwargs)


class ExamListView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ListView):
    model = ExamType
    template_name = "corecode/exam_list.html"
    permission_required = "corecode.view_examtype"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ExamTypeForm()
        return context


class ExamCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = ExamType
    form_class = ExamTypeForm
    template_name = "corecode/mgt_form.html"
    success_url = reverse_lazy("exams")
    success_message = "New exam type successfully added"
    permission_required = "corecode.add_examtype"


class ExamUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ExamType
    form_class = ExamTypeForm
    success_url = reverse_lazy("exams")
    success_message = "Exam type successfully updated."
    template_name = "corecode/mgt_form.html"
    permission_required = "corecode.change_examtype"

    def form_valid(self, form):
        obj = self.object
        if obj.current is False:
            exams = ExamType.objects.filter(current=True).exclude(name=obj.name).exists()
            if not exams:
                messages.warning(self.request, "You must set an exam type to current.")
                return redirect("exam")
        return super().form_valid(form)


class ExamDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ExamType
    success_url = reverse_lazy("exams")
    template_name = "corecode/core_confirm_delete.html"
    success_message = "The exam type {} has been deleted with all its attached content"
    permission_required = "corecode.delete_examtype"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.current is True:
            messages.warning(request, "Cannot delete exam type as it is set to current")
            return redirect("exams")
        messages.success(self.request, self.success_message.format(obj.name))
        return super().delete(request, *args, **kwargs)


class InstallListView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ListView):
    model = Installment
    template_name = "corecode/install_list.html"
    permission_required = "corecode.view_installment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = InstallmentForm()
        return context


class InstallCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Installment
    form_class = InstallmentForm
    template_name = "corecode/mgt_form.html"
    success_url = reverse_lazy("installs")
    success_message = "New installment successfully added"
    permission_required = "corecode.add_installment"


class InstallUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Installment
    form_class = InstallmentForm
    success_url = reverse_lazy("installs")
    success_message = "Installment successfully updated."
    template_name = "corecode/mgt_form.html"
    permission_required = "corecode.change_installment"

    def form_valid(self, form):
        obj = self.object
        if obj.current is False:
            installs = Installment.objects.filter(current=True).exclude(name=obj.name).exists()
            if not installs:
                messages.warning(self.request, "You must set an installment to current.")
                return redirect("installs")
        return super().form_valid(form)


class InstallDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Installment
    success_url = reverse_lazy("installs")
    template_name = "corecode/core_confirm_delete.html"
    success_message = "The installment {} has been deleted with all its attached content"
    permission_required = "corecode.delete_installment"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message.format(obj.name))
        return super().delete(request, *args, **kwargs)


class ClassListView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ListView):
    model = StudentClass
    template_name = "corecode/class_list.html"
    permission_required = "corecode.view_studentclass"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = StudentClassForm()
        return context


class ClassCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = StudentClass
    form_class = StudentClassForm
    template_name = "corecode/mgt_form.html"
    success_url = reverse_lazy("classes")
    success_message = "New class successfully added"
    permission_required = "corecode.add_studentclass"


class ClassUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = StudentClass
    fields = ["name"]
    success_url = reverse_lazy("classes")
    success_message = "class successfully updated."
    template_name = "corecode/mgt_form.html"
    permission_required = "corecode.change_studentclass"


class ClassDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = StudentClass
    success_url = reverse_lazy("classes")
    template_name = "corecode/core_confirm_delete.html"
    success_message = "The class {} has been deleted with all its attached content"
    permission_required = "corecode.delete_studentclass"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message.format(obj.name))
        return super().delete(request, *args, **kwargs)


class SubjectListView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, ListView):
    model = Subject
    template_name = "corecode/subject_list.html"
    permission_required = "corecode.view_subject"
    context_object_name = "subjects"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = SubjectForm()
        return context


class SubjectCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = "corecode/mgt_form.html"
    success_url = reverse_lazy("subjects")
    success_message = "New subject successfully added"
    permission_required = "corecode.add_subject"


class SubjectUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Subject
    fields = ["name"]
    success_url = reverse_lazy("subjects")
    success_message = "Subject successfully updated."
    template_name = "corecode/mgt_form.html"
    permission_required = "corecode.change_subject"


class SubjectDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Subject
    success_url = reverse_lazy("subjects")
    template_name = "corecode/core_confirm_delete.html"
    success_message = "The subject {} has been deleted with all its attached content"
    permission_required = "corecode.delete_subject"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message.format(obj.name))
        return super().delete(request, *args, **kwargs)


class CurrentSessionAndTermAndExamTypeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    form_class = CurrentSessionForm
    template_name = "corecode/current_session.html"

    def get(self, request, *args, **kwargs):
        form = self.form_class(
            initial={
                "current_session": AcademicSession.objects.get(current=True),
                "current_term": AcademicTerm.objects.get(current=True),
                "current_exam": ExamType.objects.get(current=True),
            }
        )
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(
            request.POST,
            initial={
                "current_session": AcademicSession.objects.get(current=True),
                "current_term": AcademicTerm.objects.get(current=True),
                "current_exam": ExamType.objects.get(current=True),
            }
        )
        if form.is_valid():
            session = form.cleaned_data["current_session"]
            term = form.cleaned_data["current_term"]
            exam = form.cleaned_data["current_exam"]
            AcademicSession.objects.filter(name=session).update(current=True)
            AcademicSession.objects.exclude(name=session).update(current=False)
            AcademicTerm.objects.filter(name=term).update(current=True)
            ExamType.objects.filter(name=exam).update(current=True)
        return render(request, self.template_name, {"form": form})


# ──────────────────────────────────────────────────────────────────────────────
# Signature CRUD
# ──────────────────────────────────────────────────────────────────────────────

def create_signature(request):
    if request.method == "POST":
        form = SignatureForm(request.POST)
        if form.is_valid():
            signature = form.save(commit=False)
            signature_data = request.POST.get("signature_data")
            fmt, imgstr = signature_data.split(";base64,")
            ext = fmt.split("/")[-1]
            signature_image = ContentFile(base64.b64decode(imgstr), name=f"{signature.name}_signature.{ext}")
            signature.signature_image = signature_image
            signature.save()
            return redirect("signature_list")
    else:
        form = SignatureForm()
    return render(request, "corecode/create_signature.html", {"form": form})


def signature_list(request):
    signatures = Signature.objects.all()
    return render(request, "corecode/signature_list.html", {"signatures": signatures})


def delete_signature(request, pk):
    signature = get_object_or_404(Signature, pk=pk)
    if request.method == "POST":
        signature.delete()
        messages.success(request, "Signature deleted successfully.")
        return redirect("signature_list")
    return render(request, "corecode/delete_signature.html", {"signature": signature})


# ──────────────────────────────────────────────────────────────────────────────
# NEW: Project uploads backend for "Future Plans → Project Updates"
# ──────────────────────────────────────────────────────────────────────────────

def _get_or_create_default_album() -> ProjectAlbum:
    album = ProjectAlbum.objects.filter(is_active=True).first()
    if album:
        return album
    # create a default album once
    return ProjectAlbum.objects.create(
        title="New Campus",
        slug="new-campus",
        description="Default album for future plans project uploads.",
        is_active=True,
    )


@require_POST
def project_upload(request):
    """
    Save uploaded images to ProjectPhoto and return JSON:
    {
      "ok": true,
      "photos": [{"id": 1, "url": "...", "caption": ""}, ...]
    }
    """
    files = request.FILES.getlist("photos")
    if not files:
        return HttpResponseBadRequest("No files provided.")

    album = _get_or_create_default_album()
    created = []

    for f in files:
        # Basic guard: images only
        if not (f.content_type or "").startswith("image/"):
            continue

        photo = ProjectPhoto.objects.create(
            album=album,
            image=f,
            caption=(f.name[:120] if f.name else ""),
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        created.append(
            {
                "id": photo.id,
                "url": photo.image.url,
                "caption": photo.caption or "",
                "created_at": photo.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )

    return JsonResponse({"ok": True, "photos": created})
