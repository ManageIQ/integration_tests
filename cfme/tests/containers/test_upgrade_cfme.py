import pytest
import yaml
from utils import testgen
from utils.version import current_version
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

ITEMS_TO_SAMPLE = [ContainersProvider, Image, Project, Node,
                   ImageRegistry, Pod, Template, Container]
MAX_SAMPLES_PER_OBJECT = 10


def save_object_state(provider, obj):
    rows = navigate_and_get_rows(provider, obj, MAX_SAMPLES_PER_OBJECT)
    headers_mapping = {str(header.text): indx for indx, header in
                       enumerate(rows[0].table.headers) if header.text}

    all_instance = {"main_key": None, "values": {}}

    # Get the most left column on the table to be the main key
    main_key = min(headers_mapping, key=headers_mapping.get)

    # Save main_key as metadata for case table change between CFME version
    all_instance["main_key"] = main_key

    for instance in rows:
        curr_instance_name = str(instance[main_key].text)

        # collect all instance values
        all_instance["values"][curr_instance_name] = \
            {filed: str(instance.columns[headers_mapping[filed]].text) for
             filed in set(headers_mapping) - set([main_key])}

    return all_instance


def test_pre_upgrade_status_save(provider):

    all_samples = {obj.__name__: save_object_state(provider, obj) for obj in ITEMS_TO_SAMPLE}
    all_data = {"current_version": current_version().vstring, "samples": all_samples}

    output_file_name = "/tmp/upgrade_test_output.yaml"
    with open(output_file_name, "w") as output_file:
        yaml.dump(all_data, output_file, default_flow_style=False)


def test_post_upgrade_status_validation():
    pass
