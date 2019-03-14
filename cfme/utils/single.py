def single(iterable):
    """Returns the first item from the `iterable` and checks whether it is the
    only one there."""
    it = iter(iterable)
    try:
        item = next(it)
    except StopIteration:
        raise ItemMissing('Some item was expected and not found in {!r}'.format(iterable))

    try:
        next(it)
    except StopIteration:
        # We expected just one item. So we just return what we have got.
        return item
    else:
        raise MoreThanOne('There are more than only one item in {!r}'.format(iterable))


class ItemMissing(ValueError):
    pass


class MoreThanOne(ValueError):
    pass
