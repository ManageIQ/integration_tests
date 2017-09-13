import pytest

import diaper
from fixtures.pytest_store import store
from cfme.utils.log import logger
from cfme.utils import ssh


@pytest.mark.hookwrapper
def pytest_sessionfinish(session, exitstatus):
    """Loop through the appliance stack and close ssh connections"""

    for ssh_client in store.ssh_clients_to_close:
        logger.debug('Closing ssh connection on %r', ssh_client)
        try:
            ssh_client.close()
        except:
            logger.debug(
                'Closing ssh connection on %r failed, but ignoring',
                ssh_client)
    for session in ssh._client_session:
        with diaper:
            session.close()
    yield
