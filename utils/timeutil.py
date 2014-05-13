# -*- coding: utf-8 -*-

""" This module should contain all things associated with time or date that can be shared.

"""

from datetime import datetime as _datetime
import time


class parsetime(_datetime):
    """ Modified class with loaders for our datetime formats.

    """
    _american_with_utc_format = "%m/%d/%y %H:%M:%S UTC"
    _american_date_only_format = "%m/%d/%y"
    _iso_date_only_format = "%Y-%m-%d"
    _request_format = "%Y-%m-%d-%H-%M-%S"

    @classmethod
    def _parse(self, fmt, time_string):
        return self.fromtimestamp(
            time.mktime(
                time.strptime(
                    time_string,
                    fmt
                )
            )
        )

    @classmethod
    def from_american_with_utc(self, time_string):
        """ Convert the string representation of the time into parsetime()

        CFME's format here is 'mm/dd/yy hh:mm:ss UTC'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return self._parse(self._american_with_utc_format, time_string)

    def to_american_with_utc(self):
        """ Convert the this object to string representation in american utc format.

        CFME's format here is 'mm/dd/yy hh:mm:ss UTC'

        Returns: :py:class`str` object
        """
        return self.strftime(self._american_with_utc_format)

    @classmethod
    def from_american_date_only(self, time_string):
        """ Convert the string representation of the time into parsetime()

        CFME's format here is 'mm/dd/yy'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return self._parse(self._american_date_only_format, time_string)

    def to_american_date_only(self):
        """ Convert the this object to string representation in american date only format.

        CFME's format here is 'mm/dd/yy'

        Returns: :py:class`str` object
        """
        return self.strftime(self._american_date_only_format)

    @classmethod
    def from_iso_date(self, time_string):
        """ Convert the string representation of the time into parsetime()

        Format here is 'YYYY-MM-DD'

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return self._parse(self._iso_date_only_format, time_string)

    def to_iso_date(self):
        """ Convert the this object to string representation in ISO format.

        Format here is 'YYYY-MM-DD'

        Returns: :py:class`str` object
        """
        return self.strftime(self._iso_date_only_format)

    @classmethod
    def from_request_format(self, time_string):
        """ Convert the string representation of the time into parsetime()

        Format here is 'YYYY-MM-DD-HH-MM-SS'. Used for transmitting data over http

        Args:
            time_string: String with time to parse
        Returns: :py:class`utils.timeutil.datetime()` object
        """
        return self._parse(self._request_format, time_string)

    def to_request_format(self):
        """ Convert the this object to string representation in http request.

        Format here is 'YYYY-MM-DD-HH-MM-SS'

        Returns: :py:class`str` object
        """
        return self.strftime(self._request_format)
