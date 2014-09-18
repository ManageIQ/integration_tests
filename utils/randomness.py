import random
import string
import sys
import uuid


def generate_random_int(max=sys.maxint):
    max = int(max)
    return random.randint(0, max)


def generate_random_local_ip():
    return "10.{}.{}.{}".format(
        generate_random_int(255), generate_random_int(255), generate_random_int(255))


def generate_random_string(size=8):
    size = int(size)

    def random_string_generator(size):
        choice_chars = string.letters + string.digits
        for x in xrange(size):
            yield random.choice(choice_chars)
    return ''.join(random_string_generator(size))


def generate_lowercase_random_string(size=8):
    size = int(size)

    def random_string_generator(size):
        choice_chars = string.letters + string.digits
        for x in xrange(size):
            yield random.choice(choice_chars)
    return ''.join(random_string_generator(size)).lower()


def generate_random_uuid_as_str():
    return str(uuid.uuid4())


def pick(from_where, n, quiet=True):
    """Picks `n` elements randomly from source iterable.

    Will be converted during processing so no side effects

    Args:
        from_where: Source iterable.
        n: How many elements to pick
        quiet: Whether raise the exception about n bigger than len(from_where) or not. Default True.
    Returns: n-length list with randomly picked elements from `from_where`
    """
    if len(from_where) < n:
        # We want more
        if not quiet:
            raise ValueError("Less elements in from_where than you want!")
        else:
            return list(from_where)
    elif len(from_where) == n:
        # We want all
        return list(from_where)
    # Random picking
    result = []
    from_where = list(from_where)  # to prevent side effects
    while len(result) < n:
        index = random.choice(range(len(from_where)))
        result.append(from_where.pop(index))
    return result


class RandomizeValues(object):
    _randomizers = {
        'random_int': generate_random_int,
        'random_str': generate_random_string,
        'random_uuid': generate_random_uuid_as_str,
    }

    @classmethod
    def from_dict(cls, d):
        """Load a dictionary with randomizable values and randomize them

        Targeted at dicts produced from loading YAML, so it doesn't try to
        handle more than basic types (str, tuple, list, set, dict)

        Allowable dict values to randomize (remember to quote these in YAML):

        - {random_int}: Becomes an int between 0 and maxint, inclusive
        - {random_int:max}: Becomes an int between 0 and "max",
          inclusive
        - {random_str}: Becomes a string of numbers and letters,
          length 8
        - {random_str:length}: Becomes a string of numbers and
          letters, length "length"
        - {random_uuid}: Becomes a completely random uuid

        Returns a modified dict with randomize values

        """
        return {k: cls._randomize_item(v) for k, v in d.items()}

    @classmethod
    def _randomize_item(cls, item):
        # Go through the most common types deserialized from yaml
        # pass them back through RandomizeValues as needed until
        # there are concrete things to randomize
        if isinstance(item, dict):
            return cls.from_dict(item)
        elif isinstance(item, tuple):
            return tuple(cls._randomize_item(x) for x in item)
        elif isinstance(item, list):
            return [cls._randomize_item(x) for x in item]
        elif isinstance(item, set):
            return set([cls._randomize_item(x) for x in item])
        elif isinstance(item, basestring) and item.startswith('{random_'):
            # Concreteness! Try to parse out the randomness case and
            # possible argument to the randomizer
            # '{key:arg}' should become 'key' and 'arg'; if no arg, arg is None
            try:
                key, arg = item.strip('{}').split(':', 1)
            except ValueError:
                key, arg = item.strip('{}'), None
        else:
            # No idea what this is, return it
            return item

        if key in cls._randomizers:
            # If the case actually exists, call its randomizer
            randomizer = cls._randomizers[key]
            if arg:
                random_value = randomizer(arg)
            else:
                random_value = randomizer()
            return str(random_value)
        else:
            # randomizer was tripped, but no matching randomizers found
            # in _randomizers, just return what was there
            return item
