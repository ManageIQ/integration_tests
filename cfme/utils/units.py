import functools
import re
from collections import namedtuple
from locale import atof
from locale import LC_NUMERIC
from locale import setlocale


BIN_FACTOR = 1024
DEC_FACTOR = 1000
PREFIXES = ['', 'K', 'M', 'G', 'T', 'P']
BIN_FACTORS = {prefix: BIN_FACTOR**i for i, prefix in enumerate(PREFIXES)}
DEC_FACTORS = {prefix: DEC_FACTOR**i for i, prefix in enumerate(PREFIXES)}

BIN_UNITS = ['Byte', 'Bytes', 'B', 'b', 'Bps']
DEC_UNITS = ['Hz']
UNITS = BIN_UNITS + DEC_UNITS

CUR_UNITS = ['$']

EQUAL_UNITS = {
    'B': ('Byte', 'Bytes')
}

# Sanity check
for target_unit, units in EQUAL_UNITS.items():
    assert target_unit in UNITS
    for unit in units:
        assert unit in UNITS

CUR_GRP = r'({})'.format(re.escape('|'.join(CUR_UNITS)))
NUM_GRP = r'([\d\.,]+)'
PREFIX_GRP = r'({})'.format('|'.join(PREFIXES))
UNIT_GRP = r'({})'.format('|'.join(UNITS))
SPACES = r'\s*'

NUM_REGEX = re.compile(f'^{SPACES}{NUM_GRP}{SPACES}$')
CUR_REGEX = re.compile(f'^{SPACES}{CUR_GRP}{SPACES}{NUM_GRP}{SPACES}$')
UNIT_REGEX = re.compile(f'^{SPACES}{NUM_GRP}{SPACES}{PREFIX_GRP}?{UNIT_GRP}{SPACES}$')

setlocale(LC_NUMERIC, '')


@functools.total_ordering
class Unit:
    """This class serves for simple comparison of numbers that have units.

    Imagine you pull the :py:class:`str` value '2 GB' from the UI. Calling ``Unit.parse('2 GB')``
    returns an instance of :py:class:`Unit`, which is comparable.

    You can compare two :py:class:`Unit` instances or you can compare :py:class:`Unit` with
    :py:class:`int`, :py:class:`float` or any :py:class:`str` as long as it can go through the
    :py:meth:`Unit.parse`.

    If you compare :py:class:`Unit` only (or a string that gets subsequently parsed), it also takes
    the kind of the unit it is. You cannot compare incommensurable units, e.g., Bytes and Hz. When
    comparing two instances, the absolute magnitude in the base unit is first calculated, and then
    the two absolute magnitudes are compared.

    If you compare with a number, the number is assumed to be in the base unit, e.g.,

      Unit.parse('2 GB') == 2*1024*1024*1024

    returns True.
    """
    __slots__ = ['number', 'prefix', 'unit_type']

    @classmethod
    def parse(cls, s):
        s = str(s)
        unit_type = ''
        number = ''
        prefix = ''
        # TODO: use walrus operator after upgrade to Python 3.8
        match = CUR_REGEX.match(s)
        if match:
            unit_type, number = match.groups()
            return cls(atof(number), prefix, unit_type)

        match = UNIT_REGEX.match(s)
        if match:
            number, prefix, unit_type = match.groups()
            # Check if it is just a different name for a unit.
            for target_unit, units in EQUAL_UNITS.items():
                if unit_type in units:
                    unit_type = target_unit
            return cls(atof(number), prefix, unit_type)

        match = NUM_REGEX.match(s)
        if match:
            number, = match.groups()
            return cls(atof(number), prefix, unit_type)

        raise ValueError(f"{s!r} could not be parsed.")

    def __init__(self, number, prefix, unit_type):
        self.number = float(number)
        self.prefix = prefix
        self.unit_type = unit_type

    @property
    def absolute(self):
        if self.prefix:
            factors = BIN_FACTORS if self.unit_type in BIN_UNITS else DEC_FACTORS
            return self.number * factors[self.prefix]
        else:
            return self.number

    def _as_same_unit(self, int_or_float):
        return type(self)(int_or_float, PREFIXES[0], self.unit_type)

    def _cast_other_to_same(self, other):
        if isinstance(other, str):
            other = self.parse(other)
        elif isinstance(other, (int, float)):
            other = self._as_same_unit(other)
        elif not isinstance(other, Unit):
            raise TypeError('Incomparable types {} and {}'.format(type(self), type(other)))
        # other is now an instance of Unit too
        if self.unit_type != other.unit_type:
            raise TypeError(f'Incomparable units {self.unit_type} and {other.unit_type}')
        return other

    def __eq__(self, other):
        other = self._cast_other_to_same(other)
        return self.absolute == other.absolute

    def __lt__(self, other):
        other = self._cast_other_to_same(other)
        return self.absolute < other.absolute

    def __float__(self):
        return self.absolute

    def __int__(self):
        return int(self.absolute)

    def __repr__(self):
        return '{}({}, {}, {})'.format(
            type(self).__name__, repr(self.number), repr(self.prefix), repr(self.unit_type))

    def __str__(self):
        if not self.unit_type:
            return str(self.number)
        elif self.unit_type in CUR_UNITS:
            return f'{self.unit_type}{self.number}'
        else:
            return f'{self.number} {self.prefix}{self.unit_type}'


# Chargeback header names: used in chargeback tests for convenience
_HeaderNames = namedtuple('_HeaderNames', ['rate_name', 'metric_name', 'cost_name'])
CHARGEBACK_HEADER_NAMES = {
    'Fixed1': _HeaderNames('Fixed Compute Cost 1', 'Fixed Compute Metric', 'Fixed Compute Cost 1'),
    'Fixed2': _HeaderNames('Fixed Compute Cost 2', 'Fixed Compute Metric', 'Fixed Compute Cost 2'),
    'CpuCores': _HeaderNames('Used CPU Cores', 'Cpu Cores Used Metric', 'Cpu Cores Used Cost'),
    'Memory': _HeaderNames('Used Memory', 'Memory Used', 'Memory Used Cost'),
    'Network': _HeaderNames('Used Network I/O', 'Network I/O Used', 'Network I/O Used Cost'),
}


def parse_number(str_):
    """parsing only the numbers in the string"""
    return float(''.join(re.findall(r'[\d\.]+', str_)) or 0)
