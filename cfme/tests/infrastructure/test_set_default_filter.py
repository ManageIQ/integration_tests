# -*- coding: utf-8 -*-
import pytest

from cfme.infrastructure import host, datastore
from cfme.web_ui.search import search_box
from cfme.utils import version
from cfme.web_ui import listaccordion as list_acc
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.host import Host
from cfme.infrastructure.datastore import Datastore


pytestmark = [pytest.mark.tier(3), pytest.mark.usefixtures("virtualcenter_provider")]


def test_set_default_host_filter(request, appliance):
    """ Test for setting default filter for hosts."""

    # Add cleanup finalizer
    def unset_default_host_filter():
        navigate_to(Host, 'All')
        list_acc.select('Filters', 'ALL', by_title=False)
        pytest.sel.click(host.default_host_filter_btn)
    request.addfinalizer(unset_default_host_filter)

    navigate_to(Host, 'All')
    list_acc.select('Filters', 'Status / Running', by_title=False)
    pytest.sel.click(host.default_host_filter_btn)
    appliance.server.logout()
    appliance.server.login_admin()
    navigate_to(Host, 'All')
    assert list_acc.is_selected('Filters', 'Status / Running (Default)', by_title=False),\
        'Status / Running filter not set as default'


def test_clear_host_filter_results():
    """ Test for clearing filter results for hosts."""

    navigate_to(Host, 'All')
    list_acc.select('Filters', 'Status / Stopped', by_title=False)
    pytest.sel.click(search_box.clear_advanced_search)
    page_title = pytest.sel.text(host.page_title_loc)
    assert page_title == 'Hosts', 'Clear filter results failed'


@pytest.mark.uncollectif(lambda: version.current_version() >= "5.6")
def test_set_default_datastore_filter(request, appliance):
    """ Test for setting default filter for datastores."""

    # I guess this test has to be redesigned
    # Add cleanup finalizer
    def unset_default_datastore_filter():
        navigate_to(Datastore, 'All')
        list_acc.select('Filters', 'ALL', by_title=False)
        pytest.sel.click(datastore.default_datastore_filter_btn)
    request.addfinalizer(unset_default_datastore_filter)

    navigate_to(Datastore, 'All')
    list_acc.select('Filters', 'Store Type / NFS', by_title=False)
    pytest.sel.click(datastore.default_datastore_filter_btn)
    appliance.server.logout()
    appliance.server.login_admin()
    navigate_to(Datastore, 'All')
    assert list_acc.is_selected('Filters', 'Store Type / NFS (Default)', by_title=False),\
        'Store Type / NFS not set as default'


def test_clear_datastore_filter_results():
    """ Test for clearing filter results for datastores."""
    view = navigate_to(Datastore, 'All')
    view.sidebar.datastores.tree.click_path('Datastores', 'All Datastores', 'Global Filters',
                                            'Store Type / VMFS')
    view.entities.search.clear_search()
    assert view.entities.title.text == 'All Datastores', 'Clear filter results failed'
