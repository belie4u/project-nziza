from django import template

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
