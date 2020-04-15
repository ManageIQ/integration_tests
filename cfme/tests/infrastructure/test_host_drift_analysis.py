import pytest

from cfme import test_requirements
from cfme.common.host_views import HostDriftAnalysis
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider import InfraProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.drift,
    pytest.mark.tier(3),
    pytest.mark.meta(blockers=[BZ(1635126, forced_streams=['5.10'])]),
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=['hosts'])
    argnames += ['host']

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(list(zip(argnames, argvalue_tuple)))

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
    try:
        host_data, = [data for data in provider.data['hosts'] if data['name'] == a_host.name]
    except ValueError:
        pytest.skip('Multiple hosts with the same name found, only expecting one')
    a_host.update_credentials_rest(credentials=host_data['credentials'])

    yield
    a_host.update_credentials_rest(
        credentials={'default': Host.Credential(principal='', secret='')})


def test_host_drift_analysis(appliance, request, a_host, soft_assert, set_host_credentials):
    """Tests host drift analysis

    Metadata:
        test_flag: host_drift_analysis

    Polarion:
        assignee: nansari
        casecomponent: SmartState
        initialEstimate: 1/3h
    """

    # get drift history num
    view = navigate_to(a_host, 'Details')
    drift_num_orig = int(view.entities.summary('Relationships').get_text_of('Drift History'))

    # clear table
    col = appliance.collections.tasks.filter({'tab': 'AllTasks'})
    col.delete_all()

    # initiate 1st analysis
    a_host.run_smartstate_analysis(wait_for_task_result=True)

    # wait for for drift history num+1
    navigate_to(a_host, 'Details')
    wait_for(
        lambda: (view.entities.summary('Relationships').get_text_of('Drift History') ==
                 str(drift_num_orig + 1)),
        delay=10,
        num_sec=360,
        message="Waiting for Drift History count to increase",
        fail_func=appliance.server.browser.refresh
    )

    # add a tag and a finalizer to remove it
    added_tag = appliance.collections.categories.instantiate(
        display_name='Department').collections.tags.instantiate(
        display_name='Accounting')
    a_host.add_tag(added_tag)
    request.addfinalizer(lambda: a_host.remove_tag(added_tag))

    # initiate 2nd analysis
    a_host.run_smartstate_analysis(wait_for_task_result=True)

    # wait for for drift history num+2
    navigate_to(a_host, 'Details')
    wait_for(
        lambda: (view.entities.summary('Relationships').get_text_of('Drift History') ==
                 str(drift_num_orig + 2)),
        delay=10,
        num_sec=360,
        message="Waiting for Drift History count to increase",
        fail_func=appliance.server.browser.refresh
    )
    # check drift difference
    soft_assert(
        a_host.equal_drift_results(
            f'{added_tag.category.display_name} (1)',
            'My Company Tags',
            0,
            1
        ),
        "Drift analysis results are equal when they shouldn't be"
    )

    # Test UI features that modify the drift grid
    drift_analysis_view = appliance.browser.create_view(HostDriftAnalysis)

    # Accounting tag should not be displayed, because it was changed to True
    drift_analysis_view.toolbar.same_values_attributes.click()
    soft_assert(
        not drift_analysis_view.drift_analysis.check_section_attribute_availability(
            f'{added_tag.category.display_name}'),
        f"{added_tag.display_name} row should be hidden, but not")

    # Accounting tag should be displayed now
    drift_analysis_view.toolbar.different_values_attributes.click()
    soft_assert(
        drift_analysis_view.drift_analysis.check_section_attribute_availability(
            f'{added_tag.category.display_name} (1)'),
        f"{added_tag.display_name} row should be visible, but not")
