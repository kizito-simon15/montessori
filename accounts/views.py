import logging
from itertools import chain

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView as DefaultLoginView
from django.db.models import Count, Q, Value, DecimalField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

# Optional geo guards (kept for parity with your earlier code)
from geopy.distance import geodesic

from location.models import SchoolLocation
from apps.staffs.models import Staff
from apps.students.models import Student
from sms.beem_service import send_sms
from sms.models import SentSMS

from .forms import (
    ParentUserCreationForm,
    HeadTeacherUserCreationForm,
    ProfileUpdateForm,
    # ▼ these were referenced but not imported before
    #    (adds missing Create/Update flows for other roles)
    #    If any of these don’t exist yet in forms.py, create them or comment out.
    #    They should mirror Parent/HeadTeacher patterns.
    TeacherUserCreationForm,
    BursorUserCreationForm,
    SecretaryUserCreationForm,
    AcademicUserCreationForm,
)
from .models import (
    ParentUser,
    TeacherUser,
    BursorUser,
    SecretaryUser,
    AcademicUser,
    CustomUser,
    HeadTeacherUser,
    UserProfile,
)

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
# helper – ONE place to send credentials to staff
# ════════════════════════════════════════════════════════════════════
def _send_credentials(
    first_name: str,
    last_name: str | None,
    mobile: str,
    username: str,
    pwd_raw: str,
    role: str,
) -> None:
    """
    Fires a Beem SMS containing freshly-created credentials.
    Any blank / missing mobile silently aborts.
    """
    if not mobile:
        return
    sms = (
        f"Dear {role} {first_name} {last_name or ''}, "
        f"your login details for the Victory Schools system are:\n"
        f"• Username: {username}\n• Password: {pwd_raw}\n"
        "Keep this message safe."
    )
    send_sms(
        sms,
        [
            {
                "dest_addr": mobile,
                "first_name": first_name,
                "last_name": last_name or "",
            }
        ],
    )


class CustomLoginView(DefaultLoginView):
    """
    Centralised login view that:
      • logs the user in
      • (optionally) enforces staff geo/time window
      • redirects to the right dashboard per role
    """
    form_class = AuthenticationForm
    template_name = "registration/login.html"

    def form_valid(self, form):
        user = form.get_user()
        auth_login(self.request, user)
        logger.debug("User %s logged in", user.username)

        # ── Optional: geo/time guard for staff roles ───────────────────
        staff_roles = (
            hasattr(user, "teacheruser")
            or hasattr(user, "bursoruser")
            or hasattr(user, "secretaryuser")
            or hasattr(user, "academicuser")
            or hasattr(user, "headteacheruser")
        )
        if staff_roles:
            school_location = SchoolLocation.objects.filter(is_active=True).first()
            if school_location:
                # Example guard (disabled by default):
                #   distance_km = geodesic(
                #       (school_location.latitude, school_location.longitude),
                #       (user_last_known_lat, user_last_known_lng)
                #   ).km
                #   allowed_radius_km = 50
                #   if distance_km > allowed_radius_km:
                #       messages.warning(self.request, "Login blocked: out of allowed area.")
                #       return redirect("custom_login")
                pass

        return self.redirect_user(user)

    def redirect_user(self, user):
        """Send each account type to its dashboard."""
        if user.is_superuser:
            return redirect("home-index")
        if hasattr(user, "parentuser"):
            return redirect("parent_dashboard")
        if hasattr(user, "teacheruser"):
            return redirect("teacher_dashboard")
        if hasattr(user, "headteacheruser"):
            return redirect("headteacher_dashboard")
        if hasattr(user, "bursoruser"):
            return redirect("bursor_dashboard")
        if hasattr(user, "secretaryuser"):
            return redirect("secretary_dashboard")
        if hasattr(user, "academicuser"):
            return redirect("academic_dashboard")
        # default fallback
        return redirect("home-index")


# ────────────────────────────────────────────────────────────────────
# Simple dashboards
# ────────────────────────────────────────────────────────────────────

@login_required
def superuser_dashboard(request):
    return render(request, "accounts/superuser_dashboard.html")


@login_required
def parent_dashboard(request):
    return render(request, "parent_dashboard.html")


# ────────────────────────────────────────────────────────────────────
# Parent CRUD
# ────────────────────────────────────────────────────────────────────

@login_required
def create_parent_user(request):
    if request.method == "POST":
        form = ParentUserCreationForm(request.POST)
        if form.is_valid():
            parent_user = form.save()
            # Send SMS
            student = parent_user.student
            message = (
                f"Habari ndugu mzazi wa {student.firstname} {student.middle_name} {student.surname}, "
                f"pokea taarifa hizi za kukuwezesha kuingia kwenye mfumo wa shule, "
                f"username: {parent_user.username}, password: {request.POST.get('password1')}, "
                "usifute meseji hii kwa msaada piga 0744394080."
            )
            recipients = []
            if getattr(student, "father_mobile_number", ""):
                recipients.append(
                    {
                        "dest_addr": student.father_mobile_number,
                        "first_name": parent_user.parent_first_name,
                        "last_name": parent_user.parent_last_name,
                    }
                )
            if getattr(student, "mother_mobile_number", ""):
                recipients.append(
                    {
                        "dest_addr": student.mother_mobile_number,
                        "first_name": parent_user.parent_first_name,
                        "last_name": parent_user.parent_last_name,
                    }
                )
            try:
                if recipients:
                    send_sms(message, recipients)
                messages.success(
                    request,
                    "Parent user created successfully, and SMS has been sent.",
                )
            except Exception as e:
                messages.error(
                    request, f"Parent user created, but SMS sending failed: {e}"
                )
            return redirect("list_users")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ParentUserCreationForm()
    return render(request, "accounts/create_parent_user.html", {"form": form})


@login_required
def parent_user_list(request):
    parent_users = ParentUser.objects.all()
    return render(request, "accounts/parent_user_list.html", {"parent_users": parent_users})


@login_required
def update_parent_user(request, pk):
    user = get_object_or_404(ParentUser, pk=pk)
    if request.method == "POST":
        form = ParentUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            # Send SMS
            student = user.student
            message = (
                f"Habari ndugu mzazi wa {student.firstname} {student.surname}, "
                "pokea maboresho ya taarifa za kuingia kwenye mfumo wa shule, "
                f"username: {user.username}, password: {request.POST.get('password1')}, "
                "usifute meseji hii kwa msaada piga 0762023662."
            )
            recipients = []
            if getattr(student, "father_mobile_number", ""):
                recipients.append(
                    {
                        "dest_addr": student.father_mobile_number,
                        "first_name": user.parent_first_name,
                        "last_name": user.parent_last_name,
                    }
                )
            if getattr(student, "mother_mobile_number", ""):
                recipients.append(
                    {
                        "dest_addr": student.mother_mobile_number,
                        "first_name": user.parent_first_name,
                        "last_name": user.parent_last_name,
                    }
                )
            try:
                if recipients:
                    send_sms(message, recipients)
                messages.success(
                    request, "Parent user updated successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Parent user updated, but SMS sending failed: {e}"
                )
            return redirect("list_users")
    else:
        form = ParentUserCreationForm(instance=user)
    return render(
        request, "accounts/update_user.html", {"form": form, "user_type": "Parent"}
    )


@login_required
def delete_parent_user(request, pk):
    user = get_object_or_404(ParentUser, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "Parent user deleted successfully.")
        return redirect("parent_user_list")
    return render(request, "accounts/delete_parent_user.html", {"user": user})


# ────────────────────────────────────────────────────────────────────
# Role selection screen
# ────────────────────────────────────────────────────────────────────

@login_required
def select_user_type(request):
    return render(request, "accounts/select_user_type.html")


# ────────────────────────────────────────────────────────────────────
# Teacher / Bursor / Secretary / HeadTeacher / Academic CRUD
# (Create + Update + Delete + Toggle)
# ────────────────────────────────────────────────────────────────────

@login_required
def create_teacher_user(request):
    if request.method == "POST":
        form = TeacherUserCreationForm(request.POST)
        if form.is_valid():
            teacher_user = form.save()
            staff = teacher_user.staff
            message = (
                f"Hello {staff.firstname} {staff.middle_name} {staff.surname}, "
                f"receive the informations to enter the school management system, "
                f"username: {teacher_user.username}, password: {request.POST.get('password1')}, "
                "don't delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request, "Teacher user created successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Teacher user created, but SMS sending failed: {e}"
                )
            return redirect("select_user_type")
    else:
        form = TeacherUserCreationForm()
    return render(
        request, "accounts/create_user.html", {"form": form, "user_type": "Teacher"}
    )


@login_required
def create_bursor_user(request):
    if request.method == "POST":
        form = BursorUserCreationForm(request.POST)
        if form.is_valid():
            bursor_user = form.save()
            staff = bursor_user.staff
            message = (
                f"Hello bursor, {staff.firstname} {staff.middle_name} {staff.surname}, "
                f"receive the informations to enter the school management system, "
                f"username: {bursor_user.username}, password: {request.POST.get('password1')}, "
                "don't delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request, "Bursor user created successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Bursor user created, but SMS sending failed: {e}"
                )
            return redirect("select_user_type")
    else:
        form = BursorUserCreationForm()
    return render(
        request, "accounts/create_user.html", {"form": form, "user_type": "Bursor"}
    )


@login_required
def create_secretary_user(request):
    if request.method == "POST":
        form = SecretaryUserCreationForm(request.POST)
        if form.is_valid():
            secretary_user = form.save()
            staff = secretary_user.staff
            message = (
                f"Hello secretary, {staff.firstname} {staff.middle_name} {staff.surname}, "
                f"receive the informations to enter the school management system, "
                f"username: {secretary_user.username}, password: {request.POST.get('password1')}, "
                "dont delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request,
                    "Secretary user created successfully, and SMS has been sent.",
                )
            except Exception as e:
                messages.error(
                    request, f"Secretary user created, but SMS sending failed: {e}"
                )
            return redirect("select_user_type")
    else:
        form = SecretaryUserCreationForm()
    return render(
        request, "accounts/create_user.html", {"form": form, "user_type": "Secretary"}
    )


@login_required
def create_headteacher_user(request):
    """
    Creates a Head-Teacher account and texts the selected staff member
    their username + raw password using the central `_send_credentials` helper.
    Assigns necessary permissions for headteacher role.
    """
    if request.method == "POST":
        form = HeadTeacherUserCreationForm(request.POST)
        if form.is_valid():
            ht_user = form.save()  # saves + returns HeadTeacherUser
            staff = ht_user.staff  # FK to apps.staffs.models.Staff
            custom_user = ht_user.user  # linked CustomUser instance

            # Assign some example permissions (adjust to your project)
            from django.contrib.auth.models import Permission
            from django.contrib.contenttypes.models import ContentType
            from apps.students.models import Student

            content_type = ContentType.objects.get_for_model(Student)
            perms = ["view_student", "add_student", "change_student", "delete_student"]
            for codename in perms:
                try:
                    permission = Permission.objects.get(
                        codename=codename, content_type=content_type
                    )
                    custom_user.user_permissions.add(permission)
                except Permission.DoesNotExist:
                    logger.warning("Permission %s missing; skipped", codename)

            _send_credentials(
                first_name=staff.firstname,
                last_name=staff.surname,
                mobile=staff.mobile_number,
                username=custom_user.username,
                pwd_raw=request.POST.get("password1"),
                role="Head-Teacher",
            )
            messages.success(
                request, "Head-Teacher user created, permissions assigned, and SMS sent."
            )
            return redirect("select_user_type")
    else:
        form = HeadTeacherUserCreationForm()
    return render(
        request, "accounts/create_user.html", {"form": form, "user_type": "Head-Teacher"}
    )


@login_required
def update_headteacher_user(request, pk):
    user = get_object_or_404(HeadTeacherUser, pk=pk)
    if request.method == "POST":
        form = HeadTeacherUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Head-Teacher user updated.")
            return redirect("list_users")
    else:
        form = HeadTeacherUserCreationForm(instance=user)
    return render(
        request, "accounts/update_user.html", {"form": form, "user_type": "Head-Teacher"}
    )


@login_required
def delete_headteacher_user(request, pk):
    user = get_object_or_404(HeadTeacherUser, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "Head-Teacher user deleted.")
        return redirect("list_users")
    return render(
        request, "accounts/delete_user.html", {"user": user, "user_type": "Head-Teacher"}
    )


@login_required
def toggle_headteacher_status(request, user_id):
    user = get_object_or_404(HeadTeacherUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_all_headteachers_status(request):
    """
    Flip the `is_active` flag for ALL head-teacher accounts at once.
    If every account is currently active → deactivate all, else activate all.
    """
    headteachers = HeadTeacherUser.objects.all()
    all_active = all(ht.is_active for ht in headteachers)
    for ht in headteachers:
        ht.is_active = not all_active
        ht.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def create_academic_user(request):
    if request.method == "POST":
        form = AcademicUserCreationForm(request.POST)
        if form.is_valid():
            academic_user = form.save()
            staff = academic_user.staff
            message = (
                f"Hello academic, {staff.firstname} {staff.middle_name} {staff.surname}, "
                f"receive the informations to enter the school management system, "
                f"username: {academic_user.username}, password: {request.POST.get('password1')}, "
                "don't delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request, "Academic user created successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Academic user created, but SMS sending failed: {e}"
                )
            return redirect("select_user_type")
    else:
        form = AcademicUserCreationForm()
    return render(
        request, "accounts/create_user.html", {"form": form, "user_type": "Academic"}
    )


# ────────────────────────────────────────────────────────────────────
# Aggregated list + toggles
# ────────────────────────────────────────────────────────────────────

@login_required
def list_users(request):
    qs_map = {
        "Parents": ParentUser.objects.all(),
        "Teachers": TeacherUser.objects.all(),
        "Head-Teachers": HeadTeacherUser.objects.all(),
        "Bursors": BursorUser.objects.all(),
        "Secretaries": SecretaryUser.objects.all(),
        "Academics": AcademicUser.objects.all(),
    }
    cfg = {
        "Parents": dict(
            gradA="#10b981cc",
            gradB="#34d399cc",
            filter1=("Student", 1),
            filter2=("Class", 2),
            toggle_all="toggle_all_parents_status",
            update="update_parent_user",
            delete="delete_parent_user",
            toggle="toggle_parent_status",
        ),
        "Teachers": dict(
            gradA="#3b82f6cc",
            gradB="#60a5facc",
            filter1=("Name", 1),
            toggle_all="toggle_all_teachers_status",
            update="update_teacher_user",
            delete="delete_teacher_user",
            toggle="toggle_teacher_status",
        ),
        "Head-Teachers": dict(
            gradA="#06b6d4cc",
            gradB="#0284c7cc",
            filter1=("Name", 1),
            toggle_all="toggle_all_headteachers_status",
            update="update_headteacher_user",
            delete="delete_headteacher_user",
            toggle="toggle_headteacher_status",
        ),
        "Bursors": dict(
            gradA="#f97316cc",
            gradB="#fdba74cc",
            filter1=("Name", 1),
            toggle_all="toggle_all_bursors_status",
            update="update_bursor_user",
            delete="delete_bursor_user",
            toggle="toggle_bursor_status",
        ),
        "Secretaries": dict(
            gradA="#8b5cf6cc",
            gradB="#c084facc",
            filter1=("Name", 1),
            toggle_all="toggle_all_secretaries_status",
            update="update_secretary_user",
            delete="delete_secretary_user",
            toggle="toggle_secretary_status",
        ),
        "Academics": dict(
            gradA="#ef4444cc",
            gradB="#f87171cc",
            filter1=("Name", 1),
            toggle_all="toggle_all_academics_status",
            update="update_academic_user",
            delete="delete_academic_user",
            toggle="toggle_academic_status",
        ),
    }
    sections = [
        {
            "label": label,
            "users": qs,
            **cfg[label],
        }
        for label, qs in qs_map.items()
        if qs.exists()
    ]
    focus = request.GET.get("account_type", "").replace("-", " ").title()
    if focus and focus in qs_map:
        sections = [s for s in sections if s["label"].lower() == focus.lower()]
    return render(
        request,
        "accounts/list_users.html",
        {"sections": sections, "overall_total": sum(s["users"].count() for s in sections)},
    )


# Updates
@login_required
def update_teacher_user(request, pk):
    user = get_object_or_404(TeacherUser, pk=pk)
    if request.method == "POST":
        form = TeacherUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            staff = user.staff
            message = (
                f"Hello {staff.firstname} {staff.middle_name} {staff.surname}, "
                "receive the updates of entering the school management system, "
                f"username: {user.username}, password: {request.POST.get('password1')}, "
                "dont delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request, "Teacher user updated successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Teacher user updated, but SMS sending failed: {e}"
                )
            return redirect("list_users")
    else:
        form = TeacherUserCreationForm(instance=user)
    return render(
        request, "accounts/update_user.html", {"form": form, "user_type": "Teacher"}
    )


@login_required
def update_bursor_user(request, pk):
    user = get_object_or_404(BursorUser, pk=pk)
    if request.method == "POST":
        form = BursorUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            staff = user.staff
            message = (
                f"Hello bursor, {staff.firstname} {staff.middle_name} {staff.surname}, "
                "receive the updates of entering the school management system, "
                f"username: {user.username}, password: {request.POST.get('password1')}, "
                "dont delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request, "Bursor user updated successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Bursor user updated, but SMS sending failed: {e}"
                )
            return redirect("list_users")
    else:
        form = BursorUserCreationForm(instance=user)
    return render(
        request, "accounts/update_user.html", {"form": form, "user_type": "Bursor"}
    )


@login_required
def update_secretary_user(request, pk):
    user = get_object_or_404(SecretaryUser, pk=pk)
    if request.method == "POST":
        form = SecretaryUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            staff = user.staff
            message = (
                f"Hello secretary, {staff.firstname} {staff.middle_name} {staff.surname}, "
                "receive the updates of entering the school management system, "
                f"username: {user.username}, password: {request.POST.get('password1')}, "
                "dont delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request, "Secretary user updated successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Secretary user updated, but SMS sending failed: {e}"
                )
            return redirect("list_users")
    else:
        form = SecretaryUserCreationForm(instance=user)
    return render(
        request, "accounts/update_user.html", {"form": form, "user_type": "Secretary"}
    )


@login_required
def update_academic_user(request, pk):
    user = get_object_or_404(AcademicUser, pk=pk)
    if request.method == "POST":
        form = AcademicUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            staff = user.staff
            message = (
                f"Hello academic, {staff.firstname} {staff.middle_name} {staff.surname}, "
                "receive the updates of entering the school management system, "
                f"username: {user.username}, password: {request.POST.get('password1')}, "
                "dont delete this message, for help call 0744394080."
            )
            recipients = [
                {
                    "dest_addr": staff.mobile_number,
                    "first_name": staff.firstname,
                    "last_name": staff.surname,
                }
            ]
            try:
                send_sms(message, recipients)
                messages.success(
                    request, "Academic user updated successfully, and SMS has been sent."
                )
            except Exception as e:
                messages.error(
                    request, f"Academic user updated, but SMS sending failed: {e}"
                )
            return redirect("list_users")
    else:
        form = AcademicUserCreationForm(instance=user)
    return render(
        request, "accounts/update_user.html", {"form": form, "user_type": "Academic"}
    )


# Deletes
@login_required
def delete_teacher_user(request, pk):
    user = get_object_or_404(TeacherUser, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "Teacher user deleted successfully.")
        return redirect("list_users")
    return render(request, "accounts/delete_user.html", {"user": user, "user_type": "Teacher"})


@login_required
def delete_bursor_user(request, pk):
    user = get_object_or_404(BursorUser, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "Bursor user deleted successfully.")
        return redirect("list_users")
    return render(request, "accounts/delete_user.html", {"user": user, "user_type": "Bursor"})


@login_required
def delete_secretary_user(request, pk):
    user = get_object_or_404(SecretaryUser, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "Secretary user deleted successfully.")
        return redirect("list_users")
    return render(request, "accounts/delete_user.html", {"user": user, "user_type": "Secretary"})


@login_required
def delete_academic_user(request, pk):
    user = get_object_or_404(AcademicUser, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "Academic user deleted successfully.")
        return redirect("list_users")
    return render(request, "accounts/delete_user.html", {"user": user, "user_type": "Academic"})


# Toggles
@login_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_all_parents_status(request):
    parents = ParentUser.objects.all()
    current_status = all(parent.is_active for parent in parents)
    for parent in parents:
        parent.is_active = not current_status
        parent.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_parent_status(request, user_id):
    user = get_object_or_404(ParentUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_teacher_status(request, user_id):
    user = get_object_or_404(TeacherUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_bursor_status(request, user_id):
    user = get_object_or_404(BursorUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_secretary_status(request, user_id):
    user = get_object_or_404(SecretaryUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_academic_status(request, user_id):
    user = get_object_or_404(AcademicUser, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_all_teachers_status(request):
    teachers = TeacherUser.objects.all()
    current_status = all(teacher.is_active for teacher in teachers)
    for teacher in teachers:
        teacher.is_active = not current_status
        teacher.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_all_bursors_status(request):
    bursors = BursorUser.objects.all()
    current_status = all(bursor.is_active for bursor in bursors)
    for bursor in bursors:
        bursor.is_active = not current_status
        bursor.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_all_secretaries_status(request):
    secretaries = SecretaryUser.objects.all()
    current_status = all(secretary.is_active for secretary in secretaries)
    for secretary in secretaries:
        secretary.is_active = not current_status
        secretary.save(update_fields=["is_active"])
    return redirect("list_users")


@login_required
def toggle_all_academics_status(request):
    academics = AcademicUser.objects.all()
    current_status = all(academic.is_active for academic in academics)
    for academic in academics:
        academic.is_active = not current_status
        academic.save(update_fields=["is_active"])
    return redirect("list_users")


# ────────────────────────────────────────────────────────────────────
# Public index
# ────────────────────────────────────────────────────────────────────

def index(request):
    """
    View to render the public-facing index page for Victory Primary School.
    """
    slides = [
        {"image": "img/hero1.JPG", "title": "Welcome to Victory", "text": "Empowering Young Minds"},
        {"image": "img/about-victory.JPG", "title": "Holistic Education", "text": "Nurturing Future Leaders"},
        {"image": "img/about-2.JPG", "title": "Modern Facilities", "text": "Learning in a Conducive Environment"},
        {"image": "img/staff/group-staff.JPG", "title": "Dedicated Team", "text": "Guiding with Excellence"},
    ]
    return render(request, "index1.html", {"slides": slides})


# ────────────────────────────────────────────────────────────────────
# Accounts overview dashboard (KPI)
# ────────────────────────────────────────────────────────────────────

@login_required
def accounts_dashboard(request):
    """One-screen KPI overview for every account type."""
    stats = {
        "Parents": ParentUser.objects.aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        ),
        "Teachers": TeacherUser.objects.aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        ),
        "Head-Teachers": HeadTeacherUser.objects.aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        ),
        "Bursors": BursorUser.objects.aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        ),
        "Secretaries": SecretaryUser.objects.aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        ),
        "Academics": AcademicUser.objects.aggregate(
            total=Count("id"), active=Count("id", filter=Q(is_active=True))
        ),
    }
    palette_map = {
        "Parents": "--emerald",
        "Teachers": "--amber",
        "Head-Teachers": "--cyan",
        "Bursors": "--purple",
        "Secretaries": "--rose",
        "Academics": "--indigo",
    }
    rows = [
        {
            "label": label,
            "palette": palette_map.get(label, "--slate"),
            "total": data["total"],
            "active": data["active"],
            "inactive": data["total"] - data["active"],
        }
        for label, data in stats.items()
    ]
    context = {
        "stats": stats,
        "labels": list(stats.keys()),
        "total_series": [d["total"] for d in stats.values()],
        "active_series": [d["active"] for d in stats.values()],
        "inactive_series": [d["total"] - d["active"] for d in stats.values()],
        "total_users": sum(d["total"] for d in stats.values()),
        "rows": rows,  # drives the KPI card grid in the template
    }
    return render(request, "accounts/user_dashboard.html", context)


# ────────────────────────────────────────────────────────────────────
# Profile
# ────────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    """Display the user's profile with options to add or edit."""
    has_profile = hasattr(request.user, "profile")
    context = {
        "user": request.user,
        "has_profile": has_profile,
    }
    return render(request, "accounts/profile_detail.html", context)


@login_required
def profile_add(request):
    """Create a new profile for the user."""
    if hasattr(request.user, "profile"):
        messages.warning(request, "You already have a profile.")
        return redirect("profile")
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Profile created successfully.")
            return redirect("profile")
    else:
        form = ProfileUpdateForm()
    return render(request, "accounts/profile_add.html", {"form": form})


@login_required
def profile_edit(request):
    """Edit the existing user profile."""
    if not hasattr(request.user, "profile"):
        messages.warning(request, "You need to create a profile first.")
        return redirect("profile_add")
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, "accounts/profile_edit.html", {"form": form})
