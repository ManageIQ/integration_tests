# -*- coding: utf-8 -*-
import pytest

from widgetastic.utils import partial_match
import miq_version
from cfme import test_requirements
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils import testgen

pytestmark = [
    test_requirements.smartstate,
    pytest.mark.tier(3)
]
HOST_TYPES = ('rhev', 'rhel', 'esx', 'esxi')


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(metafunc, [InfraProvider],
                                                             required_fields=['hosts'])
    argnames = argnames + ['host_type', 'host_name']
    new_argvalues = []
    new_idlist = []

    for index, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        prov_hosts = args['provider'].data.hosts

        for test_host in prov_hosts:
            if not test_host.get('test_fleece', False):
                continue
            assert test_host.get('type') in HOST_TYPES, (
                'host type must be set to [{}] for smartstate analysis tests'.format(
                    '|'.join(HOST_TYPES)))

            new_argvalue_list = [args['provider'], test_host['type'], test_host['name']]
            test_id = '{}-{}-{}'.format(args['provider'].key, test_host['type'], test_host['name'])
            new_argvalues.append(new_argvalue_list)
            new_idlist.append(test_id)
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def host_with_credentials(appliance, provider, host_name):
    """ Add credentials to hosts """
    hosts_collection = appliance.collections.hosts
    host_list = provider.hosts
    test_host = hosts_collection.instantiate(name=host_name, provider=provider)
    host_data = [host for host in host_list if host.name == host_name][0]
    test_host.update_credentials_rest(credentials=host_data.credentials)

    yield test_host
    test_host.update_credentials_rest(credentials=Host.Credential(principal="", secret=""))


@pytest.mark.rhv1
@pytest.mark.uncollectif(
    lambda provider, appliance:
    appliance.version == miq_version.UPSTREAM and provider.one_of(RHEVMProvider))
def test_run_host_analysis(setup_provider_modscope, provider, host_type, host_name, register_event,
                           soft_assert, host_with_credentials):
    """ Run host SmartState analysis

    Metadata:
        test_flag: host_analysis
    """
    register_event(target_type='Host', target_name=host_name, event_type='request_host_scan')
    register_event(target_type='Host', target_name=host_name, event_type='host_scan_complete')

    # Initiate analysis
    host_with_credentials.run_smartstate_analysis(wait_for_task_result=True)

    # Check results of the analysis
    view = navigate_to(host_with_credentials, 'Details')
    drift_history = view.entities.summary('Relationships').get_text_of('Drift History')
    soft_assert(drift_history != '0', 'No drift history change found')

    if provider.type == "rhevm":
        soft_assert(view.entities.summary('Configuration').get_text_of('Services') != '0',
                    'No services found in host detail')

    if host_type in ('rhel', 'rhev'):
        soft_assert(view.entities.summary('Configuration').get_text_of('Packages') != '0',
                    'No packages found in host detail')
        soft_assert(view.entities.summary('Configuration').get_text_of('Files') != '0',
                    'No files found in host detail')

    elif host_type in ('esx', 'esxi'):
        soft_assert(view.entities.summary('Configuration').get_text_of('Advanced Settings') != '0',
                    'No advanced settings found in host detail')
        view.security_accordion.navigation.select(partial_match('Firewall Rules'))
        # Page get updated if rules value is not 0, and title is update
        soft_assert("(Firewall Rules)" in view.title.text, (
            "No firewall rules found in host detail"))
