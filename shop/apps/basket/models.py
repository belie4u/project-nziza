


from oscar.apps.basket.abstract_models import AbstractBasket, AbstractLine
from decimal import Decimal as D
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from apps.catalogue.models import Option
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
import os


class Basket(AbstractBasket):

    def _handle_uploaded_file(self, file):
        """
        Handles saving the uploaded file and returns the file path relative to MEDIA_URL.
        """
        # Sanitize and ensure a unique filename
        file_name = os.path.basename(file.name)
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')

        # Ensure the upload directory exists
        os.makedirs(upload_dir, exist_ok=True)

        # Generate a unique file path
        upload_path = os.path.join(upload_dir, file_name)
        base, extension = os.path.splitext(file_name)
        counter = 1
        while os.path.exists(upload_path):
            file_name = f"{base}_{counter}{extension}"
            upload_path = os.path.join(upload_dir, file_name)
            counter += 1

        # Save the uploaded file
        with open(upload_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Return the relative path to MEDIA_URL
        relative_path = os.path.join('uploads', file_name)
        return relative_path

    def add_product(self, product, quantity=1, options=None):
        if options is None:
            options = []
        if not self.id:
            self.save()

        # Use a dictionary to track option totals
        option_totals = {}

        def make_hashable(value):
            if isinstance(value, dict):
                return frozenset((k, make_hashable(v)) for k, v in value.items())
            elif isinstance(value, list):
                return tuple(make_hashable(v) for v in value)
            return value

        for option_data in options:
            try:
                # Use filter to get all matching options, then select the first one
                option = Option.objects.filter(
                    name=option_data["option"]
                ).first()

                # If no matching option is found, raise an error
                if option is None:
                    raise ValueError(f"Option with name '{
                                     option_data['option']}' not found.")

            except MultipleObjectsReturned:
                # Handle the case where multiple options are returned
                raise ValueError(f"Multiple options found for '{
                                 option_data['option']}'.")

            # Ensure option_data["value"] is hashable
            option_value = option_data["value"]

            # Convert dictionaries to frozensets of tuples
            if isinstance(option_value, dict):
                option_value = make_hashable(option_value)

            # Convert lists to tuples to ensure hashability
            elif isinstance(option_value, list):
                option_value = tuple(option_value)

            # Use the hashable option_value as part of the dictionary key
            option_key = (option.id, option_value)

            # Add price to option_totals
            price = option.get_price(option_value, product)
            option_totals[option_key] = price * quantity

        # Calculate and update total prices based on option totals
        self.price_excl_tax = self._calculate_total_price(option_totals)
        self.price_incl_tax = self._calculate_total_price(option_totals)
        self.save()

        # Ensure that all lines are the same currency
        price_currency = self.currency
        stock_info = self.get_stock_info(product, options)

        if not stock_info.price.exists:
            raise ValueError(
                f"Strategy hasn't found a price for product {product}")

        if price_currency and stock_info.price.currency != price_currency:
            raise ValueError(
                f"Basket lines must all have the same currency. Proposed "
                f"line has currency {
                    stock_info.price.currency}, while basket has currency {price_currency}"
            )

        if stock_info.stockrecord is None:
            raise ValueError(
                f"Basket lines must all have stock records. Strategy hasn't "
                f"found any stock record for product {product}"
            )

        # Line reference is used to distinguish between variations of the same
        # product (e.g., T-shirts with different personalizations)
        line_ref = self._create_line_reference(
            product, stock_info.stockrecord, options)

        # Determine price to store (if one exists). It is only stored for
        # audit and sometimes caching.
        defaults = {
            "quantity": quantity,
            "price_excl_tax": stock_info.price.excl_tax,
            "price_currency": stock_info.price.currency,
            "tax_code": stock_info.price.tax_code,
        }
        if stock_info.price.is_tax_known:
            defaults["price_incl_tax"] = stock_info.price.incl_tax

        line, created = self.lines.get_or_create(
            line_reference=line_ref,
            product=product,
            stockrecord=stock_info.stockrecord,
            defaults=defaults
        )

        if created:
            for option_dict in options:
                option = option_dict["option"]
                value = option_dict["value"]

                # Handle uploaded file if the option type is IMAGE
                if isinstance(value, InMemoryUploadedFile):
                    value = self._handle_uploaded_file(
                        value)  # Convert file to path

                # Ensure value is seriaInMemoryUploadedFilelizable (e.g., convert to string if necessary)
                if isinstance(value, (list, dict)):
                    # If it's a complex type, you might want to convert it to a string representation
                    # or use json.dumps(value) if you need JSON format
                    value = str(value)

                # Create the line attribute with the processed value
                line.attributes.create(option=option, value=value)
        else:
            line.quantity = max(0, line.quantity + quantity)
            line.save()

        # Returning the line is useful when overriding this method.
        return line, created

    add_product.alters_data = True
    add = add_product

    def _calculate_total_price(self, option_totals):
        total = D('0.00')
        for price in option_totals.values():
            total += price
        return total

    @property
    def total_excl_tax(self):
        total_from_lines = self._get_total(
            "line_price_excl_tax_incl_discounts")
        total_from_options = sum(
            total for _, total in self.get_option_totals().items())
        return total_from_lines + total_from_options

    @property
    def total_incl_tax(self):
        total_from_lines = self._get_total(
            "line_price_incl_tax_incl_discounts")
        total_from_options = sum(
            total for _, total in self.get_option_totals().items())
        return total_from_lines + total_from_options

    def _get_total(self, model_property):
        """
        For executing a named method on each line of the basket
        and returning the total.
        """
        total = D("0.00")
        for line in self.all_lines():
            if model_property == "line_price_excl_tax_incl_discounts":
                total += getattr(line, model_property)
                for option_cost in self.get_option_totals().values():
                    total += option_cost
            else:
                try:
                    total += getattr(line, model_property)
                except ObjectDoesNotExist:
                    # Handle situation where the product may have been deleted
                    pass
                except TypeError:
                    # Handle unavailable products with no known price
                    info = self.get_stock_info(
                        line.product, line.attributes.all())
                    if info.availability.is_available_to_buy:
                        raise
        return total

    def get_option_totals(self):
        """
        Return a dictionary of option totals for all lines in the basket.
        """
        def make_hashable(value):
            if isinstance(value, dict):
                # Convert dictionary to frozenset of tuples
                return frozenset((k, make_hashable(v)) for k, v in value.items())
            elif isinstance(value, list):
                # Convert list to tuple and ensure all elements are hashable
                return tuple(make_hashable(v) for v in value)
            return value  # Return the value as is if already hashable

        option_totals = {}
        for line in self.all_lines():
            for attribute in line.attributes.all():
                option = attribute.option
                value = attribute.value

                # Ensure value is hashable
                value = make_hashable(value)

                price = option.get_price(value, line.product)

                # Use the hashable value as part of the dictionary key
                option_key = (option.id, value)

                if option_key not in option_totals:
                    option_totals[option_key] = D('0.00')

                option_totals[option_key] += price * line.quantity

        return option_totals
from oscar.apps.basket.models import *