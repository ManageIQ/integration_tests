import pytest

from cfme.configure.configuration.region_settings import Category, Tag, MapTags, RedHatUpdates
from cfme.configure.configuration.analysis_profile import AnalysisProfile
from cfme.utils.appliance.implementations.ui import navigate_to
from navmazing import NavigationDestinationNotFound

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
    ('regions', None, 'Details', False),
    ('zones', None, 'Details', False),
    ('candus', None, 'Details', False),
    ('category', Category, 'All', False),
       # (Import Tags, False),
       # (Import Variables, False),
    ('map_tags', MapTags, 'All', False),
    ('red_hat_updates', RedHatUpdates, 'Details', False),
        #(Help Menu, False),
    ('analysis_profile', AnalysisProfile, 'All', True),

        #(Default zone -> Zone/SmartProxy Affinity, False),
    ('system_schedules', None, 'All', True),
    ('system_schedules', None, 'Add', False),
    ('users', None, 'All', True),
    ('groups', None, 'All', True),
    ('roles', None, 'All', True),
    ('tenants', None, 'All', True),
]

details_pages = [
    ('regions', None, 'Details', False),
    ('users', None, 'Details', False),
    ('groups', None, 'Details', False),
    ('roles', None, 'Details', False),
    ('tenants', None, 'Details', False),
    ('analysis_profile', AnalysisProfile, 'Details', False),
    ('system_schedules', None, 'Details', False),
    ('tag', Tag, 'All', False),
]


@pytest.mark.parametrize('place_info', general_list_pages,
                         ids=['{}_{}'.format(set_type[0], set_type[2].lower()) for set_type in general_list_pages])
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
    try:
        #appliance.browser.widgetastic.refresh()
        view = navigate_to(test_class, place_navigation)
        try:
            view.browser.element("//div[@id='paging_div']/div")
            actual_visibility = True
        except Exception:
            actual_visibility = False
        assert actual_visibility == paginator_expected_result
    except NavigationDestinationNotFound:
        pytest.fail('not that obgect')


diagnostics = [
    ('regions', None, 'Details', False),
]
#
# Go to Configuration -> Diagnostics
# 1) CFME Region - no navigation pane
# 1a) Roles by Servers - no navigation pane
# 1b) Servers by Roles - no navigation pane
# 1c) Servers - no navigation pane

# 1e) Orphaned data - no navigation pane
# 2) Zone - no navigation pane
# 2a) Servers by Roles - no navigation pane
# 2b) Servers - no navigation pane
# 2c) Collect logs - no navigation pane
# 2d) C & U Gap Collection - no navigation pane
# 3b) Collect Logs - no navigation pane
#
# 4) Go to Configuration -> Database - no pagination pane
# 4a) Tables - pagination pane
# 4b) Indexes - pagination pane
# 4c) Settings - pagination pane
# 4d) Client Connections - pagination pane
# 4e) Utilization - no pagination pane