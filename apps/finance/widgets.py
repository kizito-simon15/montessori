# finance/widgets.py  – patched 02 Jul 2025
from __future__ import annotations

from django import forms
from django.forms.models import ModelChoiceIteratorValue
from apps.staffs.models import Staff


class StaffSelectWithData(forms.Select):
    """
    <select> for the Salary-Invoice form.
    Each <option> carries data-* attributes for instant JS salary maths.
    """

    option_inherits_attrs = True  # keep "class" etc. on <option>

    # ------------------------------------------------------------------ #
    #  SAFE __init__  → guarantees attrs is a dict                       #
    # ------------------------------------------------------------------ #
    def __init__(self, attrs: dict | None = None, choices=()):
        base = {
            "class": (
                "form-select w-full rounded-md border-gray-300 "
                "focus:ring-2 focus:ring-indigo-500"
            )
        }
        if attrs:
            # merge caller-supplied attributes
            base.update(attrs)
        # always pass a *dict* to super()
        super().__init__(attrs=base, choices=choices)

    # ------------------------------------------------------------------ #
    #  Add data-attributes to each <option>                              #
    # ------------------------------------------------------------------ #
    def create_option(
        self,
        name: str,
        value,
        label,
        selected: bool,
        index: int,
        subindex: int | None = None,
        attrs: dict | None = None,
    ) -> dict:
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )

        pk = value.value if isinstance(value, ModelChoiceIteratorValue) else value
        if not pk:
            return option

        try:
            staff: Staff = Staff.objects.get(pk=pk)
        except Staff.DoesNotExist:
            return option

        option["attrs"].update(
            {
                "data-basic":     f"{staff.salary:.2f}",
                "data-special":   f"{staff.special_allowance:.2f}",
                "data-gross":     f"{staff.gross_for_deductions:.2f}",
                "data-has-heslb": "true" if staff.has_helsb else "false",
                "data-hrate":     f"{staff.helsb_rate:.2f}",  # percent
            }
        )
        return option
