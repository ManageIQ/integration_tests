# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime

from miq_version import get_version
from miq_version import LATEST  # noqa: F401
from miq_version import LOWEST  # noqa: F401
from miq_version import SPTuple  # noqa: F401
from miq_version import UPSTREAM  # noqa: F401
from miq_version import Version
from miq_version import version_stream_product_mapping  # noqa: F401
from widgetastic.utils import VersionPick
from widgetastic.widget import Widget

from cfme.fixtures.pytest_store import store


def get_stream(ver):
    """Return a stream name for given Version obj or version string
    """
    ver = Version(ver)
    if ver.stream() is not None:
        return ver.stream()
    else:
        raise LookupError("no matching stream found for version {}".format(ver))


def current_version():
    """A lazy cached method to return the appliance version.

       Do not catch errors, since generally we cannot proceed with
       testing, without knowing the server version.

    """
    return store.current_appliance.version


def appliance_build_datetime():
    try:
        return store.current_appliance.build_datetime
    except Exception:
        return None


def appliance_build_date():
    try:
        return store.current_appliance.build_date
    except Exception:
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


def appliance_has_netapp():
    try:
        return store.current_appliance.has_netapp()
    except Exception:
        return None


class VersionPicker(VersionPick):
    """An adopted version of :py:class:`widgetastic.utils.VersionPick` descriptor."""

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        # in order to keep widgetastic.utils.VersionPick behaviour
        elif isinstance(obj, Widget):
            return super(VersionPicker, self).__get__(obj)
        else:
            return self.pick(obj.appliance.version)

    def pick(self, active_version=None):
        """
        Collapses an ambiguous series of objects bound to specific versions
        by interrogating the CFME Version and returning the correct item.

        Args:
            active_version: a :py:class:`miq_version.Version` instance.

        Returns:
            A value from the version dictionary.
        """
        # convert keys to Versions
        active_version = active_version or current_version()

        v_dict = {get_version(k): v for (k, v) in self.version_dict.items()}
        versions = list(v_dict.keys())
        sorted_matching_versions = sorted((v for v in versions if v <= active_version),
                                          reverse=True)
        return v_dict.get(sorted_matching_versions[0]) if sorted_matching_versions else None
