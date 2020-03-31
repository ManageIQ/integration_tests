from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.ssh import SSHClient


class OcpCli:
    """This class provides CLI functionality for Openshift provider.
    """
    def __init__(self, provider):

        self.hostname = provider.data['hostname']
        creds = provider.data.get('ssh_creds')

        if not creds:
            raise Exception('Could not find ssh_creds in provider\'s cfme data.')
        if isinstance(creds, dict):
            self.username = creds.get('username')
            self.password = creds.get('password')
        else:
            self.username = credentials[creds].get('username')
            self.password = credentials[creds].get('password')

        with SSHClient(hostname=self.hostname, username=self.username,
                       password=self.password, look_for_keys=True) as ssh_client:
            self.ssh_client = ssh_client
            self.ssh_client.load_system_host_keys()

        self._command_counter = 0
        self.log_line_limit = 500

    def run_command(self, *args, **kwargs):
        logger.info('{} - Running SSH Command#{} : {}'
                    .format(self.hostname, self._command_counter, args[0]))
        results = self.ssh_client.run_command(*args, **kwargs)
        results_short = results[:max((self.log_line_limit, len(results)))]
        if results.success:
            logger.info('{} - Command#{} - Succeed: {}'
                        .format(self.hostname, self._command_counter, results_short))
        else:
            logger.warning('{} - Command#{} - Failed: {}'
                           .format(self.hostname, self._command_counter, results_short))
        self._command_counter += 1
        return results

    def close(self):
        self.ssh_client.close()
