from django.urls import path

from .views import (
    ClassCreateView,
    ClassDeleteView,
    ClassListView,
    ClassUpdateView,
    CurrentSessionAndTermAndExamTypeView,
    IndexView,
    SessionCreateView,
    SessionDeleteView,
    SessionListView,
    SessionUpdateView,
    SiteConfigView,
    SubjectCreateView,
    SubjectDeleteView,
    SubjectListView,
    SubjectUpdateView,
    TermCreateView,
    TermDeleteView,
    TermListView,
    TermUpdateView,
    ExamCreateView,
    ExamDeleteView,
    ExamListView,
    ExamUpdateView,
    InstallCreateView,
    InstallDeleteView,
    InstallListView,
    InstallUpdateView,
    create_signature,
    signature_list,
    ManagementHomeView
)

from . import views


urlpatterns = [
    path('management/home/', ManagementHomeView.as_view(), name='management_home'),  # Adjust this URL as needed
    path("", IndexView.as_view(), name="index-home"),
    path("site-config", SiteConfigView.as_view(), name="configs"),
    path(
        "current-session/", CurrentSessionAndTermAndExamTypeView.as_view(), name="current-session"
    ),
    path("session/list/", SessionListView.as_view(), name="sessions"),
    path("session/create/", SessionCreateView.as_view(), name="session-create"),
    path(
        "session/<int:pk>/update/",
        SessionUpdateView.as_view(),
        name="session-update",
    ),
    path(
        "session/<int:pk>/delete/",
        SessionDeleteView.as_view(),
        name="session-delete",
    ),
    path("term/list/", TermListView.as_view(), name="terms"),
    path("term/create/", TermCreateView.as_view(), name="term-create"),
    path("term/<int:pk>/update/", TermUpdateView.as_view(), name="term-update"),
    path("term/<int:pk>/delete/", TermDeleteView.as_view(), name="term-delete"),
    path("exam/list/", ExamListView.as_view(), name="exams"),
    path("exam/create/", ExamCreateView.as_view(), name="exam-create"),
    path("exam/<int:pk>/update/", ExamUpdateView.as_view(), name="exam-update"),
    path("exam/<int:pk>/delete/", ExamDeleteView.as_view(), name="exam-delete"),
    path("install/list/", InstallListView.as_view(), name="installs"),
    path("install/create/", InstallCreateView.as_view(), name="install-create"),
    path("install/<int:pk>/update/", InstallUpdateView.as_view(), name="install-update"),
    path("install/<int:pk>/delete/", InstallDeleteView.as_view(), name="install-delete"),
    path("class/list/", ClassListView.as_view(), name="classes"),
    path("class/create/", ClassCreateView.as_view(), name="class-create"),
    path("class/<int:pk>/update/", ClassUpdateView.as_view(), name="class-update"),
    path("class/<int:pk>/delete/", ClassDeleteView.as_view(), name="class-delete"),
    path("subject/list/", SubjectListView.as_view(), name="subjects"),
    path("subject/create/", SubjectCreateView.as_view(), name="subject-create"),
    path('create-signature/', create_signature, name='create_signature'),
    path('signatures/', signature_list, name='signature_list'),
    path('signature/<int:pk>/delete/', views.delete_signature, name='delete_signature'),
    path(
        "subject/<int:pk>/update/",
        SubjectUpdateView.as_view(),
        name="subject-update",
    ),
    path(
        "subject/<int:pk>/delete/",
        SubjectDeleteView.as_view(),
        name="subject-delete",
    ),
]