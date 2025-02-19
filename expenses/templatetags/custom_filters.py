from django import template

register = template.Library()

@register.filter
def get_item(value, key):
    """Safely get value from dict or return 0.0"""
    if isinstance(value, dict):
        return float(value.get(str(key), 0.0))
    return 0.0

@register.filter
def sub(value, arg):
    try:
        value_float = float(value)
        arg_float = float(arg)
        result = value_float - arg_float
        return max(result, 0.0)
    except Exception as e:
        print(f"Error in sub: value={value} (type={type(value)}), arg={arg} (type={type(arg)}), error={e}")
        return 0.0