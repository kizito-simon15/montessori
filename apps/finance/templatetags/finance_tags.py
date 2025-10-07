# apps/finance/templatetags/finance_tags.py 
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP   
from typing import Any
from django.template.defaultfilters import stringfilter 
from django import template
from django.utils.safestring import mark_safe




register = template.Library()

@register.filter
def add_attributes(field, attr):
    """
    Adds attributes to a form field widget.
    Usage: {{ form.field|add_attributes:"class=form-control placeholder=Enter text" }}
    """
    attrs = {}
    attr_dict = {}
    if attr:
        # Split the attribute string into key-value pairs
        for item in attr.split():
            if '=' in item:
                key, value = item.split('=', 1)
                attr_dict[key] = value
    attrs.update(field.field.widget.attrs)
    attrs.update(attr_dict)
    return field.as_widget(attrs=attrs)

@register.filter
def add_class(field, css_class):
    """
    Adds a CSS class to a form field widget.
    Usage: {{ form.field|add_class:"form-control" }}
    """
    return add_attributes(field, f"class={css_class}")




# ───────────────────────────────────────────────────────────────
#  Form-field helpers
# ───────────────────────────────────────────────────────────────
@register.filter(name="add_class")
def add_class(field, css):
    """
    Append a CSS class (or classes) to a Django form widget in-template.

    {{ form.field|add_class:"my-class other" }}
    """
    attrs = field.field.widget.attrs
    existing = attrs.get("class", "")
    # keep order: existing → new
    combined = f"{existing} {css}".strip() if existing else css
    return field.as_widget(attrs={**attrs, "class": combined})


@register.filter(name="attr")
def add_attribute(field, args):
    """
    Set **any** HTML attribute on a form widget.

    {{ form.field|attr:'placeholder:Type amount' }}
    """
    bits = args.split(":", 1)
    key = bits[0]
    val = bits[1] if len(bits) > 1 else ""
    return field.as_widget(attrs={**field.field.widget.attrs, key: val})


# ───────────────────────────────────────────────────────────────
#  Numeric helpers
# ───────────────────────────────────────────────────────────────
@register.filter(name="gt")     # greater-than
def greater_than(val, arg):
    """Return *True* if val > arg (both can be strings or numbers)."""
    try:
        return float(val) > float(arg)
    except (TypeError, ValueError):
        return False


@register.filter(name="lt")     # less-than
def less_than(val, arg):
    """Return *True* if val < arg."""
    try:
        return float(val) < float(arg)
    except (TypeError, ValueError):
        return False


@register.filter(name="percent")
def as_percent(value, total):
    """
    Return *value / total × 100*, formatted with 0 decimal places.

    {{ paid|percent:expected }} → "43"
    """
    try:
        return int(round(float(value) / float(total) * 100))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


# ───────────────────────────────────────────────────────────────
#  Misc. helpers
# ───────────────────────────────────────────────────────────────
@register.simple_tag
def badge(text, hue="info"):
    """
    Quick coloured pill for statuses.

    {% badge invoice.status "success" %}
    """
    return mark_safe(
        f'<span class="badge bg-{hue} text-capitalize">{text}</span>'
    )


@register.filter(name="mul")
def mul(value, arg):
    try:
        return Decimal(value) * Decimal(arg)
    except (TypeError, ValueError, InvalidOperation):
        return ""
    

@register.filter(name="minus")
def minus(a, b):
    try:
        return Decimal(str(a)) - Decimal(str(b))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")

@register.filter(name="dec")          # ← NEW
def dec(value):
    """
    Format with thousands-commas.  Show decimals ONLY when the number really
    has cents, e.g. 83 750  → “83,750”   •   83 750.4  → “83,750.40”
    """
    try:
        val = Decimal(value)
        if val == val.to_integral_value():         # whole number → no dp
            return "{:,}".format(int(val))
        return "{:,.2f}".format(val.quantize(Decimal("0.01"), ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return value
