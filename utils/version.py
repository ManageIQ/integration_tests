# -*- coding: utf-8 -*-
import re
from cached_property import cached_property
from collections import namedtuple
from datetime import date, datetime

import multimethods as mm

from fixtures.pytest_store import store


def get_product_version(ver):
    """Return product version for given Version obj or version string
    """
    ver = Version(ver)
    if ver.product_version() is not None:
        return ver.product_version()
    else:
        raise LookupError("no matching product version found for version {}".format(ver))


def get_stream(ver):
    """Return a stream name for given Version obj or version string
    """
    ver = Version(ver)
    if ver.stream() is not None:
        return ver.stream()
    else:
        raise LookupError("no matching stream found for version {}".format(ver))


def current_stream():
    return get_stream(store.current_appliance.version)


def get_version(obj=None):
    """
    Return a Version based on obj.  For CFME, 'master' version
    means always the latest (compares as greater than any other version)

    If obj is None, the version will be retrieved from the current appliance

    """
    if isinstance(obj, Version):
        return obj
    if obj.startswith('master'):
        return Version.latest()
    return Version(obj)


def current_version():
    """A lazy cached method to return the appliance version.

       Do not catch errors, since generally we cannot proceed with
       testing, without knowing the server version.

    """
    return store.current_appliance.version


def appliance_build_datetime():
    try:
        return store.current_appliance.build_datetime
    except:
        return None


def appliance_build_date():
    try:
        return store.current_appliance.build_date
    except:
        return None


def appliance_is_downstream():
    return store.current_appliance.is_downstream


def parsedate(o):
    if isinstance(o, date):
        return o
    elif isinstance(o, datetime):
        return o.date()
    else:
        # 1234-12-13
        return date(*[int(x) for x in str(o).split("-", 2)])


def before_date_or_version(date=None, version=None):
    """Function for deciding based on the build date and version.

    Usage:

        * If both date and version are set, then two things can happen. If the appliance is
            downstream, both date and version are checked, otherwise only the date.
        * If only date is set, then only date is checked.
        * if only version is set, then it checks the version if the appliance is downstream,
            otherwise it returns ``False``

    The checks are in form ``appliance_build_date() < date`` and ``current_version() < version``.
    Therefore when used in ``if`` statement, the truthy value signalizes 'older' version and falsy
    signalizes 'newer' version.
    """
    if date is not None:
        date = parsedate(date)
    if date is not None and version is not None:
        if not appliance_is_downstream():
            return appliance_build_date() < date
        else:
            return appliance_build_date() < date and current_version() < version
    elif date is not None and version is None:
        return appliance_build_date() < date
    elif date is None and version is not None:
        if not appliance_is_downstream():
            return False
        return current_version() < version
    else:
        raise TypeError("You have to pass either date or version, or both!")


def since_date_or_version(*args, **kwargs):
    """Opposite of :py:func:`before_date_or_version`"""
    return not before_date_or_version(*args, **kwargs)


def appliance_has_netapp():
    try:
        return store.current_appliance.has_netapp()
    except:
        return None


def product_version_dispatch(*_args, **_kwargs):
    """Dispatch function for use in multimethods that just ignores
       arguments and dispatches on the current product version."""
    return current_version()


def dependent(default_function):
    m = mm.MultiMethod(default_function.__name__, product_version_dispatch)
    m.add_method(mm.Default, default_function)
    mm._copy_attrs(default_function, m)
    return m


def pick(v_dict):
    """
    Collapses an ambiguous series of objects bound to specific versions
    by interrogating the CFME Version and returning the correct item.
    """
    # convert keys to Versions
    v_dict = {get_version(k): v for (k, v) in v_dict.items()}
    versions = v_dict.keys()
    sorted_matching_versions = sorted(filter(lambda v: v <= current_version(), versions),
                                      reverse=True)
    return v_dict.get(sorted_matching_versions[0]) if sorted_matching_versions else None


class Version(object):
    """Version class based on distutil.version.LooseVersion"""
    SUFFIXES = ('nightly', 'pre', 'alpha', 'beta', 'rc')
    SUFFIXES_STR = "|".join(r'-{}(?:\d+(?:\.\d+)?)?'.format(suff) for suff in SUFFIXES)
    component_re = re.compile(r'(?:\s*(\d+|[a-z]+|\.|(?:{})+$))'.format(SUFFIXES_STR))
    suffix_item_re = re.compile(r'^([^0-9]+)(\d+(?:\.\d+)?)?$')

    def __init__(self, vstring):
        self.parse(vstring)

    def parse(self, vstring):
        if vstring is None:
            raise ValueError('Version string cannot be None')
        elif isinstance(vstring, (list, tuple)):
            vstring = ".".join(map(str, vstring))
        elif vstring:
            vstring = str(vstring).strip()
        if vstring in ('master', 'latest', 'upstream'):
            vstring = 'master'
        if vstring == 'darga-3':
            vstring = '5.6.1'
        if vstring == 'darga-4.1':
            vstring = '5.6.2'

        components = filter(lambda x: x and x != '.',
                            self.component_re.findall(vstring))
        # Check if we have a version suffix which denotes pre-release
        if components and components[-1].startswith('-'):
            self.suffix = components[-1][1:].split('-')    # Chop off the -
            components = components[:-1]
        else:
            self.suffix = None
        for i in range(len(components)):
            try:
                components[i] = int(components[i])
            except ValueError:
                pass

        self.vstring = vstring
        self.version = components

    @cached_property
    def normalized_suffix(self):
        """Turns the string suffixes to numbers. Creates a list of tuples.

        The list of tuples is consisting of 2-tuples, the first value says the position of the
        suffix in the list and the second number the numeric value of an eventual numeric suffix.

        If the numeric suffix is not present in a field, then the value is 0
        """
        numberized = []
        if self.suffix is None:
            return numberized
        for item in self.suffix:
            suff_t, suff_ver = self.suffix_item_re.match(item).groups()
            if suff_ver is None or len(suff_ver) == 0:
                suff_ver = 0.0
            else:
                suff_ver = float(suff_ver)
            suff_t = self.SUFFIXES.index(suff_t)
            numberized.append((suff_t, suff_ver))
        return numberized

    @classmethod
    def latest(cls):
        try:
            return cls._latest
        except AttributeError:
            cls._latest = cls('latest')
            return cls._latest

    @classmethod
    def lowest(cls):
        try:
            return cls._lowest
        except AttributeError:
            cls._lowest = cls('lowest')
            return cls._lowest

    def __str__(self):
        return self.vstring

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, repr(self.vstring))

    def __cmp__(self, other):
        try:
            if not isinstance(other, type(self)):
                other = Version(other)
        except:
            raise ValueError('Cannot compare Version to {}'.format(type(other).__name__))

        if self == other:
            return 0
        elif self == self.latest() or other == self.lowest():
            return 1
        elif self == self.lowest() or other == self.latest():
            return -1
        else:
            result = cmp(self.version, other.version)
            if result != 0:
                return result
            # Use suffixes to decide
            if self.suffix is None and other.suffix is None:
                # No suffix, the same
                return 0
            elif self.suffix is None:
                # This does not have suffix but the other does so this is "newer"
                return 1
            elif other.suffix is None:
                # This one does have suffix and the other does not so this one is older
                return -1
            else:
                # Both have suffixes, so do some math
                return cmp(self.normalized_suffix, other.normalized_suffix)

    def __eq__(self, other):
        try:
            if not isinstance(other, type(self)):
                other = Version(other)
            return (
                self.version == other.version and self.normalized_suffix == other.normalized_suffix)
        except:
            return False

    def __contains__(self, ver):
        """Enables to use ``in`` expression for :py:meth:`Version.is_in_series`.

        Example:
            ``"5.5.5.2" in Version("5.5") returns ``True``

        Args:
            ver: Version that should be checked if it is in series of this version. If
                :py:class:`str` provided, it will be converted to :py:class:`Version`.
        """
        try:
            return Version(ver).is_in_series(self)
        except:
            return False

    def is_in_series(self, series):
        """This method checks whether the version belongs to another version's series.

        Eg.: ``Version("5.5.5.2").is_in_series("5.5")`` returns ``True``

        Args:
            series: Another :py:class:`Version` to check against. If string provided, will be
                converted to :py:class:`Version`
        """

        if not isinstance(series, Version):
            series = get_version(series)
        if self in {self.lowest(), self.latest()}:
            if series == self:
                return True
            else:
                return False
        return series.version == self.version[:len(series.version)]

    def series(self, n=2):
        return ".".join(self.vstring.split(".")[:n])

    def stream(self):
        for v, spt in version_stream_product_mapping.items():
            if self.is_in_series(v):
                return spt.stream

    def product_version(self):
        for v, spt in version_stream_product_mapping.items():
            if self.is_in_series(v):
                return spt.product_version

LOWEST = Version.lowest()
LATEST = Version.latest()
UPSTREAM = LATEST

SPTuple = namedtuple('StreamProductTuple', ['stream', 'product_version'])

# Maps stream and product version to each app version
version_stream_product_mapping = {
    '5.2': SPTuple('downstream-52z', '3.0'),
    '5.3': SPTuple('downstream-53z', '3.1'),
    '5.4': SPTuple('downstream-54z', '3.2'),
    '5.5': SPTuple('downstream-55z', '4.0'),
    '5.6': SPTuple('downstream-56z', '4.1'),
    '5.7': SPTuple('downstream-57z', '4.2'),
    LATEST: SPTuple('upstream', 'master')
}


# Compare Versions using > for dispatch
@mm.is_a.method((Version, Version))
def _is_a_loose(x, y):
    return x >= y


@mm.is_a.method((str, Version))
def _is_a_slv(x, y):
    return mm.is_a(Version(x), y)


@mm.is_a.method((Version, str))
def _is_a_lvs(x, y):
    return mm.is_a(x, Version(y))
