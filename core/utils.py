from collections.abc import Iterable

from django.db.models.fields.related import ForeignKey, OneToOneField


def model_unwrap(instance, fields=None, exclude=None, include_timestamps=False):
    """
    Converts a Django model instance or a queryset/list of model instances to a dictionary or list of dictionaries.
    For ForeignKey and OneToOneField, only includes the related object's id to avoid recursion.
    Also adds a <field_name>_id key for ForeignKey/OneToOneField with the related object's id.
    By default, 'created_at' and 'updated_at' are excluded unless include_timestamps=True.
    :param instance: The model instance, queryset, or list to convert.
    :param fields: Optional list of field names to include.
    :param exclude: Optional list of field names to exclude.
    :param include_timestamps: If True, includes 'created_at' and 'updated_at' fields.
    :return: dict or list of dicts representation of the model instance(s).
    """
    # Handle QuerySet, list, or any iterable of model instances (but not string/bytes)
    if isinstance(instance, Iterable) and not isinstance(instance, (str, bytes, dict)) and hasattr(instance, "__iter__"):
        return [
            model_unwrap(
                obj,
                fields=fields,
                exclude=exclude,
                include_timestamps=include_timestamps,
            )
            for obj in instance
        ]

    data = {}
    default_exclude = set()
    if not include_timestamps:
        default_exclude.update({"created_at", "updated_at"})
    if exclude is not None:
        exclude_set = set(exclude) | default_exclude
    else:
        exclude_set = default_exclude

    for field in instance._meta.fields:
        field_name = field.name
        if fields is not None and field_name not in fields:
            continue
        if field_name in exclude_set:
            continue

        # Handle ForeignKey and OneToOneField by just including the related object's id
        if isinstance(field, (ForeignKey, OneToOneField)):
            related_obj = getattr(instance, field_name)
            data[f"{field_name}_id"] = related_obj.pk if related_obj is not None else None
        else:
            data[field_name] = getattr(instance, field_name)
    print("data", type(data))
    return data
