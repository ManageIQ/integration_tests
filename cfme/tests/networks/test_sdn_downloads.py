import pytest
import random

from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.version import LATEST

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.meta(blockers=[BZ(1480577, forced_streams=["5.7", "5.8"])]),
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


def download(appliance, objecttype, extension):
    view = navigate_to(objecttype, 'All')
    if appliance.version >= '5.10' and extension == 'pdf':
        view.toolbar.download.item_select("Print or export as PDF")
    else:
        view.toolbar.download.item_select("Download as {}".format(extensions_mapping[extension]))


def download_summary(spec_object):
    view = navigate_to(spec_object, 'Details')
    view.toolbar.download.click()


@pytest.mark.parametrize("filetype", extensions_mapping.keys())
@pytest.mark.parametrize("collection_type", OBJECTCOLLECTIONS)
@pytest.mark.uncollectif(
    lambda appliance, filetype: appliance.version == LATEST and filetype == 'pdf'
)
def test_download_lists_base(filetype, collection_type, appliance):
    """ Download the items from base lists.

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: mmojzis
        initialEstimate: 1/10h
    """
    collection = getattr(appliance.collections, collection_type)
    download(appliance, collection, filetype)


@pytest.mark.uncollectif(
    lambda appliance: appliance.version == LATEST
)
@pytest.mark.parametrize("collection_type", OBJECTCOLLECTIONS)
def test_download_pdf_summary(appliance, collection_type, provider):
    """ Download the summary details of specific object

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: jhenner
        initialEstimate: 1/10h
    """
    collection = getattr(appliance.collections, collection_type)
    all_entities = collection.all()
    if all_entities:
        random_obj = random.choice(all_entities)
        download_summary(random_obj)
    else:
        pytest.skip('{} entities not available'.format(collection_type))


@pytest.mark.manual
@pytest.mark.tier(1)
def test_pdf_summary_infra_provider():
    """
    https://bugzilla.redhat.com/show_bug.cgi?id=1651194

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        caseautomation: manualonly
        initialEstimate: 1/8h
        testSteps:
            1. Add an Infrastructure Provider (tested with VMware)
            2. Open the summary page of the provider
            3. In the toolbar click "Print or export summary"
            = Quadicon is shown correctly, exactly as in the UI
    """
    pass
