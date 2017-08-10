import pytest
from cfme.networks.provider import NetworkProvider
from cfme.networks.balancer import Balancer
from cfme.networks.cloud_network import CloudNetwork
from cfme.networks.network_port import NetworkPort
from cfme.cloud.provider.azure import AzureProvider
import cfme.web_ui.flash as flash
from utils import testgen
from utils import version
from utils.version import current_version
from functools import partial
from utils.appliance.implementations.ui import navigate_to
import cfme.web_ui.toolbar as tb


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([AzureProvider], scope="module")
FILETYPES = ["txt", "csv", "pdf"]
extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
download_btn = partial(tb.select, "Download")
download_summary_btn = partial(tb.select, "Download summary in PDF format")


def download(objecttype, extension):
    try:
        navigate_to(objecttype, 'All')
        download_btn("Download as {}".format(extensions_mapping[extension]))
    except:
        raise ValueError("Unknown extention. check the extentions_mapping")


def download_summary(spec_object):
    try:
        navigate_to(spec_object, 'Details')
        download_summary_btn()
    except:
        raise ValueError("Unknown extention. check the extentions_mapping")


@pytest.mark.uncollect
@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [NetworkProvider, Balancer,
                                        CloudNetwork, NetworkPort])
@pytest.mark.uncollectif(lambda filetype: filetype in {"pdf"} and
                         current_version() == version.UPSTREAM)
def test_download_lists_base(filetype, objecttype):
    ''' Download the items from base lists. '''
    download(objecttype, filetype)
    flash.assert_no_errors()


@pytest.mark.parametrize("objecttype", [NetworkProvider, Balancer,
                                        CloudNetwork, NetworkPort])
@pytest.mark.uncollectif(current_version() == version.UPSTREAM)
def test_download_pdf_summary(objecttype):
    ''' Download the summary details of specific object '''
    try:
        random_obj = objecttype.get_all()[0]
    except:
        return
    obj = objecttype(random_obj)
    download_summary(obj)
    flash.assert_no_errors()
