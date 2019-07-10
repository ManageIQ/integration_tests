import collections
from difflib import SequenceMatcher


class MultipleResultsException(Exception):
    pass


def soft_get(obj,
             field_base_name,
             dict_=False,
             case_sensitive=False,
             best_match=True,
             dont_include=None):
    """
    This function used for cases that we want to get some attribute that we
    either know only few parts of its name or want to prevent from case issues.

    Example:
        Imagine you have a relationships table and you want to get 'image' field.
        Since sometimes the exact name of the field is changing among versions, pages, etc.
        it could be appear as 'Images', 'Image', 'Container Images', Containers Images', etc.
        Since we don't care for the exact name and know that 'image' is a unique in the table,
        we can use this function to prevent from this complexity.

    Args:
        * obj: The object which we want to get the attribute
        * field_base_name: The base name, a string that we know
                           for sure that is a sub-string of the target field
        * dict_: Whether this is a dict AND we want to perform the same functionality on its keys
        * case_sensitive: Whether the search is a sensitive case.
        * best_match: If True: in case that it found more than 1 match field,
                               it will take the closest one
                      If False: in case that it found more than 1 match field,
                                it will raise an error
        * dont_include: Strings that should not be a part of the field.
                        Used to prevent cases like: soft_get(obj, 'image') -> obj.image_registry
    Returns:
        The value of the target attribute
    """
    dont_include = dont_include or []
    signature = ('soft_get({}, {}, dict_={}, case_sensitive={})'
                 .format(obj, field_base_name, dict_, case_sensitive))
    if not case_sensitive:
        field_base_name = field_base_name.lower()
    if dict_:
        if not isinstance(obj, collections.Mapping):
            raise TypeError('{}: {} is not a dict (type={}). '
                            .format(signature, obj, type(obj)))
        all_fields = list(obj.keys())
    else:
        all_fields = dir(obj)
    found_fields = []
    if not case_sensitive:
        dont_include = [s.lower() for s in dont_include]
    for field in all_fields:
        origin_field = field
        if not case_sensitive:
            field = field.lower()
        if (field_base_name in field) and \
                all([(s not in field) for s in dont_include]):
            found_fields.append(origin_field)
    if not found_fields:
        raise AttributeError('{}: Could not find a member for field {}.'
                             .format(signature, field_base_name))
    elif len(found_fields) > 1:
        if not best_match:
            raise MultipleResultsException('{}: Found more than 1 member for {}: {}'
                            .format(signature, field_base_name, found_fields))
        found_fields = [max(found_fields, key=lambda s:
                            SequenceMatcher(None, s, field_base_name).ratio())]

    if dict_:
        return obj[found_fields[0]]
    return getattr(obj, found_fields[0])
