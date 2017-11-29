import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.exceptions import ManyEntitiesFound
from cfme.networks.balancer import BalancerCollection
from cfme.networks.cloud_network import CloudNetworkCollection
from cfme.networks.network_port import NetworkPortCollection
from cfme.networks.network_router import NetworkRouterCollection
from cfme.networks.provider import NetworkProviderCollection
from cfme.networks.security_group import SecurityGroupCollection
from cfme.networks.subnet import SubnetCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.meta(blockers=[BZ(1480577, forced_streams=["5.7", "5.8"])]),
    pytest.mark.provider([AzureProvider], scope="module")
]
FILETYPES = ["txt", "csv", "pdf"]
extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
OBJECTCOLLECTIONS = [NetworkProviderCollection, BalancerCollection, CloudNetworkCollection,
                     NetworkPortCollection, SecurityGroupCollection, SubnetCollection,
                     NetworkRouterCollection]


def download(objecttype, extension):
    view = navigate_to(objecttype, 'All')
    view.toolbar.download.item_select("Download as {}".format(extensions_mapping[extension]))


def download_summary(spec_object):
    view = navigate_to(spec_object, 'Details')
    view.toolbar.download.click()


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", OBJECTCOLLECTIONS)
def test_download_lists_base(filetype, objecttype, appliance):
    """ Download the items from base lists. """
    download(appliance.get(objecttype), filetype)


@pytest.mark.parametrize("collection", OBJECTCOLLECTIONS)
def test_download_pdf_summary(appliance, collection, provider):
    """ Download the summary details of specific object """
    instance = collection(appliance)
    if instance.all():
        random_obj = instance.all()[0].name
        try:
            obj = instance.instantiate(random_obj)
            download_summary(obj)
        except ManyEntitiesFound:
            pass
