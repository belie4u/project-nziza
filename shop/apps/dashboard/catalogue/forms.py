from django import forms
from apps.catalogue.models import Option

class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        ["name", "type", "required",
         "order", "help_text", "option_group", "price_per_character", "price_per_logo", "price_per_item"]
