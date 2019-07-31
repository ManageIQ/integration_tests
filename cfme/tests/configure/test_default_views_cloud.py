# -*- coding: utf-8 -*-
import random

import pytest
from six import string_types

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
              test_requirements.settings,
              pytest.mark.usefixtures('openstack_provider')]


gtl_params = {
    'Cloud Providers': CloudProvider,
    'Availability Zones': 'cloud_av_zones',
    'Flavors': 'cloud_flavors',
    'Instances': 'cloud_instances',
    'Images': 'cloud_images'
}


# TODO refactor for setup_provider parametrization with new 'latest' tag

def test_default_view_cloud_reset(appliance):
    """This test case performs Reset button test.

    Steps:
        * Navigate to DefaultViews page
        * Check Reset Button is disabled
        * Select 'availability_zones' button from cloud region and change it's default mode
        * Check Reset Button is enabled

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: high
        initialEstimate: 1/20h
        tags: settings
    """
    view = navigate_to(appliance.user.my_settings, "DefaultViews")
    assert view.tabs.default_views.reset.disabled
    cloud_btn = view.tabs.default_views.clouds.availability_zones
    views = ['Tile View', 'Grid View', 'List View']
    views.remove(cloud_btn.active_button)
    cloud_btn.select_button(random.choice(views))
    assert not view.tabs.default_views.reset.disabled


@pytest.mark.parametrize('group_name', list(gtl_params.keys()))
@pytest.mark.parametrize('expected_view', ['List View', 'Tile View', 'Grid View'])
def test_cloud_default_view(appliance, group_name, expected_view):
    """This test case changes the default view of a cloud related page and asserts the change.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: high
        initialEstimate: 1/10h
        tags: settings
    """
    page = gtl_params[group_name]
    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name, fieldset='Clouds')
    default_views.set_default_view(group_name, expected_view, fieldset='Clouds')
    # gtl_params.values(), source of page, are mix of class and collection name
    nav_cls = getattr(appliance.collections, page) if isinstance(page, string_types) else page
    selected_view = navigate_to(nav_cls, 'All', use_resetter=False).toolbar.view_selector.selected
    assert expected_view == selected_view, '{} view setting failed'.format(expected_view)
    default_views.set_default_view(group_name, old_default, fieldset='Clouds')


@pytest.mark.parametrize('expected_view',
                        ['Expanded View', 'Compressed View', 'Details Mode', 'Exists Mode'])
def test_cloud_compare_view(appliance, expected_view):
    """This test changes the default view/mode for comparison between cloud provider instances
    and asserts the change.

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: high
        initialEstimate: 1/10h
        tags: settings
    """

    if expected_view in ['Expanded View', 'Compressed View']:
        group_name, selector_type = 'Compare', 'views_selector'
    else:
        group_name, selector_type = 'Compare Mode', 'modes_selector'

    default_views = appliance.user.my_settings.default_views
    old_default = default_views.get_default_view(group_name)
    default_views.set_default_view(group_name, expected_view)
    inst_view = navigate_to(appliance.collections.cloud_instances, 'All')
    [e.check() for e in inst_view.entities.get_all()[:2]]
    inst_view.toolbar.configuration.item_select('Compare Selected items')
    selected_view = getattr(inst_view.actions, selector_type).selected
    assert expected_view == selected_view, '{} setting failed'.format(expected_view)
    default_views.set_default_view(group_name, old_default)
