import string
import re
from fixtures.pytest_store import store
import multimethods as mm


def get_stream(ver):
    """Return a stream name for given Version obj or version string
    """
    if isinstance(ver, basestring):
        ver = get_version(ver)
    if ver.is_in_series('5.2'):
        return 'downstream-52z'
    elif ver.is_in_series('5.3'):
        return 'downstream-53z'
    elif ver == LATEST:
        return 'upstream'
    else:
        raise Exception("Unrecognized version '{}' - no matching stream group found".format(ver))


def get_version(obj):
    """Return a LooseVersion based on obj.  For CFME, 'master' version
       means always the latest (compares as greater than any other
       version)

    """
    if isinstance(obj, Version):
        return obj
    if obj.startswith('master'):
        return LooseVersion(latest=True)
    return LooseVersion(obj)


def current_version():
    """A lazy cached method to return the appliance version.

       Do not catch errors, since generally we cannot proceed with
       testing, without knowing the server version.

    """
    return get_version(store.current_appliance.version)


def appliance_build_datetime():
    try:
        return store.current_appliance.build_datetime
    except:
        return None


def appliance_is_downstream():
    return store.current_appliance.is_downstream


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
    # convert keys to LooseVersions
    v_dict = {get_version(k): v for (k, v) in v_dict.items()}
    versions = v_dict.keys()
    sorted_matching_versions = sorted(filter(lambda v: v <= current_version(), versions),
                                      reverse=True)
    return v_dict.get(sorted_matching_versions[0]) if sorted_matching_versions else None


class Version(object):
    """Abstract base class for version numbering classes.  Just provides
    constructor (__init__) and reproducer (__repr__), because those
    seem to be the same for all version numbering classes.
    """

    def __init__(self, vstring=None):
        if vstring:
            self.parse(vstring)

    def __repr__(self):
        return "%s ('%s')" % (self.__class__.__name__, str(self))

    def __contains__(self, ver):
        """Enables to use ``in`` expression for :py:meth:`Version.is_in_series`.

        Example:
            ``"5.2.5.2" in LooseVersion("5.2") returns ``True``

        Args:
            ver: Version that should be checked if it is in series of this version. If
                :py:class:`str` provided, it will be converted to :py:class:`LooseVersion`.
        """
        if isinstance(ver, basestring):
            ver = LooseVersion(ver)
        return ver.is_in_series(self)

    def is_in_series(self, series):
        """This method checks wheter the version belongs to another version's series.

        Eg.: ``LooseVersion("5.2.5.2").is_in_series("5.2")`` returns ``True``

        Args:
            series: Another :py:class:`Version` to check against. If string provided, will be
                converted to :py:class:`LooseVersion`
        """

        if isinstance(series, basestring):
            series = get_version(series)
        if self == LATEST or series == LATEST:
            if series == self:
                return True
            else:
                return False
        return series.version == self.version[:len(series.version)]

# Taken from stdlib, just change classes to new-style and clean up
# Interface for version-number classes -- must be implemented
# by the following classes (the concrete ones -- Version should
# be treated as an abstract class).
#    __init__ (string) - create and take same action as 'parse'
#                        (string parameter is optional)
#    parse (string)    - convert a string representation to whatever
#                        internal representation is appropriate for
#                        this style of version numbering
#    __str__ (self)    - convert back to a string; should be very similar
#                        (if not identical to) the string supplied to parse
#    __repr__ (self)   - generate Python code to recreate
#                        the instance
#    __cmp__ (self, other) - compare two version numbers ('other' may
#                        be an unparsed version string, or another
#                        instance of your version class)


class StrictVersion (Version):

    """Version numbering for anal retentives and software idealists.
    Implements the standard interface for version number classes as
    described above.  A version number consists of two or three
    dot-separated numeric components, with an optional "pre-release" tag
    on the end.  The pre-release tag consists of the letter 'a' or 'b'
    followed by a number.  If the numeric components of two version
    numbers are equal, then one with a pre-release tag will always
    be deemed earlier (lesser) than one without.

    The following are valid version numbers (shown in the order that
    would be obtained by sorting according to the supplied cmp function):

        0.4       0.4.0  (these two are equivalent)
        0.4.1
        0.5a1
        0.5b3
        0.5
        0.9.6
        1.0
        1.0.4a3
        1.0.4b1
        1.0.4

    The following are examples of invalid version numbers:

        1
        2.7.2.2
        1.3.a4
        1.3pl1
        1.3c4

    The rationale for this version numbering system will be explained
    in the distutils documentation.
    """

    version_re = re.compile(r'^(\d+) \. (\d+) (\. (\d+))? ([ab](\d+))?$',
                            re.VERBOSE)

    def parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError("invalid version number '%s'" % vstring)

        (major, minor, patch, prerelease, prerelease_num) = \
            match.group(1, 2, 4, 5, 6)

        if patch:
            self.version = tuple(map(string.atoi, [major, minor, patch]))
        else:
            self.version = tuple(map(string.atoi, [major, minor]) + [0])

        if prerelease:
            self.prerelease = (prerelease[0], string.atoi(prerelease_num))
        else:
            self.prerelease = None

    def __str__(self):

        if self.version[2] == 0:
            vstring = string.join(map(str, self.version[0:2]), '.')
        else:
            vstring = string.join(map(str, self.version), '.')

        if self.prerelease:
            vstring = vstring + self.prerelease[0] + str(self.prerelease[1])

        return vstring

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = StrictVersion(other)

        compare = cmp(self.version, other.version)
        if (compare == 0):              # have to compare prerelease

            # case 1: neither has prerelease; they're equal
            # case 2: self has prerelease, other doesn't; other is greater
            # case 3: self doesn't have prerelease, other does: self is greater
            # case 4: both have prerelease: must compare them!

            if (not self.prerelease and not other.prerelease):
                return 0
            elif (self.prerelease and not other.prerelease):
                return -1
            elif (not self.prerelease and other.prerelease):
                return 1
            elif (self.prerelease and other.prerelease):
                return cmp(self.prerelease, other.prerelease)

        else:                           # numeric versions don't match --
            return compare              # prerelease stuff doesn't matter


# end class StrictVersion


# The rules according to Greg Stein:
# 1) a version number has 1 or more numbers separated by a period or by
#    sequences of letters. If only periods, then these are compared
#    left-to-right to determine an ordering.
# 2) sequences of letters are part of the tuple for comparison and are
#    compared lexicographically
# 3) recognize the numeric components may have leading zeroes
#
# The LooseVersion class below implements these rules: a version number
# string is split up into a tuple of integer and string components, and
# comparison is a simple tuple comparison.  This means that version
# numbers behave in a predictable and obvious way, but a way that might
# not necessarily be how people *want* version numbers to behave.  There
# wouldn't be a problem if people could stick to purely numeric version
# numbers: just split on period and compare the numbers as tuples.
# However, people insist on putting letters into their version numbers;
# the most common purpose seems to be:
#   - indicating a "pre-release" version
#     ('alpha', 'beta', 'a', 'b', 'pre', 'p')
#   - indicating a post-release patch ('p', 'pl', 'patch')
# but of course this can't cover all version number schemes, and there's
# no way to know what a programmer means without asking him.
#
# The problem is what to do with letters (and other non-numeric
# characters) in a version number.  The current implementation does the
# obvious and predictable thing: keep them as strings and compare
# lexically within a tuple comparison.  This has the desired effect if
# an appended letter sequence implies something "post-release":
# eg. "0.99" < "0.99pl14" < "1.0", and "5.001" < "5.001m" < "5.002".
#
# However, if letters in a version number imply a pre-release version,
# the "obvious" thing isn't correct.  Eg. you would expect that
# "1.5.1" < "1.5.2a2" < "1.5.2", but under the tuple/lexical comparison
# implemented here, this just isn't so.
#
# Two possible solutions come to mind.  The first is to tie the
# comparison algorithm to a particular set of semantic rules, as has
# been done in the StrictVersion class above.  This works great as long
# as everyone can go along with bondage and discipline.  Hopefully a
# (large) subset of Python module programmers will agree that the
# particular flavour of bondage and discipline provided by StrictVersion
# provides enough benefit to be worth using, and will submit their
# version numbering scheme to its domination.  The free-thinking
# anarchists in the lot will never give in, though, and something needs
# to be done to accommodate them.
#
# Perhaps a "moderately strict" version class could be implemented that
# lets almost anything slide (syntactically), and makes some heuristic
# assumptions about non-digits in version number strings.  This could
# sink into special-case-hell, though; if I was as talented and
# idiosyncratic as Larry Wall, I'd go ahead and implement a class that
# somehow knows that "1.2.1" < "1.2.2a2" < "1.2.2" < "1.2.2pl3", and is
# just as happy dealing with things like "2g6" and "1.13++".  I don't
# think I'm smart enough to do it right though.
#
# In any case, I've coded the test suite for this module (see
# ../test/test_version.py) specifically to fail on things like comparing
# "1.2a2" and "1.2".  That's not because the *code* is doing anything
# wrong, it's because the simple, obvious design doesn't match my
# complicated, hairy expectations for real-world version numbers.  It
# would be a snap to fix the test suite to say, "Yep, LooseVersion does
# the Right Thing" (ie. the code matches the conception).  But I'd rather
# have a conception that matches common notions about version numbers.

class LooseVersion (Version):

    """Version numbering for anarchists and software realists.
    Implements the standard interface for version number classes as
    described above.  A version number consists of a series of numbers,
    separated by either periods or strings of letters.  When comparing
    version numbers, the numeric components will be compared
    numerically, and the alphabetic components lexically.  The following
    are all valid version numbers, in no particular order:

        1.5.1
        1.5.2b2
        161
        3.10a
        8.02
        3.4j
        1996.07.12
        3.2.pl0
        3.1.1.6
        2g6
        11g
        0.960923
        2.2beta29
        1.13++
        5.5.kw
        2.0b1pl0

    In fact, there is no such thing as an invalid version number under
    this scheme; the rules for comparison are simple and predictable,
    but may not always give the results you want (for some definition
    of "want").

    Note: 'latest' and 'oldest' are special cases, latest = (greater
    than everything else except itself). oldest = (less than
    everything else except itself.)

    """

    component_re = re.compile(r'(\d+ | [a-z]+ | \.)', re.VERBOSE)

    def __init__(self, vstring=None, latest=False, oldest=False):
        self.version = None
        if latest and oldest:
            raise ValueError('Cannot be both latest and oldest')
        if latest:
            self._special = 1
        elif oldest or vstring == 'default':
            self._special = -1
        else:
            self._special = 0
        if vstring and not self._special:
            self.parse(vstring)

    def parse(self, vstring):
        # I've given up on thinking I can reconstruct the version string
        # from the parsed tuple -- so I just store the string here for
        # use by __str__
        self.vstring = vstring
        components = filter(lambda x: x and x != '.',
                            self.component_re.split(vstring))
        for i in range(len(components)):
            try:
                components[i] = int(components[i])
            except ValueError:
                pass

        self.version = components

    def __str__(self):
        if self._special == -1:
            return 'oldest'
        elif self._special == 1:
            return 'latest'
        else:
            return self.vstring

    def __repr__(self):
        return "LooseVersion ('%s')" % str(self)

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = LooseVersion(other)
        special_cmp = cmp(self._special, other._special)
        if special_cmp == 0:
            return cmp(self.version, other.version)
        else:
            return special_cmp

# end class LooseVersion

LOWEST = LooseVersion(oldest=True)
LATEST = LooseVersion(latest=True)


# Compare Versions using > for dispatch
@mm.is_a.method((LooseVersion, LooseVersion))
def _is_a_loose(x, y):
    return x >= y


@mm.is_a.method((str, LooseVersion))
def _is_a_slv(x, y):
    return mm.is_a(LooseVersion(x), y)


@mm.is_a.method((LooseVersion, str))
def _is_a_lvs(x, y):
    return mm.is_a(x, LooseVersion(y))
