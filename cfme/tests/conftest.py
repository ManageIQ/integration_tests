import pytest
from utils.net import net_check
import requests
from fixtures.pytest_store import store


@pytest.fixture(autouse=True, scope="function")
def appliance_police():
    if not store.slave_manager:
        return
    try:
        ports = {'ssh': 22, 'https': 443, 'postgres': 5432}
        port_results = {pn: net_check(pp) for pn, pp in ports.items()}
        for port, result in port_results.items():
            if not result:
                raise Exception('Port {} was not contactable'.format(port))
        status_code = requests.get(store.current_appliance.url, verify=False,
                                   timeout=60).status_code
        if status_code != 200:
            raise Exception('Status code was {}, should be 200'.format(status_code))
    except Exception as e:
        store.slave_manager.message(
            'Help! My appliance {} crashed with: {}'.format(
                store.current_appliance.url,
                e.message))
        store.slave_manager.send_event('i_did_a_bad_thing')
