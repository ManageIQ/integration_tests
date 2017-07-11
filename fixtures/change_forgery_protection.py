from utils.log import logger
import pytest
from utils.ssh import SSHClient
import time


@pytest.yield_fixture(scope='session')
def change_forgery_protection():
    starttime = time.time()
    ssh_client = SSHClient()
    logger.info('Turning off "allow_forgery_protection"')

    ssh_client.run_command("sed -i \'s/allow_forgery_protection = true/allow_forgery_protection = false/\' "
               "/var/www/miq/vmdb/config/environments/production.rb")
    ssh_client.run_command("service evmserverd restart")

    ssh_client.close()
    timediff = time.time() - starttime
    logger.info('Turned off "allow_forgery_protection" in: {}'.format(timediff))

    yield

    starttime = time.time()
    ssh_client = SSHClient()
    logger.info('Turning on "allow_forgery_protection"')

    ssh_client.run_command("sed -i \'s/allow_forgery_protection = false/allow_forgery_protection = true/\' "
               "/var/www/miq/vmdb/config/environments/production.rb")
    ssh_client.run_command("service evmserverd restart")

    ssh_client.close()
    timediff = time.time() - starttime
    logger.info('Turned on "allow_forgery_protection" in: {}'.format(timediff))
