# -*- coding: utf-8 -*-

from utils.timeutil import parsetime
import requests


class SMTPCollectorClient(object):
    """Client for smtp_collector.py script

    Args:
        host: Host where collector runs (Default: localhost)
        port: Port where the collector query interface listens (Default: 1026)

    """
    def __init__(self, host="localhost", port=1026):
        self._host = host
        self._port = port

    def _query(self, method, path, **params):
        return method("http://{}:{}/{}".format(self._host, self._port, path), params=params)

    def clear_database(self):
        """Clear the database in collector

        Returns: :py:class:`bool`
        """
        return self._query(requests.delete, "messages").json()

    def set_test_name(self, test_name):
        """Set the test name for folder name in the collector.

        Args:
            test_name: Name to set
        Returns: :py:class:`bool` with result.
        """
        return self._query(requests.get, "set_test_name", test_name=test_name).json()

    def get_emails(self, **filter):
        """Get emails. Eventually apply filtering on SQLite level

        Time variables can be passed as instances of :py:class:`utils.timeutil.parsetime`. That
        carries out the necessary conversion automatically.

        _like args - see SQLite's LIKE operator syntax

        Keywords:
            from_address: E-mail matches.
            to_address: E-mail matches.
            subject: Subject matches exactly.
            subject_like: Subject is LIKE.
            time_from: E-mails arrived since this time.
            time_to: E-mail arrived before this time.
            text: Text matches exactly.
            text_like: Text is LIKE.

        Returns: List of dicts with e-mails matching the criteria.
        """
        if filter.get("time_from", None) is not None:
            if isinstance(filter["time_from"], parsetime):
                filter["time_from"] = filter["time_from"].to_request_format()
        if filter.get("time_to", None) is not None:
            if isinstance(filter["time_to"], parsetime):
                filter["time_to"] = filter["time_to"].to_request_format()
        return self._query(requests.get, "messages", **filter).json()

    def get_html_report(self):
        return self._query(requests.get, "messages.html").text.strip()
