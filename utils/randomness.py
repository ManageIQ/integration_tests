# -*- coding: utf-8 -*-
import fauxfactory
import sys


def generate_random_int(max=sys.maxint):
    max = int(max)
    return fauxfactory.gen_integer(0, max)


def generate_random_local_ip():
    return "10.{}.{}.{}".format(
        generate_random_int(255), generate_random_int(255), generate_random_int(255))


def generate_random_string(size=8):
    size = int(size)

    return fauxfactory.gen_string("alphanumeric", size)


def generate_lowercase_random_string(size=8):
    return generate_random_string(size).lower()


class RandomizeValues(object):
    _randomizers = {
        'random_int': generate_random_int,
        'random_str': generate_random_string,
        'random_uuid': fauxfactory.gen_uuid,
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
