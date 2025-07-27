from django.utils import timezone

def model_unwrap(instance, fields=None, exclude=None):
    """
    Converts a Django model instance to a dictionary.
    :param instance: The model instance to convert.
    :param fields: Optional list of field names to include.
    :param exclude: Optional list of field names to exclude.
    :return: dict representation of the model instance.
    """
    data = {}
    for field in instance._meta.fields:
        field_name = field.name
        if fields is not None and field_name not in fields:
            continue
        if exclude is not None and field_name in exclude:
            continue
        data[field_name] = getattr(instance, field_name)
    return data