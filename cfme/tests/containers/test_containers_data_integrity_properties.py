import pytest
from cfme.fixtures import pytest_selenium as sel
from itertools import product
from cfme.web_ui import CheckboxTable
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.provider import Provider
from cfme.containers.node import Node
from cfme.containers.container import Container
from utils import testgen
from utils.version import current_version

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

CONTAINERS_IMAGES_FIELDS = ['Name', 'Image Id', 'Full Name']
CONTAINERS_NODES_FIELDS = ['Name', 'Creation timestamp', 'Resource version', 'Number of CPU Cores',
                           'Memory', 'Max Pods Capacity', 'System BIOS UUID', 'Machine ID',
                           'Infrastructure Machine ID', 'Runtime version', 'Kubelet version',
                           'Proxy version', 'Operating System Distribution', 'Kernel version']
CONTAINERS_FIELDS = ['Name', 'State', 'Restart count', 'Backing Ref (Container ID)', 'Privileged']
IMAGE_REGISTRY_FIELDS = ['Host']


# CMP-9945

@pytest.mark.parametrize('container_fields', product(CONTAINERS_FIELDS))
def test_containers_data_containers_integrity_properties(container_fields):
    """ Container details page > Properties fields
        This test checks correct population of the Properties Fields in Containers' details menu
        Steps:
            * Goes to Containers -- > Containers menu
            * Go through each Container in the menu and check validity of Properties fields
        """
    sel.force_navigate('containers_containers')
    container_name = [r.name.text for r in list_tbl.rows()]
    container_pod_name = [r.pod_name.text for r in list_tbl.rows()]
    dictionary = dict(zip(container_name, container_pod_name))
    for container_name, container_pod_name in dictionary.iteritems():
        pod = Pod(container_pod_name, Provider)
        cont = Container(container_name, pod)
        val = cont.get_detail('Properties', ''.join(container_fields))
        assert val
        sel.click("//i[@class='fa fa-arrow-left fa-lg']")
        sel.click("//a[@data-click='history_choice__history_1']")


# CMP-9988
# Check how to add an Image Registry with code
@pytest.mark.parametrize('image_registry_fields', product(IMAGE_REGISTRY_FIELDS))
def test_containers_image_registries_integrity_properties(provider, image_registry_fields):
    """ Image Registry details page > Properties fields
        This test checks correct population of the Properties Fields in Image Registry's
        details menu.
        Prerequisites: Image Registries in CFME
        Steps:
            * Goes to Containers -- > Image Registries menu
            * Go through each Image Registry in the menu and check validity of Properties fields
        """
    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    sel.force_navigate('containers_image_registries')
    image_registry_hosts = [r.host.text for r in list_tbl.rows()]
    for host in image_registry_hosts:
        obj = ImageRegistry(host, provider)
        val = obj.get_detail('Properties', ''.join(image_registry_fields))
        assert val


# CMP-9978


@pytest.mark.parametrize('container_image_fields', product(CONTAINERS_IMAGES_FIELDS))
def test_containers_data_containers_images_integrity_properties(provider, container_image_fields):
    """ Container Image details page > Properties fields
        This test checks correct population of the Properties Fields in Containers Image's
        details menu
        Steps:
            * Goes to Containers -- > Containers Images menu
            * Go through each Container Image in the menu and check validity of Properties fields
        """
    sel.force_navigate('containers_images')
    container_images_name = [r.name.text for r in list_tbl.rows()]
    for name in container_images_name:
        obj = Image(name, provider)
        val = obj.get_detail('Properties', ''.join(container_image_fields))
        assert val


# CMP-9960


@pytest.mark.parametrize('container_nodes_fields', product(CONTAINERS_NODES_FIELDS))
def test_containers_data_containers_nodes_integrity_properties(provider, container_nodes_fields):
    """ Container Nodes details page > Properties fields
        This test checks correct population of the Properties Fields in Container Nodes'
        details menu
        Steps:
            * Goes to Containers -- > Container Nodes menu
            * Go through each Container in the menu and check validity of Properties fields
        """
    sel.force_navigate('containers_nodes')
    container_nodes_name = [r.name.text for r in list_tbl.rows()]
    for name in container_nodes_name:
        obj = Node(name, provider)
        val = obj.get_detail('Properties', ''.join(container_nodes_fields))
        assert val
