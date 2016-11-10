import pytest
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.provider import ContainersProvider
from cfme.containers.node import Node
from cfme.containers.container import Container
from utils import testgen
from utils.version import current_version
from cfme.web_ui import history
from utils.appliance.implementations.ui import  navigate_to



pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    # pytest.mark.usefixtures('has_no_container_providers'),
    # pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

container_image_fields = ['Name', 'Image_Id', 'Full_Name']
container_nodes_fields = ['Name', 'Creation_timestamp', 'Resource_version', 'Number_of_CPU_Cores',
                          'Memory', 'Max_Pods_Capacity', 'System_BIOS_UUID', 'Machine_ID',
                          'Infrastructure_Machine_ID', 'Runtime_version', 'Kubelet_version',
                          'Proxy_version', 'Operating_System_Distribution', 'Kernel_version']
container_fields = ['Name', 'State', 'Restart_count', 'Backing_Ref_Container_ID', 'Privileged']
image_registry_field = ['Host']


# CMP-9945
def test_containers_integrity_properties():
    """ Properties fields test in Containers
        This test checks correct population of the Properties Fields in Containers' details menu
        Steps:
            * Goes to Containers -- > Containers menu
            * Go through each Containers in the menu and check validity of Properties fields
        """
    navigate_to(Container, 'All', use_resetter=False)
    container_names = Container.get_container_names()
    container_pod_names = Container.get_pod_names()
    dictionary = dict(zip(container_names, container_pod_names))
    for container_name, container_pod_name in dictionary.iteritems():
        for container_field in container_fields:
            pod = Pod(container_pod_name, ContainersProvider)
            cont = Container(container_name, pod)
            assert cont.summary.properties.__getattribute__(container_field.lower())
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
    image_registry_hosts = ImageRegistry.get_names()
    for host in image_registry_hosts:
        for image in image_registry_field:
            obj = ImageRegistry(host, provider)
            assert obj.summary.properties.__getattribute__(image.lower())


# CMP-9978
def test_containers_images_integrity_properties(provider):
    """ Properties fields test in Container Images
        This test checks correct population of the Properties Fields in Containers Image's
        details menu
        Steps:
            * Goes to Containers -- > Containers Images menu
            * Go through each Container Image in the menu and check validity of Properties fields
        """
    container_images_names = Image.get_names()
    for name in container_images_names:
        for image in container_image_fields:
            obj = Image(name, provider)
            assert obj.summary.properties.__getattribute__(image.lower())


# CMP-9960
def test_containers_nodes_integrity_properties(provider):
    """ Properties fields test in Container Nodes
        This test checks correct population of the Properties Fields in Container Nodes'
        details menu
        Steps:
            * Goes to Containers -- > Container Nodes menu
            * Go through each Container in the menu and check validity of Properties fields
        """
    container_nodes_names = Node.get_names()
    for name in container_nodes_names:
        for node_field in container_nodes_fields:
            obj = Node(name, provider)
            assert obj.summary.properties.__getattribute__(node_field.lower())


