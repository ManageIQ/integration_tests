# -*- coding: utf-8 -*-
from functools import partial

import pytest

from cfme.infrastructure import host, datastore
from cfme.login import login_admin, logout
from cfme.web_ui.search import search_box
from utils import version
from cfme.web_ui import accordion, listaccordion as list_acc
from utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.host import Host
from cfme.infrastructure.datastore import Datastore


pytestmark = [pytest.mark.tier(3), pytest.mark.usefixtures("virtualcenter_provider")]


def test_set_default_host_filter(request):
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


def test_clear_host_filter_results():
    """ Test for clearing filter results for hosts."""

    navigate_to(Host, 'All')
    list_acc.select('Filters', 'Status / Stopped', by_title=False)
    pytest.sel.click(search_box.clear_advanced_search)
    page_title = pytest.sel.text(host.page_title_loc)
    assert page_title == 'Hosts', 'Clear filter results failed'


@pytest.mark.uncollectif(lambda: version.current_version() >= "5.6")
def test_set_default_datastore_filter(request):
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


def test_clear_datastore_filter_results():
    """ Test for clearing filter results for datastores."""

    if version.current_version() >= 5.6:
        expected_page_title = 'All Datastores'
        datastore_select = partial(accordion.tree, 'Datastores', 'All Datastores', 'Global Filters',
            'Store Type / VMFS')
    else:
        expected_page_title = 'Datastores'
        datastore_select = partial(list_acc.select, 'Filters', 'Store Type / VMFS', by_title=False)

    navigate_to(Datastore, 'All')
    datastore_select()
    pytest.sel.click(search_box.clear_advanced_search)
    page_title = pytest.sel.text(datastore.page_title_loc)
    assert page_title == expected_page_title, 'Clear filter results failed'
