"""Runs Idle Workload by resetting appliance and enabling specific roles with no providers."""
from utils.appliance import clean_appliance
from utils.appliance import set_server_roles
from utils.appliance import wait_for_miq_server_workers_started
from utils.conf import cfme_performance
from utils.grafana import get_scenario_dashboard_urls
from utils.log import logger
from utils.smem_memory_monitor import add_workload_quantifiers
from utils.smem_memory_monitor import SmemMemoryMonitor
from utils.ssh import SSHClient
from utils.workloads import get_idle_scenarios
import time
import pytest


def pytest_generate_tests(metafunc):
    argvalues = [[scenario] for scenario in get_idle_scenarios()]
    idlist = [scenario['name'] for scenario in get_idle_scenarios()]
    metafunc.parametrize(['scenario'], argvalues, ids=idlist)


@pytest.mark.usefixtures('generate_version_files')
def test_idle(request, scenario):
    """Runs an appliance at idle with specific roles turned on for specific amount of time. Memory
    Monitor creates graphs and summary at the end of the scenario."""
    from_ts = int(time.time() * 1000)
    ssh_client = SSHClient()
    logger.debug('Scenario: {}'.format(scenario['name']))

    clean_appliance(ssh_client)

    quantifiers = {}
    scenario_data = {'appliance_ip': cfme_performance['appliance']['ip_address'],
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'workload-idle',
        'test_name': 'Idle with {} Roles'.format(scenario['name']),
        'appliance_roles': ', '.join(scenario['roles']),
        'scenario': scenario}
    monitor_thread = SmemMemoryMonitor(SSHClient(), scenario_data)

    def cleanup_workload(from_ts, quantifiers, scenario_data):
        starttime = time.time()
        to_ts = int(starttime * 1000)
        g_urls = get_scenario_dashboard_urls(scenario, from_ts, to_ts)
        logger.debug('Started cleaning up monitoring thread.')
        monitor_thread.grafana_urls = g_urls
        monitor_thread.signal = False
        monitor_thread.join()
        add_workload_quantifiers(quantifiers, scenario_data)
        timediff = time.time() - starttime
        logger.info('Finished cleaning up monitoring thread in {}'.format(timediff))
    request.addfinalizer(lambda: cleanup_workload(from_ts, quantifiers, scenario_data))

    monitor_thread.start()

    wait_for_miq_server_workers_started(poll_interval=2)
    set_server_roles(ssh_client, scenario['roles'])

    s_time = scenario['total_time']
    logger.info('Idling appliance for {}s'.format(s_time))
    time.sleep(s_time)

    quantifiers['Elapsed_Time'] = s_time
    logger.info('Test Ending...')
