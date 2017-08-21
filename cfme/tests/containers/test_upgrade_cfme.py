import pytest
from utils import testgen

from utils.version import current_version

from cfme.configure.configuration import Tag
from cfme.containers.provider import ContainersProvider
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.node import Node
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.pod import Pod
from cfme.containers.template import Template
from cfme.containers.container import Container
from cfme.containers.provider import navigate_and_get_rows


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

ITEMS_TO_SAMPLE = [Tag, ContainersProvider, Image, Project, Node,
                   ImageRegistry, Pod, Template, Container]
MAX_SAMPLES_PER_OBJECT = 10


def save_object_state(provider, object):
    rows = navigate_and_get_rows(provider, object, MAX_SAMPLES_PER_OBJECT)
    headers_mapping = {header.text: indx for
                       indx, header in enumerate(rows[0].table.headers) if header.text}

    all_instance = {}

    for instance in rows:
        curr_instance_name = None
        curr_instance_values = {}
        for filed in headers_mapping:
            if filed == "Name":
                curr_instance_name = instance.table.headers[filed].text
            else:
                curr_instance_values[filed] = instance.table.headers[filed].text
        all_instance[curr_instance_name] = curr_instance_values
    return all_instance


def test_pre_upgrade_status_save():
    pass


def test_post_upgrade_status_validation():
    pass
