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
from utils import version
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version


pytest_generate_tests = testgen.generate([AzureProvider], scope="module")
pytestmark = pytest.mark.usefixtures('setup_provider')
FILETYPES = ["txt", "csv", "pdf"]
extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}


def download(objecttype, extension):
    try:
        view = navigate_to(objecttype, 'All')
        view.toolbar.download.item_select("Download as {}".format(extensions_mapping[extension]))
    except Exception:
        raise ValueError("Unknown extention. check the extentions_mapping")


def download_summary(spec_object):
    try:
        view = navigate_to(spec_object, 'Details')
        view.toolbar.download.click()
    except Exception:
        raise ValueError("Unknown extention. check the extentions_mapping")


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [NetworkProvider, Balancer,
                                        CloudNetwork, NetworkPort,
                                        SecurityGroup, NetworkRouter,
                                        Subnet])
@pytest.mark.uncollectif(lambda filetype: filetype in {"pdf"} and
                         current_version() == version.UPSTREAM)
def test_download_lists_base(filetype, objecttype):
    ''' Download the items from base lists. '''
    download(objecttype, filetype)


@pytest.mark.parametrize("objecttype", [NetworkProviderCollection, BalancerCollection,
                                        CloudNetworkCollection, NetworkPortCollection,
                                        SecurityGroupCollection, SubnetCollection,
                                        NetworkRouterCollection])
@pytest.mark.uncollectif(current_version() == version.UPSTREAM)
def test_download_pdf_summary(objecttype, provider):
    ''' Download the summary details of specific object '''
    instance = objecttype()
    if instance.all():
        random_obj = instance.all()[0].name
        obj = instance.instantiate(random_obj)
        download_summary(obj)
