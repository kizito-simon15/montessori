from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import SchoolLocationForm
from .models import SchoolLocation

def set_school_location(request):
    if request.method == "POST":
        form = SchoolLocationForm(request.POST)
        if form.is_valid():
            # Deactivate all other locations before saving the new one
            SchoolLocation.objects.filter(is_active=True).update(is_active=False)
            
            # Save the new location and set it as active
            location = form.save(commit=False)
            location.is_active = True
            location.save()

            messages.success(request, 'Location saved successfully and set as active.')
            return redirect('location_list')
    else:
        form = SchoolLocationForm()

    return render(request, 'location/set_school_location.html', {'form': form})

from geopy.distance import geodesic

def calculate_suggested_radius(boundary_coordinates, center_point):
    max_distance = 0
    for point in boundary_coordinates:
        distance = geodesic(center_point, point).meters
        if distance > max_distance:
            max_distance = distance
    return max_distance + 10  # Add a small buffer to the max distance

def location_details(request, pk):
    location = get_object_or_404(SchoolLocation, pk=pk)
    return render(request, 'location/location_details.html', {'location': location})

def update_location(request, pk):
    location = get_object_or_404(SchoolLocation, pk=pk)
    
    if request.method == 'POST':
        form = SchoolLocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.success(request, 'Location updated successfully.')
            return redirect('location_list')
        else:
            messages.error(request, 'There was an error updating the location.')
    else:
        form = SchoolLocationForm(instance=location)
    
    return render(request, 'location/set_school_location.html', {'form': form, 'location': location})

from django.shortcuts import render
from .models import SchoolLocation

def location_list(request):
    # Retrieve all the SchoolLocation instances
    locations = SchoolLocation.objects.all()

    # Pass the locations to the template
    return render(request, 'location/location_list.html', {'locations': locations})

from django.shortcuts import render, redirect, get_object_or_404
from .models import SchoolLocation

def delete_location(request, pk):
    location = get_object_or_404(SchoolLocation, pk=pk)
    if request.method == "POST":
        location.delete()
        return redirect('location_list')  # Replace 'locations_list' with your list view name
    return render(request, 'location/confirm_delete.html', {'location': location})

def activate_location(request, pk):
    location_to_activate = get_object_or_404(SchoolLocation, pk=pk)

    # Deactivate all other locations
    SchoolLocation.objects.filter(is_active=True).update(is_active=False)

    # Activate the selected location
    location_to_activate.is_active = True
    location_to_activate.save()

    messages.success(request, f'Location "{location_to_activate.name}" has been activated.')
    return redirect('location_list')

# View to deactivate a location (if needed)
def deactivate_location(request, pk):
    location_to_deactivate = get_object_or_404(SchoolLocation, pk=pk)
    location_to_deactivate.is_active = False
    location_to_deactivate.save()

    messages.success(request, f'Location "{location_to_deactivate.name}" has been deactivated.')
    return redirect('location_list')