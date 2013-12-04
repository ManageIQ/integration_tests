import subprocess
from utils.wait import wait_for


class IPMI():
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
        command = "chassis power status"
        output = self._run_command(command)

        if "Chassis Power is on" in output:
            return True
        elif "Chassis Power is off" in output:
            return False
        else:
            raise IPMIException("Unexpected command output: %s" % output)

    def power_off(self):
        if not self.is_power_on():
            return True
        else:
            return self._change_power_state(power_on=False)

    def power_on(self):
        if self.is_power_on():
            return True
        else:
            return self._change_power_state(power_on=True)

    def power_reset(self):
        if not self.is_power_on():
            return self.power_on()
        else:
            command = "chassis power reset"
            output = self._run_command(command)
            if "Reset" in output:
                return True
            else:
                raise Exception("Unexpected command output: %s" % output)

    def _change_power_state(self, power_on=True):
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
            raise Exception("Unexpected command output: %s" % output)

    def _run_command(self, command):
        command_args = self.cmd_args + command.split(" ")
        return self._run_ipmi(command_args)

    def _run_ipmi(self, command_args):
        proc = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        wait_for(proc.poll, fail_condition=None, num_sec=self.timeout)
        if proc.returncode == 0:
            return proc.stdout.read()
        else:
            raise IPMIException("Unexpected failure: %s" % proc.stderr.read())


class IPMIException(Exception):
    pass
