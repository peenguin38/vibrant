from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

@register.filter
def pluralize_ru(value, forms):
    """
    Склонение слов по числительным:
    {{ 5|pluralize_ru:"товар,товара,товаров" }} → товаров
    """
    try:
        one, few, many = forms.split(',')
        value = abs(int(value))
    except (ValueError, TypeError):
        return many

    if value % 10 == 1 and value % 100 != 11:
        return one
    elif 2 <= value % 10 <= 4 and (value % 100 < 10 or value % 100 >= 20):
        return few
    else:
        return many
