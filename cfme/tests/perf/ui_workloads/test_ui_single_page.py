"""Workload to stress WebUI with python requests."""
from utils.appliance import get_server_roles_ui_workload
from utils.conf import cfme_performance
from utils.grafana import get_scenario_dashboard_urls
from utils.log import logger
from utils.smem_memory_monitor import add_workload_quantifiers
from utils.smem_memory_monitor import SmemMemoryMonitor
from utils.ssh import SSHClient
from utils.workloads import get_ui_single_page_scenarios
from collections import OrderedDict
import pytest
import re
import requests
import time

roles_ui_workload = ['automate', 'reporting', 'scheduler', 'user_interface', 'web_services',
    'websocket']

@pytest.mark.usefixtures('set_server_roles_ui_workload_session', 'generate_version_files')
@pytest.mark.parametrize('scenario', get_ui_single_page_scenarios())
def test_ui_single_page(request, scenario):
    """UI Workload to initiate navigations on the WebUI to dashboard and to various major pages."""
    from_ts = int(time.time() * 1000)
    logger.debug('Scenario: {}'.format(scenario['name']))

    scenario_data = {'appliance_ip': cfme_performance['appliance']['ip_address'],
        'appliance_name': cfme_performance['appliance']['appliance_name'],
        'test_dir': 'ui-workload-single-page',
        'test_name': 'UI Workload {}'.format(scenario['name']),
        'appliance_roles': ','.join(roles_ui_workload),
        'scenario': scenario}
    quantifiers = {}
    monitor_thread = SmemMemoryMonitor(SSHClient(), scenario_data)

    def cleanup_workload(scenario, from_ts, quantifiers):
        starttime = time.time()
        to_ts = int(starttime * 1000)
        g_urls = get_scenario_dashboard_urls(scenario, from_ts, to_ts)
        logger.debug('Started cleaning up monitoring thread.')
        monitor_thread.grafana_urls = g_urls
        monitor_thread.signal = False
        monitor_thread.join()
        add_workload_quantifiers(quantifiers, scenario_data)
        timediff = round(time.time() - starttime, 2)
        logger.info('Finished cleaning up monitoring thread in {}'.format(timediff))
    request.addfinalizer(lambda: cleanup_workload(scenario, from_ts, quantifiers))

    monitor_thread.start()

    cfme_ip = cfme_performance['appliance']['ip_address']
    ui_user = cfme_performance['appliance']['web_ui']['username']
    ui_password = cfme_performance['appliance']['web_ui']['password']
    request_number = scenario['requests']
    quantifiers['number of requests'] = request_number
    quantifiers['pages'] = OrderedDict()

    url = 'https://{}/'.format(cfme_ip)
    credentials = {'user_name': ui_user, 'user_password': ui_password}
    headers = {'Accept': 'text/html'}

    with requests.Session() as session:
        response = session.get(url, verify=False, allow_redirects=False, headers=headers)
        found = re.findall(
            r'\<meta\s*content\=\"([0-9a-zA-Z+\/]*\=\=)\"\s*name\=\"csrf\-token\"\s*\/\>',
            response.text)

        if found:
            headers['X-CSRF-Token'] = found[0]
        else:
            logger.error('CSRF Token not found.')

        response = session.post('{}{}'.format(url, 'dashboard/authenticate'), params=credentials,
            verify=False, allow_redirects=False, headers=headers)

        # Get a protected page now:
        for page in scenario['pages']:
            logger.info('Producing Navigations to: {}'.format(page))
            requests_start = time.time()
            for i in range(request_number):
                navigation_start = time.time()
                response = session.get('{}{}'.format(url, page), verify=False, headers=headers)
                navigation_time = round(time.time() - navigation_start, 2)

                if page not in quantifiers['pages']:
                    quantifiers['pages'][page] = OrderedDict()
                    quantifiers['pages'][page]['navigations'] = 1
                    quantifiers['pages'][page][response.status_code] = 1
                    quantifiers['pages'][page]['timings'] = []
                    quantifiers['pages'][page]['timings'].append(
                        {response.status_code: navigation_time})
                else:
                    quantifiers['pages'][page]['navigations'] += 1
                    quantifiers['pages'][page]['timings'].append(
                        {response.status_code: navigation_time})
                    if response.status_code not in quantifiers['pages'][page]:
                        quantifiers['pages'][page][response.status_code] = 1
                    else:
                        quantifiers['pages'][page][response.status_code] += 1

                if response.status_code == 503:
                    # TODO: Better handling of this, typically 503 means the UIWorker has restarted
                    logger.error('Status code 503 received, waiting 5s before next request')
                    time.sleep(5)
                elif response.status_code != 200:
                    logger.error('Non-200 HTTP status code: {} on {}'.format(response.status_code, page))
            requests_time = round(time.time() - requests_start, 2)
            logger.info('Created {} Requests in {}s'.format(request_number, requests_time))

    logger.info('Test Ending...')
