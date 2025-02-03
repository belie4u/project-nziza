from django.db import models
from django.contrib.auth.models import User
from oscar.apps.catalogue.abstract_models import AbstractProduct, AbstractCategory, AbstractOption,  AbstractAttributeOption

from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from oscar.models.fields import AutoSlugField
import ast

class Option(models.Model):
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"

    SELECT = "select"
    RADIO = "radio"
    MULTI_SELECT = "multi_select"
    CHECKBOX = "checkbox"
    FILE = "file"
    IMAGE = "image"
    LOCATIONS = "locations"

    TYPE_CHOICES = (
        (TEXT, _("Text")),
        (INTEGER, _("Integer")),
        (BOOLEAN, _("True / False")),
        (FLOAT, _("Float")),
        (DATE, _("Date")),
        (SELECT, _("Select")),
        (RADIO, _("Radio")),
        (MULTI_SELECT, _("Multi select")),
        (CHECKBOX, _("Checkbox")),
        (FILE, _("File")),
        (IMAGE, _("Image")),
        (LOCATIONS, _("Locations")),
    )

    price_per_character = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, default=0.00
    )
    price_per_logo = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, default=0.00
    )
    price_per_item = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, default=0.00
    )

    name = models.CharField(_("Name"), max_length=128, db_index=True)
    code = AutoSlugField(_("Code"), max_length=128,
                         unique=True, populate_from="name")
    type = models.CharField(
        _("Type"), max_length=255, default=TEXT, choices=TYPE_CHOICES
    )
    required = models.BooleanField(
        _("Is this option required?"), default=False)
    option_group = models.ForeignKey(
        "catalogue.AttributeOptionGroup",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="product_options",
        verbose_name=_("Option Group"),
        help_text=_(
            'Select an option group if using type "Option" or "Multi Option"'),
    )
    help_text = models.CharField(
        verbose_name=_("Help text"),
        blank=True,
        null=True,
        max_length=255,
        help_text=_("Help text shown to the user on the add to basket form"),
    )
    order = models.IntegerField(
        _("Ordering"),
        null=True,
        blank=True,
        help_text=_(
            "Controls the ordering of product options on product detail pages"),
        db_index=True,
    )

    @property
    def is_option(self):
        return self.type in [self.SELECT, self.RADIO]

    @property
    def is_multi_option(self):
        return self.type in [self.MULTI_SELECT, self.CHECKBOX, self.LOCATIONS]

    @property
    def is_select(self):
        return self.type in [self.SELECT, self.MULTI_SELECT]

    @property
    def is_radio(self):
        return self.type in [self.RADIO]

    def add_empty_choice(self, choices):
        if self.is_select and not self.is_multi_option:
            choices = [("", self.empty_label)] + choices
        elif self.is_radio:
            choices = [(None, self.empty_radio_label)] + choices
        return choices

    def get_choices(self):
        if self.option_group:
            choices = [
                (opt.option, opt.option) for opt in self.option_group.options.all()
            ]
        else:
            choices = []

        if not self.required:
            choices = self.add_empty_choice(choices)

        return choices

    def clean(self):
        if self.type in [self.RADIO, self.SELECT, self.MULTI_SELECT, self.CHECKBOX, self.LOCATIONS]:
            if self.option_group is None:
                raise ValidationError(
                    _("Option Group is required for type %s") % self.get_type_display()
                )
        elif self.option_group:
            raise ValidationError(
                _("Option Group can not be used with type %s") % self.get_type_display()
            )
        return super().clean()

    def get_price(self, value, product=None):
        """
        Calculates the price of an option based on its type and the provided value.

        :param value: The value of the option. For location options, this is a dictionary 
                      containing 'texts' and 'images' fields.
        :param product: The product associated with the option (optional).
        :return: The calculated price for the option.
        """
        if value is None:
            print("Value is None.")
            return 0

        # Convert value from string to dictionary if necessary
        if isinstance(value, str):
            try:
                # Safely evaluate the string to a dictionary
                value = ast.literal_eval(value)
            except Exception as e:
                print(f"Error parsing value: {e}")
                return 0

        total_price = 0

        # Check for TEXT type
        if self.type == self.TEXT and isinstance(value, str):
            total_price += self.price_per_character * len(value)

        # Check for IMAGE type
        elif self.type == self.IMAGE:
            total_price += self.price_per_logo * (1 if value else 0)

        # Check for LOCATION type
        elif self.type == self.LOCATIONS and isinstance(value, dict):
            # Access selected locations and their counts
            selected_locations = value.get('selected locations', [])
            # Count of selected locations
            location_count = len(selected_locations)
            total_price += self.price_per_item * \
                location_count  # Price for selected locations

            # Calculate price for texts
            if 'texts' in value:
                for location_key, text in value['texts'].items():
                    if text:  # Ensure text is not empty
                        text_length = len(text)  # Calculate length of the text
                        total_price += self.price_per_character * text_length * location_count
                        print(f"Adding text price for '{location_key}': {self.price_per_character} * {text_length} * {location_count} = {self.price_per_character * text_length * location_count}")
                              

            # Calculate price for images
            if 'images' in value:
                for location_key, image in value['images'].items():
                    if image:  # Assuming each image has a price, add it if the image string is not empty
                        total_price += self.price_per_logo * location_count
                        print(f"Adding image price for '{location_key}': {self.price_per_logo} * {location_count} for image: {image}")
                              

        # Handle other option types
        elif self.type in (self.SELECT, self.RADIO, self.CHECKBOX):
            total_price += self.price_per_item

        print(f"Total price calculated for LOCATION: {total_price}")
        return total_price

    @property
    def is_file(self):
        return self.type == self.FILE

    @property
    def is_image(self):
        return self.type == self.IMAGE

    def __str__(self):
        return self.name


class OptionPrice(models.Model):
    # ForeignKey relationship to Option
    option = models.ForeignKey(
        Option, on_delete=models.CASCADE, related_name='option_prices')

    # Access the price from the related Option instance
    @property
    def price_per_character(self):
        if self.option:
            return self.option.price_per_character
        return 0

    @property
    def price_per_logo(self):
        if self.option:
            return self.option.price_per_logo
        return 0

    @property
    def price_per_item(self):
        if self.option:
            return self.option.price_per_item
        return 0

    # Method to set prices (mirroring set_stockrecord in Product model)
    def set_option_prices(self, price_per_character, price_per_logo, price_per_item):
        if self.option:
            # Update prices on the related Option instance
            self.option.price_per_character = price_per_character
            self.option.price_per_logo = price_per_logo
            self.option.price_per_item = price_per_item
            self.option.save()




from oscar.apps.catalogue.models import * 
