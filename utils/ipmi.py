from __future__ import unicode_literals
import subprocess
from utils.wait import wait_for


class IPMI():
    """ Utility to access IPMI via CLI.

    The IPMI utility uses the ``ipmitool`` package to access the remote management
    card of a server.

    .. note: ``ipmitool`` is not a standard tool and will need to be installed separately.

    .. warning These commands do not gracefully shutdown a machine. The immediately remove
       power to a machine. Use with caution.

    Args:
        hostname: The hostname of the remote management console.
        username: The username for the remote management console.
        password: The password tied to the username.
        interface_type: A string giving the ``interface_type`` to pass to the CLI.
        timeout: The number of seconds to wait before giving up on a command.
    Returns: A :py:class:`IPMI` instnace.

    """
    def __init__(self, hostname, username, password, interface_type="lan", timeout=30):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.interface_type = interface_type
        cmd_args = ['ipmitool']
        cmd_args.extend(['-H', self.hostname])
        cmd_args.extend(['-U', self.username])
        cmd_args.extend(['-P', self.password])
        cmd_args.extend(['-I', self.interface_type])
        self.cmd_args = cmd_args
        self.timeout = timeout

    def is_power_on(self):
        """ Checks if the power is on.

        Returns: ``True`` if power is on, ``False`` if not.
        """
        command = "chassis power status"
        output = self._run_command(command)

        if "Chassis Power is on" in output:
            return True
        elif "Chassis Power is off" in output:
            return False
        else:
            raise IPMIException("Unexpected command output: {}".format(output))

    def power_off(self):
        """ Turns the power off.

        Returns: ``True`` if power is off, ``False`` if not.
        """
        if not self.is_power_on():
            return True
        else:
            return self._change_power_state(power_on=False)

    def power_on(self):
        """ Turns the power on.

        Returns: ``True`` if power is on, ``False`` if not.
        """
        if self.is_power_on():
            return True
        else:
            return self._change_power_state(power_on=True)

    def power_reset(self):
        """ Turns the power off.

        Returns: ``True`` if power reset initiated, ``False`` if not.
        """
        if not self.is_power_on():
            return self.power_on()
        else:
            command = "chassis power reset"
            output = self._run_command(command)
            if "Reset" in output:
                return True
            else:
                raise Exception("Unexpected command output: {}".format(output))

    def _change_power_state(self, power_on=True):
        """ Changes the power state of a machine.

        Args:
            power_on: A boolean. ``True`` to request the power be turned on,
                ``False`` to turn it off.

        Returns: ``True`` if operation was successful, ``False`` if not.
        """
        if power_on:
            command = "chassis power on"
        else:
            command = "chassis power off"
        output = self._run_command(command)

        if "Chassis Power Control: Up/On" in output and power_on:
            return True
        elif "Chassis Power Control: Down/Off" in output and not power_on:
            return True
        else:
            raise Exception("Unexpected command output: {}".format(output))

    def _run_command(self, command):
        """ Builds the command arguments from the command string.

        Args:
            command: An IPMI command to be passed to the CLI as a string.
                As an example, "chassis power on".
        Returns: The string output from the command's stdout.
        """

        command_args = self.cmd_args + command.split(" ")
        return self._run_ipmi(command_args)

    def _run_ipmi(self, command_args):
        """ Runs the actual IPMI command

        Args:
            command_args: A list of command arguments to be send to ``ipmitool``.
        Returns: The string output from the command's stdout.
        Raises:
            IPMIException: If the return code is non zero.
        """
        proc = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        wait_for(proc.poll, fail_condition=None, num_sec=self.timeout)
        if proc.returncode == 0:
            return proc.stdout.read()
        else:
            raise IPMIException("Unexpected failure: {}".format(proc.stderr.read()))


class IPMIException(Exception):
    """
    Raised during :py:meth:`_run_ipmi` if the error code is non zero.
    """
    pass
