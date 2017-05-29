from utils import conf
from utils.log import logger
from utils.ssh import SSHClient


class OcpCli(object):
    """This class provides CLI functionality for Openshift provider.
    """
    def __init__(self, provider):

        provider_cfme_data = provider.get_yaml_data()
        self.hostname = provider_cfme_data['hostname']
        creds = conf.configuration.yaycl_config.credentials
        if hasattr(creds, provider.key):
            prov_creds = getattr(creds, provider.key)
            self.username = prov_creds.username
            self.password = prov_creds.password
            self.ssh_client = SSHClient(hostname=self.hostname,
                                        username=self.username,
                                        password=self.password)
        else:
            # Try with known hosts
            self.ssh_client = SSHClient()
            self.ssh_client.load_system_host_keys()
            self.ssh_client.connect(self.hostname)
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
