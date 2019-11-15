import socket
import textwrap

from paramiko_expect import SSHClientInteraction

from cfme.exceptions import SSHExpectTimeoutError
from cfme.utils.log import logger


def logging_callback(appliance):
    def the_logger(m):
        logger.info('Appliance %s:\n%s', appliance.hostname, m)
    return the_logger


class SSHExpect(SSHClientInteraction):
    def __init__(self, appliance):
        SSHClientInteraction.__init__(
            self, appliance.ssh_client, timeout=10, display=True,
            output_callback=logging_callback(appliance))

    def answer(self, question, answer, timeout=None):
        self.expect(question, timeout=timeout)
        self.send(answer)

    def expect(self, re_string, *args, **kwargs):
        try:
            SSHClientInteraction.expect(self, re_string, *args, **kwargs)
        except socket.timeout:
            current_output = '""' if not self.current_output else self.current_output
            raise SSHExpectTimeoutError(
                f"Timeouted when waiting for '{re_string}'. Current output:\n"
                + textwrap.indent(current_output, '> '))
