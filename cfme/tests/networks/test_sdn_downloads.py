import pytest
from cfme.cloud.provider.azure import AzureProvider
from cfme.networks.balancer import (Balancer, BalancerCollection)
from cfme.networks.cloud_network import (CloudNetwork, CloudNetworkCollection)
from cfme.networks.network_port import (NetworkPort, NetworkPortCollection)
from cfme.networks.network_router import (NetworkRouter, NetworkRouterCollection)
from cfme.networks.provider import (NetworkProvider, NetworkProviderCollection)
from cfme.networks.security_group import (SecurityGroup, SecurityGroupCollection)
from cfme.networks.subnet import (Subnet, SubnetCollection)
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.blockers import BZ


pytest_generate_tests = testgen.generate([AzureProvider], scope="module")
pytestmark = pytest.mark.usefixtures('setup_provider')
FILETYPES = ["txt", "csv", "pdf"]
extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}


def download(objecttype, extension):
    view = navigate_to(objecttype, 'All')
    view.toolbar.download.item_select("Download as {}".format(extensions_mapping[extension]))


def download_summary(spec_object):
    view = navigate_to(spec_object, 'Details')
    view.toolbar.download.click()


@pytest.mark.meta(blockers=[BZ(1480577, forced_streams=["5.7", "5.8"])])
@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [NetworkProvider, Balancer,
                                        CloudNetwork, NetworkPort,
                                        SecurityGroup, NetworkRouter,
                                        Subnet])
def test_download_lists_base(filetype, objecttype):
    ''' Download the items from base lists. '''
    download(objecttype, filetype)


@pytest.mark.meta(blockers=[BZ(1480577, forced_streams=["5.7", "5.8"])])
@pytest.mark.parametrize("objecttype", [NetworkProviderCollection, BalancerCollection,
                                        CloudNetworkCollection, NetworkPortCollection,
                                        SecurityGroupCollection, SubnetCollection,
                                        NetworkRouterCollection])
def test_download_pdf_summary(objecttype, provider):
    ''' Download the summary details of specific object '''
    instance = objecttype()
    if instance.all():
        random_obj = instance.all()[0].name
        obj = instance.instantiate(random_obj)
        download_summary(obj)
