# -*- coding: utf-8 -*-

""" This module should contain all things associated with time or date that can be shared.

"""

from datetime import datetime as _datetime
import time
import tzlocal

local_tz = tzlocal.get_localzone()


class parsetime(_datetime):  # NOQA
    """ Modified class with loaders for our datetime formats.

    """
    _american_with_utc_format = "%m/%d/%y %H:%M:%S UTC"
    _iso_with_utc_format = "%Y-%m-%d %H:%M:%S UTC"
    _american_minutes = "%m/%d/%y %H:%M"
    _american_minutes_wit_utc = "%m/%d/%y %H:%M UTC"
    _american_date_only_format = "%m/%d/%y"
    _iso_date_only_format = "%Y-%m-%d"
    _request_format = "%Y-%m-%d-%H-%M-%S"

    @classmethod
    def _parse(cls, fmt, time_string):
        return cls.fromtimestamp(
            time.mktime(
                time.strptime(
                    time_string,
                    fmt
                )
            )
        )

    @classmethod
    def from_american_with_utc(cls, time_string):
        """ Convert the string representation of the time into parsetime()

        CFME's format here is 'mm/dd/yy hh:mm:ss UTC'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return cls._parse(cls._american_with_utc_format, time_string)

    def to_american_with_utc(self):
        """ Convert the this object to string representation in american with UTC.

        CFME's format here is 'mm/dd/yy hh:mm:ss UTC'

        Returns: :py:class`str` object
        """
        return self.strftime(self._american_with_utc_format)

    @classmethod
    def from_iso_with_utc(cls, time_string):
        """ Convert the string representation of the time into parsetime()

        CFME's format here is 'mm-dd-yy hh:mm:ss UTC'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return cls._parse(cls._iso_with_utc_format, time_string)

    def to_iso_with_utc(self):
        """ Convert the this object to string representation in american with UTC.

        CFME's format here is 'mm-dd-yy hh:mm:ss UTC'

        Returns: :py:class`str` object
        """
        return self.strftime(self._iso_with_utc_format)

    @classmethod
    def from_american_minutes(cls, time_string):
        """ Convert the string representation of the time into parsetime()

        CFME's format here is 'mm/dd/yy hh:mm'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return cls._parse(cls._american_minutes, time_string)

    def to_american_minutes(self):
        """ Convert the this object to string representation in american with just minutes.

        CFME's format here is 'mm/dd/yy hh:mm'

        Returns: :py:class`str` object
        """
        return self.strftime(self._american_minutes)

    @classmethod
    def from_american_minutes_with_utc(cls, time_string):
        """ Convert the string representation of the time into parsetime()

        CFME's format here is 'mm/dd/yy hh:mm UTC'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return cls._parse(cls._american_minutes_wit_utc, time_string)

    def to_american_minutes_with_utc(self):
        """ Convert the this object to string representation in american with just minutes.

        CFME's format here is 'mm/dd/yy hh:mm'

        Returns: :py:class`str` object
        """
        return self.strftime(self._american_minutes_wit_utc)

    @classmethod
    def from_american_date_only(cls, time_string):
        """ Convert the string representation of the time into parsetime()

        CFME's format here is 'mm/dd/yy'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return cls._parse(cls._american_date_only_format, time_string)

    def to_american_date_only(self):
        """ Convert the this object to string representation in american date only format.

        CFME's format here is 'mm/dd/yy'

        Returns: :py:class`str` object
        """
        return self.strftime(self._american_date_only_format)

    @classmethod
    def from_iso_date(cls, time_string):
        """ Convert the string representation of the time into parsetime()

        Format here is 'YYYY-MM-DD'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return cls._parse(cls._iso_date_only_format, time_string)

    def to_iso_date(self):
        """ Convert the this object to string representation in ISO format.

        Format here is 'YYYY-MM-DD'

        Returns: :py:class`str` object
        """
        return self.strftime(self._iso_date_only_format)

    @classmethod
    def from_request_format(cls, time_string):
        """ Convert the string representation of the time into parsetime()

        Format here is 'YYYY-MM-DD-HH-MM-SS'. Used for transmitting data over http

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return cls._parse(cls._request_format, time_string)

    def to_request_format(self):
        """ Convert the this object to string representation in http request.

        Format here is 'YYYY-MM-DD-HH-MM-SS'

        Returns: :py:class`str` object
        """
        return self.strftime(self._request_format)


def nice_seconds(t_s):
    """Return nicer representation of seconds"""
    if t_s < 60.0:
        return "{0:.2f}s".format(t_s)
    minutes = 1
    while t_s - (minutes * 60.0) >= 60.0:
        minutes += 1
    seconds = t_s - (minutes * 60)
    if minutes < 60.0:
        return "{0}m{1:.2f}s".format(minutes, seconds)
    # Hours
    hours = 1
    while minutes - (hours * 60.0) >= 60.0:
        hours += 1
    minutes = minutes - (hours * 60)
    if hours < 24.0:
        return "{0}h{1}m{2:.2f}s".format(hours, minutes, seconds)
    # Days
    days = 1
    while hours - (days * 24.0) >= 24.0:
        days += 1
    hours = hours - (days * 24)
    if days < 7.0:
        return "{0}d{1}h{2}m{3:.2f}s".format(days, hours, minutes, seconds)
    # Weeks
    weeks = 1
    while days - (weeks * 7.0) >= 7.0:
        weeks += 1
    days = days - (weeks * 7)
    return "{0}w{1}d{2}h{3}m{4:.2f}s".format(weeks, days, hours, minutes, seconds)
