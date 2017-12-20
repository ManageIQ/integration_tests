import pytest

from cfme.cloud.provider.azure import AzureProvider
from cfme.exceptions import ManyEntitiesFound
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.meta(blockers=[BZ(1480577, forced_streams=["5.7", "5.8"])]),
    pytest.mark.provider([AzureProvider], scope="module")
]
FILETYPES = ["txt", "csv", "pdf"]
extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
OBJECTCOLLECTIONS = [
    'network_providers',
    'balancers',
    'cloud_networks',
    'network_ports',
    'network_security_groups',
    'network_subnets',
    'network_routers'
]


def download(objecttype, extension):
    view = navigate_to(objecttype, 'All')
    view.toolbar.download.item_select("Download as {}".format(extensions_mapping[extension]))


def download_summary(spec_object):
    view = navigate_to(spec_object, 'Details')
    view.toolbar.download.click()


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("collection_type", OBJECTCOLLECTIONS)
def test_download_lists_base(filetype, collection_type, appliance):
    """ Download the items from base lists. """
    collection = getattr(appliance.collections, collection_type)
    download(collection, filetype)


@pytest.mark.parametrize("collection_type", OBJECTCOLLECTIONS)
def test_download_pdf_summary(appliance, collection_type, provider):
    """ Download the summary details of specific object """
    collection = getattr(appliance.collections, collection_type)
    if collection.all():
        random_obj = collection.all()[0].name
        try:
            obj = collection.instantiate(random_obj)
            download_summary(obj)
        except ManyEntitiesFound:
            pass
