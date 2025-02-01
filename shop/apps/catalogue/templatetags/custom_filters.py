from django import template
from oscar.apps.partner.models import StockRecord

register = template.Library()


@register.filter(name='get_range')
def get_range(value, arg=None):
    return range(int(value)) if arg is None else range(int(value), int(arg))


@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiplies the given value by the provided argument.
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    

@register.simple_tag
def get_stock_record(product):

    stock_record = StockRecord.objects.filter(product=product).first()
    if stock_record:
        return {
            "partner": stock_record.partner.name,
            "sku": stock_record.partner_sku
        }
    return None
