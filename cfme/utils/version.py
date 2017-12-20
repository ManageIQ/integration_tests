# -*- coding: utf-8 -*-
from datetime import date, datetime

import multimethods as mm
from miq_version import (  # noqa
    Version, LOWEST, LATEST, UPSTREAM, SPTuple, get_version,
    version_stream_product_mapping
)

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


def pick(v_dict, active_version=None):
    """
    Collapses an ambiguous series of objects bound to specific versions
    by interrogating the CFME Version and returning the correct item.
    """
    # convert keys to Versions
    active_version = active_version or current_version()

    v_dict = {get_version(k): v for (k, v) in v_dict.items()}
    versions = v_dict.keys()
    sorted_matching_versions = sorted((v for v in versions if v <= active_version),
                                      reverse=True)
    return v_dict.get(sorted_matching_versions[0]) if sorted_matching_versions else None


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
