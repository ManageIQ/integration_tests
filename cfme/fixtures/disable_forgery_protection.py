import time

import pytest

from cfme.utils.log import logger
from cfme.utils.ssh import SSHClient


@pytest.fixture(scope='session')
def disable_forgery_protection():
    starttime = time.time()
    with SSHClient() as ssh_client:
        logger.info('Turning off "allow_forgery_protection"')

        ssh_client.run_command(
            "sed -i \'s/allow_forgery_protection = true/allow_forgery_protection = false/\' "
            "/var/www/miq/vmdb/config/environments/production.rb")
        ssh_client.run_command("service evmserverd restart")

    timediff = time.time() - starttime
    logger.info(f'Turned off "allow_forgery_protection" in: {timediff}')

    yield

    starttime = time.time()
    with SSHClient() as ssh_client:
        logger.info('Turning on "allow_forgery_protection"')

        ssh_client.run_command(
            "sed -i \'s/allow_forgery_protection = false/allow_forgery_protection = true/\' "
            "/var/www/miq/vmdb/config/environments/production.rb")
        ssh_client.run_command("service evmserverd restart")

    timediff = time.time() - starttime
    logger.info(f'Turned on "allow_forgery_protection" in: {timediff}')
