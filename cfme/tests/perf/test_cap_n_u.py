# -*- coding: utf-8 -*
import pytest
from utils.log import logger
from utils.providers import setup_provider
from utils.hosts import setup_providers_hosts_credentials
from cfme.configure import configuration
from utils.ssh import SSHClient
from utils import conf
from fixtures import navigation as nav
import time

pytestmark = [
    pytest.mark.fixtureconf(
        server_roles="+ems_metrics_coordinator +ems_metrics_collector +ems_metrics_processor"),
    pytest.mark.usefixtures("setup_infrastructure_providers")]


def test_cap_and_u_timings():

    ssh_kwargs = {
        'username': conf.credentials['ssh']['username'],
        'password': conf.credentials['ssh']['password'],
        'hostname': conf.env['base_url']
    }

    # Set Roles
    logger.info('Setting up server roles...')
    configuration.set_server_roles(**{"ems_metrics_coordinator": True, "ems_metrics_collector": True, "ems_metrics_processor": True, "web_services": False})

    # Set C&U Collection
    logger.info('Setting up c&u collection...')
    cnf_page = nav.cnf_configuration_pg()
    settings = cnf_page.click_on_settings()
    rsettings = settings.click_on_first_region()
    cusettings = rsettings.click_on_cap_and_util()
    cusettings.check_all_clusters()
    cusettings.check_all_datastores()
    cusettings.save_button.click()

    # Issue with using old code and not waiting for the ajax call to complete
    time.sleep(3)

    # add providers
    logger.info('Setting up provider...')
    setup_provider('perfrhevm33')

    # credential hosts
    logger.info('Credentialing hosts...')
    setup_providers_hosts_credentials('perfrhevm33')

    # Place the shell script that compiles all evm log files into single log file
    logger.info('Sending perf_evmlog.sh to Appliance...')
    client = SSHClient(**ssh_kwargs)
    client.put_file('cfme_tests/scripts/perf_evmlog.sh', '/root/perf_evmlog.sh')
    client.close()

    logger.info('Finished setting up host appliance...')

    # Wait for c&u collections to occur, currently test 1 hour, future test 24hrs
    logger.info('Waiting 1hr for C&U collections to occur...')
    time.sleep(3600)

    # Compile any logrotated evm log files into a single evm.total.log file
    logger.info('Running perf_evmlog.sh on Appliance...')
    client.connect(**ssh_kwargs)
    client.run_command('./perf_evmlog.sh')

    # Get that file
    logger.info('Getting evm.total.log.gz...')
    client.get_file('/var/www/miq/vmdb/log/evm.total.log.gz', 'cfme_tests/log/evm.total.log.gz')
    client.close()
