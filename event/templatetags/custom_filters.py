# custom_filters.py

from django import template
from django.utils.timesince import timesince as django_timesince

register = template.Library()

@register.filter
def time_since(value):
    return django_timesince(value)

