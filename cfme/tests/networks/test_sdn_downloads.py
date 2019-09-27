import random

import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.sdn,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([AzureProvider, EC2Provider, GCEProvider, OpenStackProvider],
                         scope="module")
]

extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
OBJECTCOLLECTIONS = [
    'network_providers',
    'balancers',
    'cloud_networks',
    'network_ports',
    'network_security_groups',
    'network_subnets',
    'network_routers',

]


def download(objecttype, extension):
    view = navigate_to(objecttype, 'All')
    if view.browser.product_version >= '5.10' and extension == 'pdf':
        view.toolbar.download.item_select("Print or export as PDF")
        handle_extra_tabs(view)
    else:
        view.toolbar.download.item_select("Download as {}".format(extensions_mapping[extension]))


def download_summary(spec_object):
    view = navigate_to(spec_object, 'Details')
    view.toolbar.download.click()
    if view.browser.product_version >= '5.10':
        handle_extra_tabs(view)


def handle_extra_tabs(view):
    tabs = view.browser.selenium.window_handles
    while len(tabs) > 1:
        view.browser.selenium.switch_to_window(tabs[-1])
        view.browser.selenium.close()
        tabs = view.browser.selenium.window_handles
    view.browser.selenium.switch_to_window(tabs[0])


@pytest.mark.parametrize("filetype", list(extensions_mapping.keys()))
@pytest.mark.parametrize("collection_type", OBJECTCOLLECTIONS)
@pytest.mark.uncollectif(
    lambda collection_type, appliance:
    "balancers" in collection_type and appliance.version > "5.11",
    reason="Cloud Load Balancers are removed in 5.11, see BZ 1672949")
def test_download_lists_base(filetype, collection_type, appliance):
    """ Download the items from base lists.

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/10h
        casecomponent: WebUI
        caseimportance: medium
    """
    collection = getattr(appliance.collections, collection_type)
    download(collection, filetype)


@pytest.mark.uncollectif(
    lambda collection_type, appliance:
    "balancers" in collection_type and appliance.version > "5.11",
    reason="Cloud Load Balancers are removed in 5.11, see BZ 1672949")
@pytest.mark.parametrize("collection_type", OBJECTCOLLECTIONS)
def test_download_pdf_summary(appliance, collection_type, provider):
    """ Download the summary details of specific object

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/10h
        casecomponent: WebUI
        caseimportance: medium
    """
    collection = getattr(appliance.collections, collection_type)
    all_entities = collection.all()
    if all_entities:
        random_obj = random.choice(all_entities)
        download_summary(random_obj)
    else:
        pytest.skip('{} entities not available'.format(collection_type))
