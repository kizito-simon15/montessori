from django.shortcuts import render, redirect, get_object_or_404
from .forms import PropertyForm, UpdatePropertyForm
from .models import Property
from apps.corecode.models import AcademicSession
from django.contrib import messages

def property_list(request):
    current_session = AcademicSession.objects.filter(current=True).first()
    properties = Property.objects.filter(session=current_session)
    return render(request, 'property_list.html', {'properties': properties})


def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            # Set the session for the property
            current_session = AcademicSession.objects.filter(current=True).first()
            if current_session:
                form.instance.session = current_session
                form.save()
                # Add a success message
                messages.success(request, 'Property added successfully!')
                return redirect('property_list')
            else:
                form.add_error(None, "No active session found.")
        else:
            print(form.errors)  # Log form errors for debugging
    else:
        form = PropertyForm()
    return render(request, 'add_property.html', {'form': form})


def property_detail(request, pk):
    property = get_object_or_404(Property, pk=pk)
    return render(request, 'property_details.html', {'property': property})

def update_property(request, pk):
    property = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        form = UpdatePropertyForm(request.POST, instance=property)
        if form.is_valid():
            form.save()
            return redirect('property_list')
    else:
        form = UpdatePropertyForm(instance=property)
    return render(request, 'update_property.html', {'form': form})

def delete_property(request, pk):
    property = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        property.delete()
        return redirect('property_list')
    return render(request, 'delete_property.html', {'property': property})
