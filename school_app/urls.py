# school_app/urls.py — updated
"""Main URL configuration.

- Public landing page -> accounts.views.index
- Auth-protected dashboard -> apps.corecode.views.IndexView
- Includes every app's urls (as in your project)
- Serves MEDIA in development
- Loads Django Debug Toolbar only when DEBUG=True and installed
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import include, path, reverse

# Landing + dashboard
from accounts.views import index
from apps.corecode.views import IndexView


def admin_redirect(request):
    """Redirect /goto-admin/ to the actual admin index."""
    return redirect(reverse("admin:index"))


urlpatterns = [
    # Public home page
    path("", index, name="index"),

    # Auth-protected dashboard
    path("home/", login_required(IndexView.as_view()), name="home-index"),

    # Admin
    path("admin/", admin.site.urls),
    path("goto-admin/", admin_redirect, name="goto-admin"),

    # Core app (also contains project_upload endpoint)
    path("", include("apps.corecode.urls")),

    # Auth / Accounts
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),

    # Domain apps
    path("student/", include("apps.students.urls")),
    path("staff/", include("apps.staffs.urls")),
    path("finance/", include("apps.finance.urls")),
    path("expenditures/", include("expenditures.urls")),
    path("event/", include("event.urls")),
    path("result/", include("apps.result.urls")),
    path("updations/", include("updations.urls")),
    path("school_properties/", include("school_properties.urls")),
    path("library/", include("library.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("bursor/", include("bursor.urls")),
    path("teachers/", include("teachers.urls")),
    path("sms/", include("sms.urls")),
    path("headteacher/", include("headteacher.urls")),
    path("location/", include("location.urls")),
    path("duty/", include("duty.urls")),
    path("meetings/", include("meetings.urls")),
    path("alevel_students/", include("alevel_students.urls")),
    path("alevel_results/", include("alevel_results.urls")),
]

# Development helpers
if settings.DEBUG:
    # Serve MEDIA files in dev
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Enable Django Debug Toolbar only if installed
    try:
        import debug_toolbar  # noqa: F401
        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except Exception:
        pass
