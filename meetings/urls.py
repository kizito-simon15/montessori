# meetings/urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('create/', views.create_meeting, name='create_meeting'),
    path('invite/<int:meeting_id>/', views.invite_participants, name='invite_participants'),
    path('join/<int:meeting_id>/', views.join_meeting, name='join_meeting'),
    path('parent/meetings/', views.parent_meetings, name='parent_meetings'),
    path('notifications/', views.notifications, name='notifications'),
    path('meetings/', views.meeting_list, name='meeting_list'),
    path('detail/<int:meeting_id>/', views.meeting_detail, name='meeting_detail'),
    path('meetings/<int:meeting_id>/activate/', views.set_meeting_as_active, name='set_meeting_as_active'),
    path('meetings/parent-room/<int:meeting_id>/', views.parent_meeting_room, name='parent_meeting_room'),
    path('<int:meeting_id>/update/', views.update_meeting_details, name='update_meeting'),  # New URL for updating meeting
    path('<int:meeting_id>/set_inactive/', views.set_meeting_as_inactive, name='set_meeting_as_inactive'),  # Set to inactive
    path('<int:meeting_id>/set_past/', views.set_meeting_as_past, name='set_meeting_as_past'),  # Set to past
    path('<int:meeting_id>/delete/', views.delete_meeting, name='delete_meeting'),  # Delete meeting
    path('secretary/meetings/', views.secretary_meetings_list, name='secretary_meetings_list'),
    path('bursor/meetings/', views.bursor_meetings_list, name='bursor_meetings_list'),
    path('academic/meetings/', views.academic_meetings_list, name='academic_meetings_list'),
    path('teacher/meetings/', views.teacher_meetings_list, name='teacher_meetings_list'),
]
