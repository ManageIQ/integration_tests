from datetime import datetime
from datetime import timedelta

import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.provider([VMwareProvider],
    scope='module',
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')]),
    pytest.mark.meta(blockers=[BZ(1635126, forced_streams=['5.10'])])
]


ELEMENTS = ['vm', 'host']
GRAPH_TYPE = ['hourly', 'daily']


@pytest.fixture(scope='module')
def order_data(appliance, provider, enable_candu):
    # Order two day back gap collection data for testing
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)

    view = navigate_to(appliance.server.zone, 'CANDUGapCollection')
    view.candugapcollection.fill({'end_date': end_date,
                                'start_date': start_date})
    view.candugapcollection.submit.click()


@pytest.mark.parametrize('graph_type', GRAPH_TYPE)
@pytest.mark.parametrize('element', ELEMENTS)
def test_gap_collection(appliance, provider, element, graph_type, order_data):
    """ Test gap collection data

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to Configuration > Diagnostics > Zone Gap Collection Page
        * Order old data
        * Navigate to VM or Host Utilization page
        * Check for Hourly data
        * Check for Daily data

    Polarion:
        assignee: nachandr
        casecomponent: CandU
        caseimportance: medium
        initialEstimate: 1/4h
    """
    if element == 'host':
        collection = appliance.collections.hosts
        for test_host in provider.data['hosts']:
            if not test_host.get('test_fleece', False):
                continue
            element = collection.instantiate(name=test_host.name, provider=provider)
    elif element == 'vm':
        collection = appliance.provider_based_collection(provider)
        element = collection.instantiate('cu-24x7', provider)

    date = datetime.now() - timedelta(days=1)
    element.wait_candu_data_available(timeout=1200)

    view = navigate_to(element, 'candu')
    view.options.interval.fill(graph_type.capitalize())
    try:
        graph = getattr(view, 'vm_cpu')
    except AttributeError:
        graph = getattr(view.interval_type, 'host_cpu')
    assert graph.is_displayed

    def refresh():
        provider.browser.refresh()
        view = navigate_to(element, 'candu')
        view.options.interval.fill(graph_type.capitalize())

    # wait, some time graph took time to load
    wait_for(lambda: len(graph.all_legends) > 0,
             delay=5, timeout=600, fail_func=refresh)

    # check collected data for cpu graph
    view.options.calendar.fill(date)
    graph_data = 0
    for leg in graph.all_legends:
        graph.display_legends(leg)
        for data in graph.data_for_legends(leg).values():
            graph_data += float(data[leg].replace(',', '').replace('%', '').split()[0])
    assert graph_data > 0
