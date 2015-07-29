# -*- coding: utf-8 -*-
from cfme.configure import tasks
from cfme.exceptions import ListAccordionLinkNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host
from cfme.web_ui import listaccordion as list_acc, tabstrip as tabs, toolbar as tb
from utils import conf
from utils import testgen
from utils.wait import wait_for


HOST_TYPES = ('rhev', 'rhel', 'esx', 'esxi')


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(metafunc)
    argnames = argnames + ['host_type', 'host_name']
    new_argvalues = []
    new_idlist = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        prov_hosts = args['provider'].data['hosts']

        if not prov_hosts:
            continue
        for test_host in prov_hosts:
            if not test_host.get('test_fleece', False):
                continue
            assert test_host.get('type', None) in HOST_TYPES,\
                'host type must be set to [{}] for smartstate analysis tests'\
                .format('|'.join(HOST_TYPES))

            argvalues[i] = argvalues[i] + [test_host['type'], test_host['name']]
            test_id = '{}-{}-{}'.format(args['provider'].key, test_host['type'], test_host['name'])
            idlist.append(test_id)
            new_argvalues.append(argvalues[i])
            new_idlist.append(test_id)
    metafunc.parametrize(argnames, new_argvalues, ids=new_idlist, scope="module")


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


def test_run_host_analysis(request, setup_provider, provider, host_type, host_name, register_event,
                           soft_assert, bug):
    """ Run host SmartState analysis

    Metadata:
        test_flag: host_analysis
    """
    # Add credentials to host
    host_data = get_host_data_by_name(provider.key, host_name)
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

        # Remove creds after test
        def test_host_remove_creds():
            test_host.update(
                updates={
                    'credentials': host.Host.Credential(
                        principal="",
                        secret="",
                        verify_secret=""
                    )
                }
            )
        request.addfinalizer(test_host_remove_creds)

    register_event(None, "host", host_name, ["host_analysis_request", "host_analysis_complete"])

    # Initiate analysis
    test_host.run_smartstate_analysis()

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
        delay=15,
        num_sec=480,
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
    services_bug = bug(1156028)
    if not (services_bug is not None and provider.type == "rhevm" and provider.version >= "3.3"):
        soft_assert(test_host.get_detail('Configuration', 'Services') != '0',
            'No services found in host detail')

    if host_type in ('rhel', 'rhev'):
        soft_assert(test_host.get_detail('Security', 'Users') != '0',
            'No users found in host detail')
        soft_assert(test_host.get_detail('Security', 'Groups') != '0',
            'No groups found in host detail')
        soft_assert(test_host.get_detail('Configuration', 'Packages') != '0',
            'No packages found in host detail')

    elif host_type in ('esx', 'esxi'):
        soft_assert(test_host.get_detail('Configuration', 'Advanced Settings') != '0',
            'No advanced settings found in host detail')

        fw_bug = bug(1055657)
        if not (fw_bug is not None and provider.type == "virtualcenter" and provider.version < "5"):
            # If the Firewall Rules are 0, the element can't be found (it's not a link)
            try:
                # This fails for vsphere4...  https://bugzilla.redhat.com/show_bug.cgi?id=1055657
                list_acc.select('Security', 'Show the firewall rules on this Host')
            except ListAccordionLinkNotFound:
                # py.test's .fail would wipe the soft_assert data
                soft_assert(False, "No firewall rules found in host detail accordion")
