from PIL import Image
from django import forms
from django.utils.translation import gettext_lazy as _
from oscar.apps.dashboard.catalogue.forms import BaseCategoryForm
from oscar.apps.dashboard.catalogue.forms import SEOFormMixin


class CategoryForm(SEOFormMixin, BaseCategoryForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "slug" in self.fields:
            self.fields["slug"].required = False
            self.fields["slug"].help_text = _(
                "Leave blank to generate from category name"
            )

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if image:
            # Open the image file
            try:
                img = Image.open(image)
            except (IOError, SyntaxError) as e:
                raise forms.ValidationError(_("Invalid image file."))

            # Get the dimensions
            width, height = img.size

            # Define exact dimensions
            required_width = 235
            required_height = 356

            if width != required_width or height != required_height:
                raise forms.ValidationError(
                    _("Image must have exact dimensions of %(width)sx%(height)s pixels."),
                    params={"width": required_width, "height": required_height},
                )

            # Verify the file is a valid image
            try:
                img.verify()
            except (IOError, SyntaxError):
                raise forms.ValidationError(_("Invalid image file."))

        return image
