# -*- coding: utf-8 -*-
"""This module provides a client class for the SNMP listener

It automatically detects whether the listener is installed and if it is not, it installs it
automatically.
"""
import requests
from subprocess import Popen, PIPE

from utils import lazycache


class SNMPClient(object):
    """Class for accessing the SNMP traps stored in the appliance listener

    Args:
        addr: Address of the appliance
        port: port to contact, 8765 by default
    """
    def __init__(self, addr, port=8765):
        self._addr = addr
        self._port = port

    @lazycache
    def setup(self):
        """Checks for presence of the listener on the appliance. If it is not present, it then
        installs it."""
        try:
            requests.get("http://{}:{}/traps".format(self._addr, self._port), timeout=5)
            return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return self.install()

    def install(self):
        """Install the listener to the appliance"""
        install = Popen(["python", "scripts/install_snmp_listener.py", self._addr], stdout=PIPE)
        install.communicate()
        while install.poll() is None:
            install.communicate()
        return True

    def get_all(self):
        """Get all traps that were caught.

        Returns: List of dicts.
        """
        self.setup
        rdata = requests.get("http://{}:{}/traps".format(self._addr, self._port)).json()
        status, content = rdata["status"], rdata["content"]
        if status != 200:
            raise Exception("SNMP Client exception {}: {}".format(status, content))
        return content
