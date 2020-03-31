import attr
import pytest
import requests

from cfme.fixtures.pytest_store import store
from cfme.fixtures.rdb import Rdb
from cfme.utils.conf import rdb
from cfme.utils.net import net_check
from cfme.utils.wait import TimedOutError


@attr.s
class AppliancePoliceException(Exception):
    message = attr.ib()
    port = attr.ib()

    def __str__(self):
        return f"{self.message} (port {self.port})"


@pytest.fixture(autouse=True, scope="function")
def appliance_police(appliance):
    if not store.slave_manager:
        return
    try:
        available_ports = {
            'ssh': (appliance.hostname, appliance.ssh_port),
            'https': (appliance.hostname, appliance.ui_port),
            'postgres': (appliance.db_host or appliance.hostname, appliance.db_port)}
        port_results = {pn: net_check(addr=p_addr, port=p_port, force=True)
                        for pn, (p_addr, p_port) in available_ports.items()}
        for port, result in port_results.items():
            if port == 'ssh' and appliance.is_pod:
                # ssh is not available for podified appliance
                continue
            if not result:
                raise AppliancePoliceException('Unable to connect', available_ports[port][1])

        try:
            status_code = requests.get(appliance.url, verify=False,
                                       timeout=120).status_code
        except Exception:
            raise AppliancePoliceException('Getting status code failed',
                                           available_ports['https'][1])

        if status_code != 200:
            raise AppliancePoliceException('Status code was {}, should be 200'.format(
                status_code), available_ports['https'][1])
        return
    except AppliancePoliceException as e:
        # special handling for known failure conditions
        if e.port == 443:
            # Lots of rdbs lately where evm seems to have entirely crashed
            # and (sadly) the only fix is a rude restart
            appliance.restart_evm_rude()
            try:
                appliance.wait_for_web_ui(900)
                store.write_line('EVM was frozen and had to be restarted.', purple=True)
                return
            except TimedOutError:
                pass
        e_message = str(e)
    except Exception as e:
        e_message = str(e)

    # Regardles of the exception raised, we didn't return anywhere above
    # time to call a human
    msg = f'Help! My appliance {appliance.url} crashed with: {e_message}'
    store.slave_manager.message(msg)
    if 'appliance_police_recipients' in rdb:
        rdb_kwargs = {
            'subject': 'RDB Breakpoint: Appliance failure',
            'recipients': rdb.appliance_police_recipients,
        }
    else:
        rdb_kwargs = {}
    Rdb(msg).set_trace(**rdb_kwargs)
    store.slave_manager.message('Resuming testing following remote debugging')
