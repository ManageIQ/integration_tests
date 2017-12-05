# -*- coding: utf-8 -*-
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.datastore import DatastoreCollection


pytestmark = [pytest.mark.tier(3), pytest.mark.usefixtures("virtualcenter_provider")]


def test_set_default_host_filter(request, appliance):
    """ Test for setting default filter for hosts."""
    host_collection = appliance.collections.hosts

    # Add cleanup finalizer
    def unset_default_host_filter():
        view = navigate_to(host_collection, 'All')
        view.filters.navigation.select('ALL')
        view.default_filter_btn.click()
    request.addfinalizer(unset_default_host_filter)

    view = navigate_to(host_collection, 'All')
    view.filters.navigation.select('Status / Running')
    view.default_filter_btn.click()
    appliance.server.logout()
    appliance.server.login_admin()
    navigate_to(host_collection, 'All')
    assert view.filters.navigation.currently_selected[0] == 'Status / Running (Default)'


def test_clear_host_filter_results(appliance):
    """ Test for clearing filter results for hosts."""
    host_collection = appliance.collections.hosts

    # TODO many parts of this test and others in this file need to be replaced with WT calls
    view = navigate_to(host_collection, 'All')
    view.filters.navigation.select('Status / Stopped')
    view.entities.search.remove_search_filters()
    page_title = view.title.text
    assert page_title == 'Hosts', 'Clear filter results failed'


def test_clear_datastore_filter_results(appliance):
    """ Test for clearing filter results for datastores."""
    dc = DatastoreCollection(appliance)
    view = navigate_to(dc, 'All')
    view.sidebar.datastores.tree.click_path('All Datastores', 'Global Filters',
                                            'Store Type / VMFS')
    view.entities.search.remove_search_filters()
    assert view.entities.title.text == 'All Datastores', 'Clear filter results failed'
