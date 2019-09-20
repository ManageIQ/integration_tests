import fauxfactory
import pytest
from widgetastic.exceptions import NoSuchElementException
from widgetastic_patternfly import Dropdown

from cfme import test_requirements
from cfme.configure.configuration.region_settings import RedHatUpdates
from cfme.utils.appliance.implementations.ui import navigate_to

general_list_pages = [
    ('servers', None, 'Details', False),
    ('servers', None, 'Authentication', False),
    ('servers', None, 'Workers', False),
    ('servers', None, 'CustomLogos', False),
    ('servers', None, 'Advanced', False),
    ('servers', None, 'DiagnosticsDetails', False),
    ('servers', None, 'DiagnosticsWorkers', False),
    ('servers', None, 'CFMELog', False),
    ('servers', None, 'AuditLog', False),
    ('servers', None, 'ProductionLog', False),
    ('servers', None, 'Utilization', False),
    ('servers', None, 'Timelines', False),
    ('servers', None, 'ServerDiagnosticsCollectLogs', False),
    ('servers', None, 'DatabaseSummary', False),
    ('servers', None, 'DatabaseTables', True),
    ('servers', None, 'DatabaseIndexes', True),
    ('servers', None, 'DatabaseSettings', True),
    ('servers', None, 'DatabaseClientConnections', True),
    ('servers', None, 'DatabaseUtilization', False),
    ('regions', None, 'Details', False),
    ('regions', None, 'ImportTags', False),
    ('regions', None, 'Import', False),
    ('regions', None, 'HelpMenu', False),
    ('regions', None, 'Advanced', False),
    ('regions', None, 'DiagnosticsZones', False),
    ('regions', None, 'OrphanedData', False),
    ('regions', None, 'Servers', True),
    ('regions', None, 'ServersByRoles', False),
    ('regions', None, 'RolesByServers', False),
    ('zones', None, 'Zone', False),
    ('zones', None, 'SmartProxyAffinity', False),
    ('zones', None, 'Advanced', False),
    ('zones', None, 'ServersByRoles', False),
    ('zones', None, 'Servers', True),
    ('zones', None, 'CANDUGapCollection', False),
    ('zones', None, 'RolesByServers', False),
    ('zones', None, 'CollectLogs', False),
    ('candus', None, 'Details', False),
    ('map_tags', None, 'All', False),
    ('categories', None, 'All', False),
    ('red_hat_updates', RedHatUpdates, 'Details', False),
    ('analysis_profiles', None, 'All', True),
    ('system_schedules', None, 'Add', False),
    ('users', None, 'All', True),
    ('groups', None, 'All', True),
    ('roles', None, 'All', True),
    ('tenants', None, 'All', True),
]

details_pages = [
    ('users', None, 'Details', False),
    ('groups', None, 'Details', False),
    ('roles', None, 'Details', False),
    ('tenants', None, 'Details', False),
    ('analysis_profiles', None, 'Details', False),
    ('system_schedules', None, 'All', True),
    ('system_schedules', None, 'Details', False),
    ('tag', None, 'All', False),
]

items_selection_5_10 = ['5 Items', '10 Items', '20 Items', '50 Items', '100 Items', '1000 Items']

items_selection = ['5 Items', '10 Items', '20 Items', '50 Items', '100 Items', '200 Items',
                   '500 Items', '1000 Items']


def check_paginator_for_page(view):
    try:
        panel = view.browser.element('//ul[@class="pagination"]')
        return panel.is_displayed()
    except NoSuchElementException:
        return False


@pytest.fixture(scope='module')
def schedule(appliance):
    schedule = appliance.collections.system_schedules.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    yield schedule
    schedule.delete()


@test_requirements.configuration
@pytest.mark.parametrize('place_info', general_list_pages,
                         ids=['{}_{}'.format(set_type[0], set_type[2].lower())
                              for set_type in general_list_pages])
def test_paginator_config_pages(appliance, place_info):
    """
        Check paginator is visible for config pages

    Polarion:
        assignee: tpapaioa
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    place_name, place_class, place_navigation, paginator_expected_result = place_info
    if place_class:
        test_class = place_class
    else:
        test_class = getattr(appliance.collections, place_name)
        if place_name == 'regions':
            test_class = test_class.instantiate()
        elif place_name == 'servers':
            test_class = test_class.get_master()
        elif place_name == 'zones':
            test_class = appliance.collections.servers.get_master().zone
    view = navigate_to(test_class, place_navigation)
    assert check_paginator_for_page(view) == paginator_expected_result


@test_requirements.configuration
@pytest.mark.parametrize('place_info', details_pages,
                         ids=['{}_{}'.format(set_type[0], set_type[2].lower())
                              for set_type in details_pages])
def test_paginator_details_page(appliance, place_info, schedule):
    """
        Check paginator is visible for access control pages + schedules.
        If paginator is present, check that all options are present in items per page.

    Polarion:
        assignee: tpapaioa
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/10h
    Bugzilla:
        1515952
    """
    place_name, place_class, place_navigation, paginator_expected_result = place_info
    if place_name == 'tag':
        category = appliance.collections.categories.instantiate(
            name='department', display_name='Department')
        test_class = category.collections.tags
        view = navigate_to(test_class, place_navigation)
    else:
        test_class = place_class if place_class else getattr(appliance.collections, place_name)
        view = navigate_to(test_class, 'All')
        table = view.table if hasattr(view, 'table') else view.entities.table
        if place_navigation == 'Details':
            table[0].click()
    assert check_paginator_for_page(view) == paginator_expected_result

    if check_paginator_for_page(view):
        paginator = view.paginator
        items_selector = Dropdown(view, '{} Items'.format(paginator.items_per_page))
        msg = 'Not all options are present in items per page'
        if view.extra.appliance.version < '5.11':
            assert set(items_selection_5_10) == set(items_selector.items), msg
        else:
            assert set(items_selection) == set(items_selector.items), msg


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_configure_diagnostics_pages_cfme_region():
    """
    Go to Settings -> Configuration -> Diagnostics -> CFME Region
    and check whether all sub pages are showing.

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/15h
    """
    pass
