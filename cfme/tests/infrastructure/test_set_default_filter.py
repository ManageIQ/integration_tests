# -*- coding: utf-8 -*-

import pytest

from cfme.login import login_admin, logout
from cfme.web_ui.search import search_box
from cfme.infrastructure import host, datastore
from utils.providers import setup_a_provider
from utils import version
from cfme.web_ui import accordion, listaccordion as list_acc
from utils.appliance.endpoints.ui import navigate_to
from cfme.infrastructure.host import Host
from cfme.infrastructure.datastore import Datastore


@pytest.fixture(scope="module")
def provider():
    return setup_a_provider(prov_class="infra", prov_type="virtualcenter")


pytestmark = [pytest.mark.tier(3)]


def test_set_default_host_filter(provider, request):
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
    logout()
    login_admin()
    navigate_to(Host, 'All')
    assert list_acc.is_selected('Filters', 'Status / Running (Default)', by_title=False),\
        'Status / Running filter not set as default'


def test_clear_host_filter_results(provider):
    """ Test for clearing filter results for hosts."""

    navigate_to(Host, 'All')
    list_acc.select('Filters', 'Status / Stopped', by_title=False)
    pytest.sel.click(search_box.clear_advanced_search)
    page_title = pytest.sel.text(host.page_title_loc)
    assert page_title == 'Hosts', 'Clear filter results failed'


@pytest.mark.uncollectif(lambda: version.current_version() >= "5.6")
def test_set_default_datastore_filter(provider, request):
    """ Test for setting default filter for datastores."""

    # Add cleanup finalizer
    def unset_default_datastore_filter():
        navigate_to(Datastore, 'All')
        list_acc.select('Filters', 'ALL', by_title=False)
        pytest.sel.click(datastore.default_datastore_filter_btn)
    request.addfinalizer(unset_default_datastore_filter)

    navigate_to(Datastore, 'All')
    list_acc.select('Filters', 'Store Type / NFS', by_title=False)
    pytest.sel.click(datastore.default_datastore_filter_btn)
    logout()
    login_admin()
    navigate_to(Datastore, 'All')
    assert list_acc.is_selected('Filters', 'Store Type / NFS (Default)', by_title=False),\
        'Store Type / NFS not set as default'


def test_clear_datastore_filter_results(provider):
    """ Test for clearing filter results for datastores."""

    if version.current_version() >= 5.6:
        expected_page_title = 'All Datastores'
        datastore_select = lambda: accordion.tree('Datastores', 'All Datastores', 'Global Filters',
            'Store Type / VMFS')
    else:
        expected_page_title = 'Datastores'
        datastore_select = lambda: list_acc.select('Filters', 'Store Type / VMFS', by_title=False)

    navigate_to(Datastore, 'All')
    datastore_select()
    pytest.sel.click(search_box.clear_advanced_search)
    page_title = pytest.sel.text(datastore.page_title_loc)
    assert page_title == expected_page_title, 'Clear filter results failed'
