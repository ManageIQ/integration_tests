import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.provider import Provider
from cfme.containers.node import Node
from cfme.containers.container import Container
from utils import testgen
from utils.version import current_version
from cfme.web_ui import history

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

container_image_fields = ['Name', 'Image Id', 'Full Name']
container_nodes_fields = ['Name', 'Creation timestamp', 'Resource version', 'Number of CPU Cores',
                          'Memory', 'Max Pods Capacity', 'System BIOS UUID', 'Machine ID',
                          'Infrastructure Machine ID', 'Runtime version', 'Kubelet version',
                          'Proxy version', 'Operating System Distribution', 'Kernel version']
container_fields = ['Name', 'State', 'Restart count', 'Backing Ref (Container ID)', 'Privileged']
image_registry_field = ['Host']


# CMP-9945
def test_containers_integrity_properties():
    """ Properties fields test in Containers
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
        for container_field in container_fields:
            pod = Pod(container_pod_name, Provider)
            cont = Container(container_name, pod)
            val = cont.get_detail('Properties', container_field)
            assert val
            history.select_nth_history_item(0)


# CMP-9988
def test_containers_image_registries_integrity_properties(provider):
    """ Properties fields test in Image Registries
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
        for image in image_registry_field:
            obj = ImageRegistry(host, provider)
            val = obj.get_detail('Properties', image)
            assert val


# CMP-9978
def test_containers_images_integrity_properties(provider):
    """ Properties fields test in Container Images
        This test checks correct population of the Properties Fields in Containers Image's
        details menu
        Steps:
            * Goes to Containers -- > Containers Images menu
            * Go through each Container Image in the menu and check validity of Properties fields
        """
    sel.force_navigate('containers_images')
    container_images_name = [r.name.text for r in list_tbl.rows()]
    for name in container_images_name:
        for image in container_image_fields:
            obj = Image(name, provider)
            val = obj.get_detail('Properties', image)
            assert val


# CMP-9960
def test_containers_nodes_integrity_properties(provider):
    """ Properties fields test in Container Nodes
        This test checks correct population of the Properties Fields in Container Nodes'
        details menu
        Steps:
            * Goes to Containers -- > Container Nodes menu
            * Go through each Container in the menu and check validity of Properties fields
        """
    sel.force_navigate('containers_nodes')
    container_nodes_name = [r.name.text for r in list_tbl.rows()]
    for name in container_nodes_name:
        for node_field in container_nodes_fields:
            obj = Node(name, provider)
            val = obj.get_detail('Properties', node_field)
            assert val
