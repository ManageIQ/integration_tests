# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import math
import re

# TODO: Split the 1000 and 1024 factor out. Now it is not an issue as it is used FOR COMPARISON ONLY
FACTOR = 1024
PREFIXES = ['', 'K', 'M', 'G', 'T', 'P']
FACTORS = {prefix: int(math.pow(FACTOR, i)) for i, prefix in enumerate(PREFIXES)}

UNITS = ['Byte', 'Bytes', 'B', 'b', 'Hz']

EQUAL_UNITS = {
    'B': ('Byte', 'Bytes')
}

# Sanity check
for target_unit, units in EQUAL_UNITS.iteritems():
    assert target_unit in UNITS
    for unit in units:
        assert unit in UNITS

REGEXP = re.compile(
    r'^\s*(\d+(?:\.\d+)?)\s*({})?({})\s*$'.format('|'.join(PREFIXES), '|'.join(UNITS)))


class Unit(object):
    """This class serves for simple comparison of numbers that have units.

    Imagine you pull a text value from the UI. 2 GB. By doing ``Unit.parse('2 GB')`` you get an
    instance of :py:class:`Unit`, which is comparable.

    You can compare two :py:class:`Unit` instances or you can compare :py:class:`Unit` with
    :py:class:`int`, :py:class:`float` or any :py:class:`str` as long as it can go through the
    :py:method:`Unit.parse`.

    If you compare :py:class:`Unit` only (or a string that gets subsequently parsed), it also takes
    the kind of the unit it is, you cannot compare bytes with hertzes. It then calculates the
    absolute value in the base units and that gets compared.

    If you compare with a number, it does it like it was the number of the same unit. So eg.
    doing ``Unit.parse('2 GB') == 2 *1024 * 1024 * 1024 `` is True.
    """
    __slots__ = ['number', 'prefix', 'unit_type']

    @classmethod
    def parse(cls, s):
        s = str(s)
        match = REGEXP.match(s)
        if match is None:
            raise ValueError('{} is not a proper value to be parsed!'.format(repr(s)))
        number, prefix, unit_type = match.groups()
        # Check if it isnt just an another name for another unit.
        for target_unit, units in EQUAL_UNITS.iteritems():
            if unit_type in units:
                unit_type = target_unit
        return cls(float(number), prefix, unit_type)

    def __init__(self, number, prefix, unit_type):
        self.number = float(number)
        self.prefix = prefix
        self.unit_type = unit_type

    @property
    def absolute(self):
        return self.number * FACTORS[self.prefix]

    def _as_same_unit(self, int_or_float):
        return type(self)(int_or_float, PREFIXES[0], self.unit_type)

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = self.parse(other)
        elif isinstance(other, (int, float)):
            other = self._as_same_unit(other)
        elif not isinstance(other, Unit):
            raise TypeError('Incomparable types {} and {}'.format(type(self), type(other)))
        # other is instance of this class too now
        if self.unit_type != other.unit_type:
            raise TypeError('Incomparable units {} and {}'.format(self.unit_type, other.unit_type))

        return cmp(self.absolute, other.absolute)

    def __float__(self):
        return self.absolute

    def __int__(self):
        return int(self.absolute)

    def __repr__(self):
        return '{}({}, {}, {})'.format(
            type(self).__name__, repr(self.number), repr(self.prefix), repr(self.unit_type))

    def __str__(self):
        return '{} {}{}'.format(self.number, self.prefix, self.unit_type)
