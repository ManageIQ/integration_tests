from paramiko_expect import SSHClientInteraction

from cfme.utils.log import logger


def logging_callback(appliance):
    def the_logger(m):
        logger.debug('Appliance %s:\n%s', appliance.hostname, m)
    return the_logger


class SSHExpect(SSHClientInteraction):
    def __init__(self, appliance):
        SSHClientInteraction.__init__(
            self, appliance.ssh_client, timeout=10, display=True,
            output_callback=logging_callback(appliance))

    def answer(self, question, answer, timeout=None):
        self.expect(question, timeout=timeout)
        self.send(answer)
