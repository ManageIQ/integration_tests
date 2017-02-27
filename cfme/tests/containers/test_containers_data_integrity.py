import pytest
import random
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.provider import ContainersProvider
from cfme.containers.node import Node
from cfme.containers.container import Container
from utils import testgen
from utils.version import current_version
from cfme.web_ui import history


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
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
            * Select a random Container in the menu and check validity of its' Properties fields
        """
    container_names = Container.get_container_names()
    container_pod_names = Container.get_pod_names()
    dictionary = dict(zip(container_names, container_pod_names))
    random_container_name = random.choice(dictionary.keys())
    random_container_pod_name = dictionary.get(random_container_name)
    for container_field in container_fields:
        pod = Pod(random_container_pod_name, ContainersProvider)
        cont = Container(random_container_name, pod.name)
        assert getattr(cont.summary.properties, container_field.lower())
        history.select_nth_history_item(0)


# CMP-9988
def test_containers_image_registries_integrity_properties(provider):
    """ Properties fields test in Image Registries
        This test checks correct population of the Properties Fields in Image Registry's
        details menu.
        Prerequisites: Image Registries in CFME
        Steps:
            * Goes to Containers -- > Image Registries menu
            * Select a random Image Registry in the menu and check
            validity of its' Properties fields
        """
    random_image_registry_host = random.choice(ImageRegistry.get_names())
    for image in image_registry_field:
        obj = ImageRegistry(random_image_registry_host, provider)
        assert getattr(obj.summary.properties, image.lower())


# CMP-9978
def test_containers_images_integrity_properties(provider):
    """ Properties fields test in Container Images
        This test checks correct population of the Properties Fields in Container Image's
        details menu
        Steps:
            * Goes to Containers -- > Containers Images menu
            * Select a random Container Image in the menu and check
            validity of its' Properties fields
        """
    random_container_image_name = random.choice(Image.get_names())
    for image in container_image_fields:
        obj = Image(random_container_image_name, provider)
        assert getattr(obj.summary.properties, image.lower())


# CMP-9960
def test_containers_nodes_integrity_properties(provider):
    """ Properties fields test in Container Nodes
        This test checks correct population of the Properties Fields in Container Nodes'
        details menu
        Steps:
            * Goes to Containers -- > Container Nodes menu
            * Select a random Node in the menu and check validity of its' Properties fields
        """
    random_container_node_name = random.choice(Node.get_names())
    for node_field in container_nodes_fields:
        obj = Node(random_container_node_name, provider)
        assert getattr(obj.summary.properties, node_field.lower())
