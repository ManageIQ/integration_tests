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

    def _run_service_command(self, command, expected_exit_code=None):
        with self.appliance.ssh_client as ssh:
            status, output = ssh.run_command('systemctl {} {}'.format(
                quote(command), quote(self.unit_name)))

        if expected_exit_code is not None and status != expected_exit_code:
            # TODO: Bring back address
            msg = 'Failed to {} {}\nError: {}'.format(
                command, self.unit_name, output)
            self.logger.error(msg)
            raise SystemdException(msg)

        return status

    def stop(self):
        self._run_service_command('stop', expected_exit_code=0)

    def start(self):
        self._run_service_command('start', expected_exit_code=0)

    def restart(self):
        self._run_service_command('restart', expected_exit_code=0)

    def enable(self):
        self._run_service_command('enable', expected_exit_code=0)

    @property
    def running(self):
        return self._run_service_command("status") == 0

    def wait_for_running(self, timeout=600):
        result, wait = wait_for(lambda: self.running, num_sec=timeout,
                                fail_condition=False, delay=10)
        return result
