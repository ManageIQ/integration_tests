# -*- coding: utf-8 -*-
import attr
from cfme.utils.quote import quote
from cfme.utils.wait import wait_for
from .plugin import AppliancePlugin, AppliancePluginException


class SystemdException(AppliancePluginException):
    pass


@attr.s
class SystemdService(AppliancePlugin):
    unit_name = attr.ib()

    def _run_service_command(self, command, expected_exit_code=None, unit_name=None):
        """Wrapper around running the command and raising exception on unexpected code

        Args:
            command: string command for systemd (stop, start, restart, etc)
            expected_exit_code: the exit code to expect, otherwise raise
            unit_name: optional unit name, defaults to self.unit_name attribute

        Raises:
            SystemdException: When expected_exit_code is not matched
        """
        unit = self.unit_name if unit_name is None else unit_name
        with self.appliance.ssh_client as ssh:
            result = ssh.run_command('systemctl {} {}'.format(quote(command), quote(unit)))

        if expected_exit_code is not None and result.rc != expected_exit_code:
            # TODO: Bring back address
            msg = 'Failed to {} {}\nError: {}'.format(
                command, self.unit_name, result.output)
            self.logger.error(msg)
            raise SystemdException(msg)

        return result

    def stop(self):
        return self._run_service_command('stop', expected_exit_code=0)

    def start(self):
        return self._run_service_command('start', expected_exit_code=0)

    def restart(self):
        return self._run_service_command('restart', expected_exit_code=0)

    def enable(self):
        return self._run_service_command('enable', expected_exit_code=0)

    @property
    def running(self):
        return self._run_service_command("status").rc == 0

    def wait_for_running(self, timeout=600):
        result, wait = wait_for(lambda: self.running, num_sec=timeout,
                                fail_condition=False, delay=10)
        return result

    def daemon_reload(self):
        """Call daemon-reload, no unit name for this"""
        return self._run_service_command(command='daemon-reload',
                                         expected_exit_code=0,
                                         unit_name='')
