import os
from contextlib import contextmanager

from cfme.utils.conf import credentials
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


class RemoteFile(object):
    """This class is useful in ansible testing to validate file created with ansible playbook"""

    def __init__(self, hostname, username=None, password=None, file_path="~/test_ansible_file"):
        self.hostname = hostname
        self.username = username or credentials["ssh"]["username"]
        self.password = password or credentials["ssh"]["password"]
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.directory = os.path.dirname(file_path)

    @property
    def is_available(self):
        """Check file available or not"""
        with SSHClient(hostname=self.hostname, username=self.username, password=self.password) as c:
            files = c.run_command(f"ls {self.directory}").output
        return self.file_name in files

    def clean(self):
        """Clean file from remote host"""
        if self.is_available:
            with SSHClient(
                hostname=self.hostname, username=self.username, password=self.password
            ) as c:
                c.run_command(f"rm -rf {self.file_path}")
            assert not self.is_available

    @contextmanager
    def validate(self, wait=240):
        self.clean()
        yield
        try:
            wait_for(
                lambda: self.is_available,
                delay=5,
                timeout=wait,
                message=f"waiting for {self.file_name}",
            )
        except TimedOutError:
            import pytest
            pytest.fail(f"Fail to create file '{self.file_name}' on host '{self.hostname}'")
