import fauxfactory
import pytest

from widgetastic.exceptions import NoSuchElementException

from cfme.configure.configuration.analysis_profile import AnalysisProfile, AnalysisProfileDetailsView
from cfme.configure.configuration.region_settings import Category, Tag, MapTags, RedHatUpdates
from cfme.utils.appliance.implementations.ui import navigate_to

general_list_pages = [
    ('servers', None, 'Details', False),
    ('servers', None, 'Authentication', False),
    ('servers', None, 'Workers', False),
    ('servers', None, 'CustomLogos', False),
    ('servers', None, 'Advanced', False),
    ('servers', None, 'DatabaseSummary', False),
    ('servers', None, 'DiagnosticsDetails', False),
    ('servers', None, 'DiagnosticsWorkers', True),
    ('servers', None, 'CFMELog', False),
    ('servers', None, 'AuditLog', False),
    ('servers', None, 'ProductionLog', False),
    ('servers', None, 'Utilization', False),
    ('servers', None, 'Timelines', False),
    ('servers', None, 'ServerDiagnosticsCollectLogs', False),
    ('servers', None, 'DatabaseTables', False),
    ('servers', None, 'DatabaseIndexes', False),
    ('servers', None, 'DatabaseSettings', False),
    ('servers', None, 'DatabaseClientConnections', False),
    ('servers', None, 'DatabaseUtilization', False),

    ('regions', None, 'Details', False),
    ('regions', None, 'ImportTags', False),
    ('regions', None, 'Imports', False),
    ('regions', None, 'HelpMenu', False),
    ('regions', None, 'Diagnostics', False),
    ('regions', None, 'DiagnosticsZones', False),
    ('regions', None, 'OrphanedData', False),
    ('regions', None, 'Servers', False),
    ('regions', None, 'ServersByRoles', False),
    ('regions', None, 'RolesByServers', False),

    ('zones', None, 'Details', False),
    ('zones', None, 'SmartProxyAffinity', False),
    ('zones', None, 'Diagnostics', False),
    ('zones', None, 'ServersByRoles', False),
    ('zones', None, 'Servers', False),
    ('zones', None, 'CANDUGapCollection', False),
    ('zones', None, 'RolesByServers', False),
    ('zones', None, 'ZoneCollectLogs', False),


    ('candus', None, 'Details', False),
    ('category', Category, 'All', False),
    ('map_tags', MapTags, 'All', False),
    ('red_hat_updates', RedHatUpdates, 'Details', False),
    ('analysis_profile', AnalysisProfile, 'All', True),
    ('system_schedules', None, 'All', True),
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
    ('analysis_profile', AnalysisProfile, 'Details', False),
    ('system_schedules', None, 'Details', False),
    ('tag', Tag, 'All', False),
]


def check_paginator_for_page(view):
    try:
        view.browser.element("//div[@id='paging_div']/div")
        return True
    except NoSuchElementException:
        return False


@pytest.mark.parametrize('place_info', general_list_pages,
                         ids=['{}_{}'.format(set_type[0], set_type[2].lower())
                              for set_type in general_list_pages])
def test_paginator(appliance, place_info):
    place_name, place_class, place_navigation, paginator_expected_result = place_info
    if place_name in ['regions', 'zones']:
        test_class = getattr(appliance.collections, place_name).instantiate()
    elif place_name == 'servers':
        test_class = getattr(appliance.collections, place_name).get_master()
    elif not place_class:
        test_class = getattr(appliance.collections, place_name)
    else:
        test_class = place_class
    appliance.browser.widgetastic.refresh()
    view = navigate_to(test_class, place_navigation)
    assert check_paginator_for_page(view) == paginator_expected_result


@pytest.mark.parametrize('place_info', details_pages,
                         ids=['{}_{}'.format(set_type[0], set_type[2].lower())
                              for set_type in details_pages])
def test_paginator_details_page(appliance, place_info):
    place_name, place_class, place_navigation, paginator_expected_result = place_info
    # First lets check for existing content
    if place_class in ['users', 'groups', 'roles', 'tenants']:
        test_class = getattr(appliance.collections, place_name)
        view = navigate_to(test_class, 'All')
        table = view.table if hasattr(view, 'table') else view.entities.table
        if table.is_displayed:
            view.entities.table[0].click()
    elif place_class == 'tag':
        cg = Category(name='department', description='Department')
        test_class = place_class(category=cg)
        view = navigate_to(test_class, place_navigation)
    else:
        test_class = place_class.create(
            name=fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
        )
        view = navigate_to(test_class, place_navigation)
    assert check_paginator_for_page(view) == paginator_expected_result