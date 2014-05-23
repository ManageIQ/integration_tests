#-*- coding: utf-8 -*-

from cfme.configure import tasks
from cfme.exceptions import ListAccordionLinkNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host
from cfme.web_ui import flash, listaccordion as list_acc, tabstrip as tabs, toolbar as tb
from utils import conf
from utils.providers import infra_provider_type_map
from utils.wait import wait_for
import pytest


pytestmark = [pytest.mark.usefixtures("setup_infrastructure_providers")]


HOST_TYPES = ('rhev', 'rhel', 'esx', 'esxi')


def fetch_list():
    tests = []
    for provider in conf.cfme_data["management_systems"]:
        prov_data = conf.cfme_data['management_systems'][provider]
        if prov_data["type"] not in infra_provider_type_map:
            continue
        if not prov_data.get('hosts', None):
            continue

        for test_host in prov_data["hosts"]:
            if not test_host.get('test_fleece', False):
                continue

            assert test_host.get('type', None) in HOST_TYPES,\
                'host type must be set to [{}] for smartstate analysis tests'\
                .format('|'.join(HOST_TYPES))
            tests.append([provider, test_host['type'], test_host['name']])
    return tests


# TODO I probably should be using utils/testgen here
def pytest_generate_tests(metafunc):
    argnames = []
    if 'host_name' in metafunc.fixturenames:
        argnames = ['provider', 'host_type', 'host_name']
        argvalues = fetch_list()
        metafunc.parametrize(argnames, argvalues, scope="module")


def get_host_data_by_name(host_name):
    for provider in conf.cfme_data['management_systems']:
        for host_obj in conf.cfme_data['management_systems'][provider].get('hosts', []):
            if host_name == host_obj['name']:
                return host_obj
    return None


def test_run_host_analysis(provider, host_type, host_name, register_event):
    """ Run host SmartState analysis """
    # Add credentials to host
    host_data = get_host_data_by_name(host_name)
    test_host = host.Host(name=host_name)

    wait_for(lambda: test_host.exists, delay=10, num_sec=120, fail_func=sel.refresh)

    if not test_host.has_valid_credentials:
        test_host.update(
            updates={'credentials': host.get_credentials_from_config(host_data['credentials'])}
        )
        wait_for(
            lambda: test_host.has_valid_credentials,
            delay=10,
            num_sec=120,
            fail_func=sel.refresh
        )

    register_event(None, "host", host_name, ["host_analysis_request", "host_analysis_complete"])

    # Initiate analysis
    sel.force_navigate('infrastructure_host', context={'host': test_host})
    tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_contain('"{}": Analysis successfully initiated'.format(host_name))

    # Wait for the task to finish
    def is_host_analysis_finished():
        """ Check if analysis is finished - if not, reload page
        """
        if not sel.is_displayed(tasks.tasks_table) or not tabs.is_tab_selected('All Other Tasks'):
            sel.force_navigate('tasks_all_other')
        host_analysis_finished = tasks.tasks_table.find_row_by_cells({
            'task_name': "SmartState Analysis for '{}'".format(host_name),
            'state': 'Finished'
        })
        return host_analysis_finished is not None

    wait_for(
        is_host_analysis_finished,
        delay=10,
        num_sec=120,
        fail_func=lambda: tb.select('Reload')
    )

    # Delete the task
    tasks.tasks_table.select_row_by_cells({
        'task_name': "SmartState Analysis for '{}'".format(host_name),
        'state': 'Finished'
    })
    tb.select('Delete Tasks', 'Delete', invokes_alert=True)
    sel.handle_alert()

    # Check results of the analysis
    assert test_host.get_detail('Configuration', 'Services') != '0',\
        'No services found in host detail'

    if host_type in ('rhel', 'rhev'):
        assert test_host.get_detail('Security', 'Users') != '0',\
            'No users found in host detail'
        assert test_host.get_detail('Security', 'Groups') != '0',\
            'No groups found in host detail'
        assert test_host.get_detail('Configuration', 'Packages') != '0',\
            'No packages found in host detail'

    elif host_type in ('esx', 'esxi'):
        assert test_host.get_detail('Configuration', 'Advanced Settings') != '0',\
            'No advanced settings found in host detail'

        # If the Firewall Rules are 0, the element can't be found (it's not a link)
        try:
            # This fails for vsphere4...  https://bugzilla.redhat.com/show_bug.cgi?id=1055657
            list_acc.select('Security', 'Show the firewall rules on this Host')
        except ListAccordionLinkNotFound:
            pytest.fail("No firewall rules found in host detail accordion")
