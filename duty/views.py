from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import StaffRoles

def delete_staff_role(request, role_id):
    # Get the specific staff role or return 404 if not found
    staff_role = get_object_or_404(StaffRoles, id=role_id)

    if request.method == 'POST':
        staff_role.delete()
        messages.success(request, "Staff role deleted successfully.")
        return redirect('staff-role-list')

    return render(request, 'duty/delete_staff_role.html', {
        'staff_role': staff_role,
    })

# apps/duty/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import StaffRolesForm, StaffRolesForming
from .models import StaffRoles
from apps.corecode.models import StudentClass, Subject

def update_staff_role(request, role_id):
    # Get the specific staff role or return 404 if not found
    staff_role = get_object_or_404(StaffRoles, id=role_id)

    if request.method == 'POST':
        form = StaffRolesForming(request.POST, instance=staff_role)
        if form.is_valid():
            form.save()  # Save the updated role
            messages.success(request, "Staff role updated successfully.")
            return redirect('staff-role-list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StaffRolesForming(instance=staff_role)

    return render(request, 'duty/update_staff_role.html', {
        'form': form,
        'staff_role': staff_role,
    })

# apps/duty/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import StaffRoles

def delete_class_teacher(request, role_id):
    # Get the specific staff role or return 404 if not found
    staff_role = get_object_or_404(StaffRoles, id=role_id, is_class_teacher=True)

    if request.method == 'POST':
        staff_role.delete()
        messages.success(request, "Class teacher deleted successfully.")
        return redirect('staff-role-list')

    return render(request, 'duty/delete_class_teacher.html', {
        'staff_role': staff_role,
    })

from django.shortcuts import render
from .models import StaffRoles

def staff_role_list(request):
    # Group staff roles by class
    class_roles = {}
    all_roles = StaffRoles.objects.all()
    
    for role in all_roles:
        class_id = role.assigned_class.id
        if class_id not in class_roles:
            class_roles[class_id] = {
                "class_name": role.assigned_class,
                "roles": []
            }
        class_roles[class_id]["roles"].append(role)
    
    # Filter only class teacher roles
    class_teachers = StaffRoles.objects.filter(is_class_teacher=True)

    # Get the staff currently on duty
    staff_on_duty = StaffRoles.objects.filter(on_duty=True).first()

    return render(request, 'duty/staff_role_list.html', {
        'class_roles': class_roles,
        'class_teachers': class_teachers,
        'staff_on_duty': staff_on_duty,  # Pass the staff on duty to the template
    })

# apps/duty/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import StaffRolesForm
from .models import StaffRoles
from apps.corecode.models import StudentClass, Subject

def assign_staff_role(request):
    if request.method == 'POST':
        form = StaffRolesForm(request.POST)
        if form.is_valid():
            staff = form.cleaned_data['staff']
            is_class_teacher = form.cleaned_data['is_class_teacher']
            class_teacher_class = form.cleaned_data.get('class_teacher_class')

            # Get class-subject pairs from the POST data
            class_ids = request.POST.getlist('class_subject_class[]')
            subject_ids = request.POST.getlist('class_subject_subject[]')

            # Iterate over the class-subject pairs and create StaffRoles entries
            for class_id, subject_id in zip(class_ids, subject_ids):
                try:
                    assigned_class = StudentClass.objects.get(id=class_id)
                    subject = Subject.objects.get(id=subject_id) if subject_id else None

                    # Only create roles with valid subjects unless it's a class teacher entry
                    if subject or (is_class_teacher and assigned_class == class_teacher_class):
                        if not StaffRoles.objects.filter(staff=staff, assigned_class=assigned_class, subject=subject).exists():
                            StaffRoles.objects.create(
                                staff=staff,
                                assigned_class=assigned_class,
                                subject=subject,
                                is_class_teacher=(is_class_teacher and assigned_class == class_teacher_class)
                            )
                        else:
                            messages.warning(request, f"The role for {staff} in {assigned_class} teaching {subject if subject else 'N/A'} already exists.")
                    else:
                        messages.error(request, "A subject is required for non-class teacher roles.")
                        return render(request, 'duty/assign_staff_role.html', {'form': form, 'subjects': Subject.objects.all()})

                except (StudentClass.DoesNotExist, Subject.DoesNotExist):
                    messages.error(request, "Invalid class or subject selection.")
                    return render(request, 'duty/assign_staff_role.html', {'form': form, 'subjects': Subject.objects.all()})

            # Handle class teacher assignment if applicable
            if is_class_teacher and class_teacher_class:
                try:
                    # Ensure only one entry is marked as class teacher for the class
                    StaffRoles.objects.filter(assigned_class=class_teacher_class, is_class_teacher=True).update(is_class_teacher=False)

                    # Check if a class teacher entry already exists
                    if not StaffRoles.objects.filter(staff=staff, assigned_class=class_teacher_class, subject=None, is_class_teacher=True).exists():
                        StaffRoles.objects.create(
                            staff=staff,
                            assigned_class=class_teacher_class,
                            subject=None,  # No specific subject for class teacher role
                            is_class_teacher=True
                        )
                    else:
                        messages.warning(request, f"{staff} is already the class teacher for {class_teacher_class}.")
                        
                except StudentClass.DoesNotExist:
                    messages.error(request, "Invalid class selection for class teacher.")
                    return render(request, 'duty/assign_staff_role.html', {'form': form, 'subjects': Subject.objects.all()})

            messages.success(request, "Staff roles assigned successfully.")
            return redirect('staff-role-list')
        else:
            messages.error(request, "Please correct the errors below.")
            return render(request, 'duty/assign_staff_role.html', {'form': form, 'subjects': Subject.objects.all()})

    else:
        form = StaffRolesForm()
        subjects = Subject.objects.all()

    return render(request, 'duty/assign_staff_role.html', {'form': form, 'subjects': subjects})

# apps/duty/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import UpdateClassTeacherForm
from .models import StaffRoles

def update_class_teacher(request, role_id):
    # Get the specific staff role or return 404 if not found
    staff_role = get_object_or_404(StaffRoles, id=role_id, is_class_teacher=True)

    if request.method == 'POST':
        form = UpdateClassTeacherForm(request.POST, instance=staff_role)
        if form.is_valid():
            form.save()
            messages.success(request, "Class teacher updated successfully.")
            return redirect('staff-role-list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UpdateClassTeacherForm(instance=staff_role)

    return render(request, 'duty/update_class_teacher.html', {
        'form': form,
        'staff_role': staff_role,
    })

from django.shortcuts import render
from .models import DailySchedule, ClassSchedule
from apps.corecode.models import StudentClass
from duty.models import StaffRoles

def daily_schedule_list(request):
    daily_schedules = DailySchedule.objects.all()
    schedule_data = {}

    for schedule in daily_schedules:
        # Create a dictionary for each day's class schedules
        class_schedule_map = {}
        for class_schedule in schedule.class_schedules.all():
            class_name = class_schedule.student_class.name
            if class_name not in class_schedule_map:
                class_schedule_map[class_name] = []
            class_schedule_map[class_name].append(class_schedule)

        schedule_data[schedule] = class_schedule_map


    staff_on_duty =StaffRoles.objects.filter(on_duty=True).first()


    return render(request, 'duty/daily_schedule_list.html', {
        'schedule_data': schedule_data,
        'staff_on_duty': staff_on_duty.staff if staff_on_duty else "No staff on duty found"
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.forms import inlineformset_factory
from .models import DailySchedule, ClassSchedule
from .forms import DailyScheduleForm, ClassScheduleForm
from apps.corecode.models import StudentClass

def update_schedule(request, day_id):
    print("Entering update_schedule view for day_id:", day_id)
    
    # Fetch the DailySchedule instance for the specified day
    daily_schedule = get_object_or_404(DailySchedule, pk=day_id)
    print("Fetched DailySchedule instance:", daily_schedule)
    
    # Instantiate the form for DailySchedule with the current data
    daily_form = DailyScheduleForm(request.POST or None, instance=daily_schedule)
    print("Initialized DailyScheduleForm with data:", daily_form.data)
    
    # Fetch all classes and initialize an empty dictionary for formsets
    classes = StudentClass.objects.all()
    print("Fetched all StudentClass instances:", classes)
    formsets = {}
    
    # Inline formset factory for ClassSchedule linked to the current DailySchedule
    ClassScheduleFormSet = inlineformset_factory(
        DailySchedule,
        ClassSchedule,
        form=ClassScheduleForm,
        extra=0,  # No additional blank form initially
        can_delete=True  # Allows entries to be deleted
    )
    
    if request.method == 'POST':
        print("Processing POST request")
        
        # Validate DailySchedule form
        if daily_form.is_valid():
            print("DailyScheduleForm is valid")
            daily_schedule_instance = daily_form.save()
            formsets_valid = True  # Flag to check formset validity
            
            # Process formsets for each class
            for student_class in classes:
                print(f"Processing formset for StudentClass: {student_class.name} (ID: {student_class.id})")
                
                # Filter existing schedules for the specific class and day
                queryset = ClassSchedule.objects.filter(student_class=student_class, daily_schedule=daily_schedule)
                formset = ClassScheduleFormSet(
                    request.POST,
                    instance=daily_schedule_instance,
                    queryset=queryset,
                    prefix=f'class_{student_class.id}'
                )
                formsets[student_class] = formset
                
                # Check if the formset is valid and save if so
                if formset.is_valid():
                    print(f"Formset for class {student_class.name} is valid. Saving entries...")
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.student_class = student_class  # Set the related class
                        instance.daily_schedule = daily_schedule_instance  # Associate with the daily schedule
                        instance.save()
                        print(f"Saved ClassSchedule instance: {instance}")
                    formset.save_m2m()  # Save many-to-many relationships if applicable
                    print(f"Completed saving formset for {student_class.name}.")
                else:
                    formsets_valid = False
                    print(f"Formset for {student_class.name} is invalid. Errors: {formset.errors}")
                    messages.error(request, f"Errors found in {student_class.name} schedule. Please correct the errors.")
                    break
            
            # Redirect if all formsets are valid
            if formsets_valid:
                messages.success(request, "Schedule updated successfully.")
                print("All formsets were valid. Schedule updated successfully.")
                return redirect('daily-schedule-list')
            else:
                print("Some formsets were invalid. Schedule not updated.")
        else:
            print("DailyScheduleForm is invalid. Errors:", daily_form.errors)
            messages.error(request, "Please correct the errors in the daily schedule.")

    else:
        print("GET request - initializing formsets with existing data")
        
        # For GET requests, populate formsets with existing data for each class
        for student_class in classes:
            queryset = ClassSchedule.objects.filter(student_class=student_class, daily_schedule=daily_schedule)
            formset = ClassScheduleFormSet(
                instance=daily_schedule,
                queryset=queryset,
                prefix=f'class_{student_class.id}'
            )
            formsets[student_class] = formset
            print(f"Initialized formset for class {student_class.name} with {len(formset)} forms")

    print("Rendering create_schedule.html template with form and formsets")
    return render(request, 'duty/update_schedule.html', {
        'daily_form': daily_form,
        'formsets': formsets,
        'classes': classes,
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import DailySchedule

def delete_schedule(request, day_id):
    # Retrieve the DailySchedule instance for the specified day
    daily_schedule = get_object_or_404(DailySchedule, pk=day_id)

    if request.method == 'POST':
        # Delete the DailySchedule instance, which cascades to delete associated ClassSchedules
        daily_schedule.delete()
        messages.success(request, f"Schedule for {daily_schedule.day} has been successfully deleted.")
        return redirect('daily-schedule-list')
    
    # Render a confirmation page
    return render(request, 'duty/delete_schedule_confirmation.html', {
        'daily_schedule': daily_schedule,
    })


def delete_class_schedule(request, day_id, class_schedule_id):
    """
    View for deleting a specific ClassSchedule for a given day and student class.
    """
    daily_schedule = get_object_or_404(DailySchedule, pk=day_id)
    class_schedule = get_object_or_404(ClassSchedule, pk=class_schedule_id, daily_schedule=daily_schedule)

    if request.method == 'POST':
        class_schedule.delete()
        messages.success(request, f"Schedule for {class_schedule.student_class} on {daily_schedule.day} deleted successfully.")
        return redirect('daily-schedule-list')  # Redirect to the schedule list after deletion

    return render(request, 'duty/delete_class_schedule_confirmation.html', {
        'daily_schedule': daily_schedule,
        'class_schedule': class_schedule,
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import DailySchedule, ClassSchedule
from .forms import ClassScheduleFormSet

def update_class_schedule(request, day_id, class_schedule_id):
    """
    View for updating a specific ClassSchedule for a given day and student class.
    """
    daily_schedule = get_object_or_404(DailySchedule, pk=day_id)
    class_schedule = get_object_or_404(ClassSchedule, pk=class_schedule_id, daily_schedule=daily_schedule)

    print(f"Entering update_class_schedule view with day_id={day_id} and class_schedule_id={class_schedule_id}")
    print(f"Fetched DailySchedule: {daily_schedule}")
    print(f"Fetched ClassSchedule for student class {class_schedule.student_class}")

    # Get all schedules for the specific class on this day
    class_schedules = ClassSchedule.objects.filter(
        daily_schedule=daily_schedule,
        student_class=class_schedule.student_class
    )
    print(f"Retrieved class schedules for the day: {class_schedules}")

    # Set extra=0 to avoid additional blank forms
    ClassScheduleFormSet.extra = 0

    if request.method == 'POST':
        formset = ClassScheduleFormSet(request.POST, queryset=class_schedules, instance=daily_schedule)

        print("POST data received for formset processing:")
        for i, form in enumerate(formset):
            print(f"Form {i} data: {form.data}")

        if formset.is_valid():
            print("Formset is valid. Saving data...")
            formset.save()
            messages.success(request, f"Schedule for {class_schedule.student_class} on {daily_schedule.day} updated successfully.")
            return redirect('daily-schedule-list')
        else:
            print("Formset is invalid. Errors:")
            for i, form in enumerate(formset):
                if form.errors:
                    print(f"Errors in form {i}: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        formset = ClassScheduleFormSet(queryset=class_schedules, instance=daily_schedule)
    
    print("Rendering update_class_schedule.html template with formset.")
    return render(request, 'duty/update_class_schedule.html', {
        'formset': formset,
        'daily_schedule': daily_schedule,
        'class_schedule': class_schedule,
    })


from django.shortcuts import render, redirect
from django.contrib import messages
from .models import DailySchedule, ClassSchedule
from .forms import DailyScheduleForm, ClassScheduleForm, ClassScheduleFormSet
from apps.corecode.models import StudentClass

def create_schedule(request):
    print("Entering create_schedule view")
    daily_form = DailyScheduleForm(request.POST or None)
    classes = StudentClass.objects.all()
    formsets = {}

    if request.method == 'POST':
        print("Received POST request")
        
        if daily_form.is_valid():
            daily_schedule = daily_form.save()
            formsets_valid = True

            for student_class in classes:
                print(f"Processing formset for {student_class.name}")
                formset = ClassScheduleFormSet(
                    request.POST, instance=daily_schedule, prefix=f'class_{student_class.id}'
                )
                formsets[student_class] = formset

                if formset.is_valid():
                    instances = formset.save(commit=False)
                    for instance in instances:
                        print(f"Saving instance for {student_class.name} with start time {instance.start_time}")
                        instance.student_class = student_class
                        instance.save()
                    formset.save_m2m()
                else:
                    formsets_valid = False
                    print(f"Errors in formset for {student_class.name}: {formset.errors}")
                    messages.error(request, f"Errors found in {student_class.name} schedule. Please correct the errors.")
                    break

            if formsets_valid:
                messages.success(request, "Schedules created successfully.")
                return redirect('daily-schedule-list')
        else:
            print("Daily form is invalid:", daily_form.errors)

    else:
        for student_class in classes:
            formset = ClassScheduleFormSet(instance=None, prefix=f'class_{student_class.id}')
            formsets[student_class] = formset

    return render(request, 'duty/create_schedule.html', {
        'daily_form': daily_form,
        'formsets': formsets,
        'classes': classes,
    })
