# -*- coding: utf-8 -*-
import attr

from cfme.utils.appliance.plugin import AppliancePlugin
from cfme.utils.appliance.plugin import AppliancePluginException
from cfme.utils.log import logger_wrap
from cfme.utils.quote import quote
from cfme.utils.wait import wait_for


class SystemdException(AppliancePluginException):
    pass


@attr.s
class SystemdService(AppliancePlugin):
    unit_name = attr.ib(type=str)

    @logger_wrap('SystemdService command runner: {}')
    def _run_service_command(
        self,
        command,
        expected_exit_code=None,
        unit_name=None,
        log_callback=None
    ):
        """Wrapper around running the command and raising exception on unexpected code

        Args:
            command: string command for systemd (stop, start, restart, etc)
            expected_exit_code: the exit code to expect, otherwise raise
            unit_name: optional unit name, defaults to self.unit_name attribute
            log_callback: logger to log against

        Raises:
            SystemdException: When expected_exit_code is not matched
        """
        unit = self.unit_name if unit_name is None else unit_name
        with self.appliance.ssh_client as ssh:
            cmd = 'systemctl {} {}'.format(quote(command), quote(unit))
            log_callback('Running {}'.format(cmd))
            result = ssh.run_command(cmd,
                                     container=self.appliance.ansible_pod_name)

        if expected_exit_code is not None and result.rc != expected_exit_code:
            # TODO: Bring back address
            msg = 'Failed to {} {}\nError: {}'.format(
                command, self.unit_name, result.output)
            if log_callback:
                log_callback(msg)
            else:
                self.logger.error(msg)
            raise SystemdException(msg)
        return result

    def stop(self, log_callback=None):
        return self._run_service_command(
            'stop',
            expected_exit_code=0,
            log_callback=log_callback
        )

    def start(self, log_callback=None):
        return self._run_service_command(
            'start',
            expected_exit_code=0,
            log_callback=log_callback
        )

    def restart(self, log_callback=None):
        return self._run_service_command(
            'restart',
            expected_exit_code=0,
            log_callback=log_callback
        )

    def reload(self, log_callback=None):
        return self._run_service_command(
            'reload',
            expected_exit_code=0,
            log_callback=log_callback
        )

    def enable(self, log_callback=None):
        return self._run_service_command(
            'enable',
            expected_exit_code=0,
            log_callback=log_callback
        )

    @property
    def enabled(self):
        return self._run_service_command('is-enabled').rc == 0

    @property
    def is_active(self):
        return self._run_service_command('is-active').rc == 0

    @property
    def running(self):
        return self._run_service_command("status").rc == 0

    def wait_for_running(self, timeout=600):
        result, wait = wait_for(
            lambda: self.running,
            num_sec=timeout,
            fail_condition=False,
            delay=5,
        )
        return result

    def daemon_reload(self, log_callback=None):
        """Call daemon-reload, no unit name for this"""
        return self._run_service_command(
            command='daemon-reload',
            expected_exit_code=0,
            unit_name='',
            log_callback=log_callback
        )
