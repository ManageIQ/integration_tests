import pytest

from utils import testgen
from utils.soft_get import soft_get
from cfme.web_ui import breadcrumbs, summary_title
from cfme.fixtures import pytest_selenium as sel
from utils.version import current_version

from cfme.containers.service import Service
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.pod import Pod
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.image import Image
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.template import Template
from cfme.containers.volume import Volume
from cfme.containers.provider import ContainersProvider, navigate_and_get_rows


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


class DataSet(object):
    def __init__(self, obj, obj_base_name):
        self.obj = obj
        self.obj_base_name = obj_base_name


DATA_SETS = [
    DataSet(Service, 'service'),
    DataSet(Route, 'route'),
    DataSet(Project, 'project'),
    DataSet(Pod, 'pod'),
    DataSet(Image, 'image'),
    DataSet(ContainersProvider, 'provider'),
    DataSet(ImageRegistry, 'image regist'),
    DataSet(Node, 'node'),
    DataSet(Replicator, 'replicator'),
    DataSet(Template, 'template'),
    DataSet(Volume, 'volume')
]


@pytest.mark.polarion('CMP-10576')
def test_breadcrumbs(provider, soft_assert):

    for dataset in DATA_SETS:

        if current_version() < '5.7' and dataset.obj == Template:
            continue

        rows = navigate_and_get_rows(provider, dataset.obj, 1)
        if not rows:
            pytest.skip('Could not test breadcrums: No records found in {}\'s table'
                        .format(dataset.obj.__name__))
        row = rows[-1]
        instance_name = row[2].text
        row.click()

        breadcrumb_elements = breadcrumbs()
        soft_assert(breadcrumb_elements,
                    'Breadcrumbs not found in {} {} summary page'
                    .format(dataset.obj.__name__, instance_name))
        bread_names_2_element = {sel.text_sane(b): b for b in breadcrumb_elements}

        try:
            breadcrumb_element = soft_get(bread_names_2_element,
                                          dataset.obj_base_name, dict_=True)
        except:
            soft_assert(False,
                'Could not find breadcrumb "{}" in {} {} summary page. breadcrumbs: {}'
                .format(dataset.obj_base_name, bread_names_2_element.keys(),
                        dataset.obj.__name__, instance_name))

        breadcrumb_name = sel.text_sane(breadcrumb_element)
        sel.click(breadcrumb_element)

        # We verify the location as following since we want to prevent from name convention errors
        soft_assert(dataset.obj_base_name in summary_title().lower(),
            'Breadcrumb link "{}" in {} {} page should navigate to '
            '{}s main page. navigated instead to: {}'
            .format(breadcrumb_name, dataset.obj.__name__,
                    instance_name, dataset.obj.__name__,
                    sel.current_url()))
