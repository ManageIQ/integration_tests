# -*- coding: utf-8 -*-
"""This module provides a client class for the SNMP listener

It automatically detects whether the listener is installed and if it is not, it installs it
automatically.
"""
from __future__ import unicode_literals
import requests
from subprocess import Popen, PIPE


class SNMPClient(object):
    """Class for accessing the SNMP traps stored in the appliance listener

    Args:
        addr: Address of the appliance
        port: port to contact, 8765 by default
    """
    def __init__(self, addr, port=8765):
        self._addr = addr
        self._port = port

    def check_installed(self):
        try:
            requests.get("http://{}:{}/traps".format(self._addr, self._port), timeout=5)
            return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return False

    def install(self):
        """Install the listener to the appliance"""
        install = Popen(["python", "scripts/install_snmp_listener.py", self._addr], stdout=PIPE)
        install.communicate()
        while install.poll() is None:
            install.communicate()
        return True

    def ensure_installed(self):
        if not self.check_installed():
            return self.install()

    def get_all(self):
        """Get all traps that were caught.

        Returns: List of dicts.
        """
        self.ensure_installed()
        rdata = requests.get("http://{}:{}/traps".format(self._addr, self._port)).json()
        status, content = rdata["status"], rdata["content"]
        if status != 200:
            raise Exception("SNMP Client exception {}: {}".format(status, content))
        return content

    def flush(self):
        """Deletes all traps from the listener."""
        self.ensure_installed()
        requests.get("http://{}:{}/flush".format(self._addr, self._port))
