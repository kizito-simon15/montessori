# meetings/views.py
from django.shortcuts import render, redirect
from django.forms import inlineformset_factory
from .models import Meeting, Agenda
from .forms import MeetingForm
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.http import JsonResponse
from .models import Meeting, Participant, Notification
from accounts.models import CustomUser
from .forms import MeetingForm  # A form for creating meetings

# meetings/views.py

from django.shortcuts import render, redirect
from .models import Meeting, Agenda
from .forms import MeetingForm, AgendaForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def create_meeting(request):
    print("Entering create_meeting view")

    if request.method == 'POST':
        print("Processing POST request")

        # Process Meeting Form
        meeting_form = MeetingForm(request.POST)
        
        # Process each Agenda entry manually
        agenda_forms = []
        agenda_data = zip(
            request.POST.getlist('agenda_description'),
            request.POST.getlist('agenda_start_time'),
            request.POST.getlist('agenda_end_time')
        )

        # Create AgendaForm instances for validation
        for desc, start, end in agenda_data:
            agenda_forms.append(AgendaForm({'description': desc, 'start_time': start, 'end_time': end}))

        # Validate the MeetingForm and each AgendaForm
        if meeting_form.is_valid() and all(form.is_valid() for form in agenda_forms):
            # Save the meeting instance
            meeting = meeting_form.save(commit=False)
            meeting.host = request.user
            meeting.save()
            print("Meeting saved with ID:", meeting.id)

            # Save each agenda associated with the meeting
            for agenda_form in agenda_forms:
                agenda = agenda_form.save(commit=False)
                agenda.meeting = meeting
                agenda.save()
                print("Agenda saved with ID:", agenda.id)

            messages.success(request, "Meeting created successfully with multiple agendas.")
            return redirect('meeting_list')
        else:
            print("Validation errors found")
            print("Meeting Form Errors:", meeting_form.errors)
            for i, form in enumerate(agenda_forms):
                if not form.is_valid():
                    print(f"Agenda Form {i+1} Errors:", form.errors)
            messages.error(request, "Error creating meeting. Please check the form entries.")

    else:
        print("Rendering form for GET request")
        meeting_form = MeetingForm()
        agenda_forms = [AgendaForm()]  # Start with one empty agenda form

    return render(request, 'meetings/create_meeting.html', {
        'meeting_form': meeting_form,
        'agenda_forms': agenda_forms,
    })



@login_required
def notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    data = [{'message': n.message, 'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')} for n in notifications]
    return JsonResponse(data, safe=False)

# meetings/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Meeting
from django.utils import timezone

@login_required
def meeting_list(request):
    """
    Display a list of meetings relevant to the logged-in user.
    """
    user = request.user

    # Fetch meetings based on new fields (is_active and is_past)
    upcoming_meetings = Meeting.objects.filter(is_active=False, is_past=False)
    ongoing_meetings = Meeting.objects.filter(is_active=True, is_past=False)
    past_meetings = Meeting.objects.filter(is_active=False, is_past=True)

    # Filter meetings where the user is a participant or host
    user_upcoming_meetings = upcoming_meetings.filter(participants__user=user) | upcoming_meetings.filter(host=user)
    user_ongoing_meetings = ongoing_meetings.filter(participants__user=user) | ongoing_meetings.filter(host=user)
    user_past_meetings = past_meetings.filter(participants__user=user) | past_meetings.filter(host=user)

    # Render the list of meetings in the template
    context = {
        'user_upcoming_meetings': user_upcoming_meetings.distinct(),
        'user_ongoing_meetings': user_ongoing_meetings.distinct(),
        'user_past_meetings': user_past_meetings.distinct(),
    }
    return render(request, 'meetings/meeting_list.html', context)

from django.shortcuts import render, get_object_or_404
from .models import Meeting, Agenda, Participant
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('meetings.view_meeting', raise_exception=True)
def meeting_detail(request, meeting_id):
    print("Entering meeting_detail view")

    # Retrieve the meeting by ID
    meeting = get_object_or_404(Meeting, id=meeting_id)
    print(f"Meeting found: ID={meeting.id}, Title={meeting.title}")

    # Retrieve all agendas associated with this meeting
    agendas = meeting.agendas.all()
    print(f"Total agendas for this meeting: {agendas.count()}")

    # Retrieve all participants invited to this meeting
    participants = meeting.participants.select_related('user').all()
    print(f"Total participants invited: {participants.count()}")

    # Render the meeting details in the template
    context = {
        'meeting': meeting,
        'agendas': agendas,
        'participants': participants,
    }
    return render(request, 'meetings/meeting_detail.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from accounts.models import CustomUser
from .models import Meeting, Participant, Notification
from apps.students.models import Student
from apps.staffs.models import Staff

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from accounts.models import CustomUser
from .models import Meeting, Participant, Notification
from apps.students.models import Student
from apps.staffs.models import Staff

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from .models import Meeting, Participant, Notification, Agenda
from accounts.models import ParentUser, TeacherUser, BursorUser, SecretaryUser, AcademicUser
from django.utils.timezone import localtime

@login_required
@permission_required('meetings.change_meeting', raise_exception=True)
def invite_participants(request, meeting_id):
    print("Entering invite_participants view")

    meeting = get_object_or_404(Meeting, id=meeting_id)
    print(f"Meeting found: ID={meeting.id}, Title={meeting.title}")

    if request.method == 'POST':
        print("Processing POST request")
        
        user_ids = request.POST.getlist('selected_users')
        print(f"Selected user IDs received: {user_ids}")

        invited_users = []
        invalid_user_ids = []

        for user_id in user_ids:
            user = None
            try:
                print(f"Attempting to retrieve user with ID {user_id} across different user types.")

                # Retrieve user from the specific user type models
                if ParentUser.objects.filter(id=user_id).exists():
                    user = ParentUser.objects.get(id=user_id)
                elif TeacherUser.objects.filter(id=user_id).exists():
                    user = TeacherUser.objects.get(id=user_id)
                elif BursorUser.objects.filter(id=user_id).exists():
                    user = BursorUser.objects.get(id=user_id)
                elif SecretaryUser.objects.filter(id=user_id).exists():
                    user = SecretaryUser.objects.get(id=user_id)
                elif AcademicUser.objects.filter(id=user_id).exists():
                    user = AcademicUser.objects.get(id=user_id)

                if user:
                    Participant.objects.create(user=user, meeting=meeting, is_admin_invited=True)
                    print(f"Participant created for user: {user.username}")

                    # Prepare a detailed notification message
                    agenda_details = "\n".join(
                        f"{agenda.description} - {localtime(agenda.start_time).strftime('%Y-%m-%d %H:%M')} to {localtime(agenda.end_time).strftime('%H:%M')}"
                        for agenda in meeting.agendas.all()
                    )
                    participants_list = ", ".join(
                        [p.user.username for p in meeting.participants.all()] + [meeting.host.username]
                    )
                    notification_message = (
                        f"Hello {user.username},\n\n"
                        f"You are invited to join the meeting '{meeting.title}' scheduled on {localtime(meeting.start_time).strftime('%Y-%m-%d %H:%M')}.\n\n"
                        f"**Agendas:**\n{agenda_details}\n\n"
                        f"**Participants:** {participants_list}\n\n"
                        f"Host: {meeting.host.username}\n"
                    )

                    # Send notification to the user
                    Notification.objects.create(
                        user=user,
                        meeting=meeting,
                        message=notification_message
                    )
                    print(f"Notification created for user: {user.username} with message: {notification_message}")
                    invited_users.append(user.username)
                else:
                    print(f"User with ID {user_id} does not exist in any user category.")
                    invalid_user_ids.append(user_id)

            except Exception as e:
                print(f"Error processing user with ID {user_id}: {str(e)}")
                invalid_user_ids.append(user_id)

        print("Final list of invited users:", invited_users)
        if invalid_user_ids:
            messages.warning(request, f"Some users could not be found: {', '.join(map(str, invalid_user_ids))}")

        messages.success(request, "Participants invited successfully.")
        return redirect('meeting_detail', meeting_id=meeting_id)

    # Load specific user types for display in the template
    parents = ParentUser.objects.all()
    teachers = TeacherUser.objects.all()
    bursors = BursorUser.objects.all()
    secretaries = SecretaryUser.objects.all()
    academics = AcademicUser.objects.all()

    return render(request, 'meetings/invite_participants.html', {
        'meeting': meeting,
        'parents': parents,
        'teachers': teachers,
        'bursors': bursors,
        'secretaries': secretaries,
        'academics': academics,
    })

# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import Meeting, Participant, Notification

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from .models import Meeting, Participant, Notification

@login_required
@permission_required('meetings.change_meeting', raise_exception=True)
def set_meeting_as_active(request, meeting_id):
    print("Entering set_meeting_as_active view")

    # Retrieve the specified meeting
    meeting = get_object_or_404(Meeting, id=meeting_id)
    print(f"Meeting found: ID={meeting.id}, Title={meeting.title}")

    # Check if the meeting is already active or past
    if meeting.is_active:
        messages.warning(request, "This meeting is already active.")
        return redirect('meeting_detail', meeting_id=meeting_id)
    elif meeting.end_time < timezone.now():
        messages.error(request, "Cannot activate a meeting that has already ended.")
        return redirect('meeting_detail', meeting_id=meeting_id)

    # Set the meeting as active and ensure a unique meeting URL is generated once
    meeting.is_active = True
    if not meeting.meeting_url:  # Only generate if it doesn't exist
        meeting.meeting_url = f"https://meet.jit.si/{meeting.title}-{meeting.id}"
    meeting.save()
    print(f"Meeting set to active: {meeting.title}, URL: {meeting.meeting_url}")

    # Notify all participants with the meeting link and details
    participants = Participant.objects.filter(meeting=meeting)

    for participant in participants:
        # Build the detailed notification message
        notification_message = (
            f"Hello {participant.user.username},\n\n"
            f"The meeting '{meeting.title}' is now active and ongoing. You are invited to participate.\n\n"
            f"**Join the Meeting Here:** [Join Meeting]({meeting.meeting_url})\n\n"
            f"Meeting Details:\n"
            f"Start Time: {meeting.start_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"End Time: {meeting.end_time.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"**Agendas:**\n" +
            "\n".join(f"{agenda.description} - {agenda.start_time.strftime('%H:%M')} to {agenda.end_time.strftime('%H:%M')}"
                      for agenda in meeting.agendas.all())
        )

        # Create and send the notification
        Notification.objects.create(
            user=participant.user,
            meeting=meeting,
            message=notification_message,
            created_at=timezone.now()
        )
        print(f"Notification sent to participant: {participant.user.username}")

    # Redirect host to the unique meeting URL
    messages.success(request, f"The meeting '{meeting.title}' has been set as active and notifications sent.")
    return redirect(meeting.meeting_url)

from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404, render

from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from django.utils.crypto import get_random_string
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

@login_required
def join_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, is_active=True)
    participant, created = Participant.objects.get_or_create(user=request.user, meeting=meeting)

    room_name = f"{meeting.title}-{meeting.id}"  # Consistent room name per meeting

    # Determine the base template based on user type
    if hasattr(request.user, 'parentuser'):
        base_template = 'parents/parent_base.html'
    elif hasattr(request.user, 'bursoruser'):
        base_template = 'bursor/bursor_base.html'
    elif hasattr(request.user, 'academicuser'):
        base_template = 'academic/academic_base.html'
    else:
        base_template = 'base.html'

    # Set this participant as active in the meeting
    participant.has_audio = True
    participant.has_video = True
    participant.save()

    # Retrieve active and absent participants
    active_participants = meeting.participants.filter(has_audio=True, has_video=True)
    absent_participants = meeting.participants.exclude(id__in=active_participants)

    return render(request, 'meetings/meeting_room.html', {
        'meeting': meeting,
        'participant': participant,
        'room_name': room_name,
        'base_template': base_template,
        'active_participants': active_participants,
        'absent_participants': absent_participants,
    })

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Meeting, Participant, Notification

@login_required
def parent_meetings(request):
    parent_user = request.user
    
    # Retrieve meetings where the parent is invited
    invited_meetings = Meeting.objects.filter(participants__user=parent_user).prefetch_related('agendas', 'participants__user')
    
    # Retrieve notifications for the parent related to these meetings
    notifications = Notification.objects.filter(user=parent_user, meeting__in=invited_meetings)

    return render(request, 'meetings/parent_meetings.html', {
        'invited_meetings': invited_meetings,
        'notifications': notifications,
    })

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string
from .models import Meeting, Participant

@login_required
def parent_meeting_room(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, is_active=True)
    participant, created = Participant.objects.get_or_create(user=request.user, meeting=meeting)
    room_name = f"{meeting.title}-{meeting.id}-{get_random_string(8)}"

    # Ensure the participant is marked as actively participating
    participant.has_audio = True
    participant.has_video = True
    participant.save()

    # Retrieve all participants for display, marking absent ones
    participants = meeting.participants.all()

    return render(request, 'meetings/parent_meeting_room.html', {
        'meeting': meeting,
        'participant': participant,
        'room_name': room_name,
        'participants': participants,
    })

# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.contrib import messages
from .models import Meeting, Agenda, Participant, Notification
from .forms import EditMeetingForm, EditAgendaFormSet, EditParticipantFormSet, EditNotificationFormSet

@login_required
@permission_required('meetings.change_meeting', raise_exception=True)
@transaction.atomic
def update_meeting_details(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    meeting_url = meeting.meeting_url

    if request.method == 'POST':
        meeting_form = EditMeetingForm(request.POST, instance=meeting)
        agenda_formset = EditAgendaFormSet(request.POST, instance=meeting)
        participant_formset = EditParticipantFormSet(request.POST, instance=meeting)
        notification_formset = EditNotificationFormSet(request.POST, instance=meeting)

        if meeting_form.is_valid() and agenda_formset.is_valid() and participant_formset.is_valid() and notification_formset.is_valid():
            meeting_form.save()
            agenda_formset.save()
            participant_formset.save()
            notification_formset.save()
            messages.success(request, 'Meeting and related details updated successfully.')
            return redirect('meeting_detail', meeting_id=meeting.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        meeting_form = EditMeetingForm(instance=meeting)
        agenda_formset = EditAgendaFormSet(instance=meeting)
        participant_formset = EditParticipantFormSet(instance=meeting)
        notification_formset = EditNotificationFormSet(instance=meeting)

    context = {
        'meeting_form': meeting_form,
        'agenda_formset': agenda_formset,
        'participant_formset': participant_formset,
        'notification_formset': notification_formset,
        'meeting_url': meeting_url,
    }
    return render(request, 'meetings/update_meeting_details.html', context)

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from .models import Meeting, Participant, Agenda, Notification

@login_required
@permission_required('meetings.delete_meeting', raise_exception=True)
def delete_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)

    # Delete associated participants, agendas, and notifications
    Participant.objects.filter(meeting=meeting).delete()
    Agenda.objects.filter(meeting=meeting).delete()
    Notification.objects.filter(meeting=meeting).delete()

    # Delete the meeting itself
    meeting.delete()

    messages.success(request, "Meeting and all associated details have been deleted successfully.")
    return redirect('meeting_list')

@login_required
@permission_required('meetings.change_meeting', raise_exception=True)
def set_meeting_as_inactive(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)

    # Check if the meeting is active before setting it to inactive
    if meeting.is_active:
        meeting.is_active = False
        meeting.save()
        messages.success(request, "Meeting has been set to inactive.")
    else:
        messages.info(request, "Meeting is already inactive.")

    return redirect('meeting_detail', meeting_id=meeting_id)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from .models import Meeting, Participant, Notification

@login_required
@permission_required('meetings.change_meeting', raise_exception=True)
def set_meeting_as_past(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)

    # Set the meeting to past if it's inactive and hasn't already been marked as past
    if not meeting.is_active and not meeting.is_past:
        meeting.is_past = True
        meeting.save()
        
        # Send notifications to all participants
        participants = Participant.objects.filter(meeting=meeting)
        notification_message = (
            "The meeting is already done. Thank you for participating if you attended. "
            "If you had not, you are still welcome for future meetings. It’s important to know the information "
            "discussed for the academic betterment of your children."
        )
        
        for participant in participants:
            Notification.objects.create(
                user=participant.user,
                meeting=meeting,
                message=notification_message,
                created_at=timezone.now()
            )
            print(f"Notification sent to participant: {participant.user.username}")

        messages.success(request, "Meeting has been marked as past, and notifications have been sent.")
    else:
        messages.info(request, "Meeting must be inactive before marking it as past.")

    return redirect('meeting_detail', meeting_id=meeting_id)

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Meeting, Participant, Notification

@login_required
def bursor_meetings_list(request):
    bursor_user = request.user

    # Retrieve meetings where the bursar is invited as a participant
    invited_meetings = Meeting.objects.filter(participants__user=bursor_user).prefetch_related('agendas', 'participants__user')
    
    # Retrieve notifications for the bursar related to these meetings
    notifications = Notification.objects.filter(user=bursor_user, meeting__in=invited_meetings)

    return render(request, 'meetings/bursor_meetings_list.html', {
        'invited_meetings': invited_meetings,
        'notifications': notifications,
    })

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Meeting, Participant, Notification

@login_required
def academic_meetings_list(request):
    academic_user = request.user

    # Retrieve meetings where the academic is invited as a participant
    invited_meetings = Meeting.objects.filter(participants__user=academic_user).prefetch_related('agendas', 'participants__user')
    
    # Retrieve notifications for the academic related to these meetings
    notifications = Notification.objects.filter(user=academic_user, meeting__in=invited_meetings)

    return render(request, 'meetings/academic_meetings_list.html', {
        'invited_meetings': invited_meetings,
        'notifications': notifications,
    })

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Meeting, Participant, Notification

@login_required
def teacher_meetings_list(request):
    teacher_user = request.user

    # Retrieve meetings where the teacher is invited as a participant
    invited_meetings = Meeting.objects.filter(participants__user=teacher_user).prefetch_related('agendas', 'participants__user')
    
    # Retrieve notifications for the teacher related to these meetings
    notifications = Notification.objects.filter(user=teacher_user, meeting__in=invited_meetings)

    return render(request, 'meetings/teacher_meetings_list.html', {
        'invited_meetings': invited_meetings,
        'notifications': notifications,
    })

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Meeting, Participant, Notification

@login_required
def secretary_meetings_list(request):
    secretary_user = request.user

    # Retrieve meetings where the secretary is invited as a participant
    invited_meetings = Meeting.objects.filter(participants__user=secretary_user).prefetch_related('agendas', 'participants__user')
    
    # Retrieve notifications for the secretary related to these meetings
    notifications = Notification.objects.filter(user=secretary_user, meeting__in=invited_meetings)

    return render(request, 'meetings/secretary_meetings_list.html', {
        'invited_meetings': invited_meetings,
        'notifications': notifications,
    })
