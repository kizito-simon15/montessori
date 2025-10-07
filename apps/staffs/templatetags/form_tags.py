from django import template

register = template.Library()


# ----------------- add_class (unchanged) -----------------
@register.filter(name="add_class")
def add_class(field, css):
    """Add a CSS class to a form widget inside a template."""
    if field is None:          # ← prevents AttributeError when the key is wrong
        return ""
    return field.as_widget(attrs={"class": css})

# ----------------- split filter  -----------------
@register.filter(name="split")
def split(value, delimiter=","):
    """
    Splits a string by *delimiter* and returns a list
    so you can iterate in {% for %}.

        {% for item in "a,b,c"|split:"," %} ... {% endfor %}
    """
    if not isinstance(value, str):
        return value
    return [bit.strip() for bit in value.split(delimiter) if bit.strip()]


@register.filter(name="getfield")
def getfield(form, name):
    """
    Usage in template:
        {{ form|getfield:"email" }}
    or inside a loop:
        {% with field=form|getfield:f %}
    """
    try:
        return form[name]
    except KeyError:
        return None
