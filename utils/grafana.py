"""Wrap interactions with Grafana or logging Grafana URLs."""
from utils.conf import cfme_performance
from utils.log import logger


def get_scenario_dashboard_urls(scenario, from_ts, to_ts, output_to_log=True):
    """Builds a dictionary of URLs to Grafana Dashboards of relevant appliances for a single
    workload's scenario.  It accounts for when a replication_master appliance is under test too."""
    if cfme_performance['tools']['grafana']['enabled']:
        g_ip = cfme_performance['tools']['grafana']['ip_address']
        g_port = cfme_performance['tools']['grafana']['port']
        appliance_name = cfme_performance['appliance']['appliance_name']
        dashboard_name = cfme_performance['tools']['grafana']['default_dashboard']
        grafana_urls = {}
        if 'grafana_dashboard' in scenario:
            dashboard_name = scenario['grafana_dashboard']
        stub = 'http://{}:{}/dashboard/db/{}?from={}&to={}&var-Node={}'
        grafana_urls['appliance'] = stub.format(g_ip, g_port, dashboard_name,
                                                from_ts, to_ts, appliance_name)
        if 'replication_master' in scenario:
            grafana_urls['replication_master'] = \
                stub.format(g_ip, g_port, dashboard_name, from_ts, to_ts,
                            scenario['replication_master']['appliance_name'])
        if output_to_log:
            logger.info('Grafana URLs: {}'.format(grafana_urls))
        return grafana_urls
    else:
        logger.warn('Grafana integration is not enabled')
        return ''
