# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.configure.configuration.region_settings import Tag, Category
from cfme.common.host_views import HostDriftAnalysis
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider import InfraProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.drift,
    pytest.mark.tier(3)
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=['hosts'])
    argnames += ['host']

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        for test_host in args['provider'].data['hosts']:
            if not test_host.get('test_fleece', False):
                continue

            argvs = argvalues[i][:]
            new_argvalues.append(argvs + [test_host])
            test_id = '{}-{}'.format(args['provider'].key, test_host['type'])
            new_idlist.append(test_id)
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def a_host(host, appliance, provider):
    host_collection = appliance.collections.hosts
    return host_collection.instantiate(name=host.name, provider=provider)


@pytest.fixture(scope='module')
def set_host_credentials(provider, a_host, setup_provider_modscope):
    host_list = provider.hosts
    host_names = [host.name for host in host_list]
    for host_name in host_names:
        host_data = [host for host in host_list if host.name == host_name][0]
        a_host.update_credentials_rest(credentials=host_data.credentials)

    yield
    a_host.update_credentials_rest(credentials=Host.Credential(principal="", secret=""))


@pytest.mark.rhv3
def test_host_drift_analysis(appliance, request, a_host, soft_assert, set_host_credentials):
    """Tests host drift analysis

    Metadata:
        test_flag: host_drift_analysis
    """

    # tabs changed, hack until configure.tasks is refactored for collections and versioned widgets
    destination = 'AllTasks' if appliance.version >= '5.9' else 'AllOtherTasks'

    # get drift history num
    view = navigate_to(a_host, 'Details')
    drift_num_orig = int(view.entities.summary('Relationships').get_text_of('Drift History'))

    # clear table
    col = appliance.collections.tasks.filter({'tab': destination})
    col.delete_all()

    # initiate 1st analysis
    a_host.run_smartstate_analysis(wait_for_task_result=True)

    # wait for for drift history num+1
    navigate_to(a_host, 'Details')
    wait_for(
        lambda: (view.entities.summary('Relationships').get_text_of('Drift History') ==
                 str(drift_num_orig + 1)),
        delay=20,
        num_sec=360,
        message="Waiting for Drift History count to increase",
        fail_func=appliance.server.browser.refresh
    )

    # add a tag and a finalizer to remove it
    added_tag = Tag(display_name='Accounting', category=Category(display_name='Department'))
    a_host.add_tag(added_tag)
    request.addfinalizer(lambda: a_host.remove_tag(added_tag))

    # initiate 2nd analysis
    a_host.run_smartstate_analysis(wait_for_task_result=True)

    # wait for for drift history num+2
    navigate_to(a_host, 'Details')
    wait_for(
        lambda: (view.entities.summary('Relationships').get_text_of('Drift History') ==
                 str(drift_num_orig + 2)),
        delay=20,
        num_sec=360,
        message="Waiting for Drift History count to increase",
        fail_func=appliance.server.browser.refresh
    )

    # check drift difference
    soft_assert(a_host.equal_drift_results(
        '{} (1)'.format(added_tag.category.display_name), 'My Company Tags', 0, 1),
        "Drift analysis results are equal when they shouldn't be")

    # Test UI features that modify the drift grid
    drift_analysis_view = appliance.browser.create_view(HostDriftAnalysis)

    # Accounting tag should not be displayed, because it was changed to True
    drift_analysis_view.toolbar.same_values_attributes.click()
    soft_assert(
        not drift_analysis_view.drift_analysis.check_section_attribute_availability(
            '{}'.format(added_tag.category.display_name)),
        "{} row should be hidden, but not".format(added_tag.display_name))

    # Accounting tag should be displayed now
    drift_analysis_view.toolbar.different_values_attributes.click()
    soft_assert(
        drift_analysis_view.drift_analysis.check_section_attribute_availability(
            '{} (1)'.format(added_tag.category.display_name)),
        "{} row should be visible, but not".format(added_tag.display_name))
