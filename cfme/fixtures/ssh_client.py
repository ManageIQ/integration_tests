import diaper
import pytest

from cfme.fixtures.pytest_store import store
from cfme.utils import ssh
from cfme.utils.log import logger


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session, exitstatus):
    """Loop through the appliance stack and close ssh connections"""

    for ssh_client in store.ssh_clients_to_close:
        logger.debug('Closing ssh connection on %r', ssh_client)
        try:
            ssh_client.close()
        except Exception:
            logger.exception('Closing ssh connection on %r failed, but ignoring', ssh_client)
    for session in ssh._client_session:
        with diaper:
            session.close()
    yield
