import pytest

from utils import testgen
from utils.soft_get import soft_get
from cfme.web_ui import breadcrumbs, summary_title
from cfme.fixtures import pytest_selenium as sel
from utils.version import current_version

from cfme.containers.service import Service, list_tbl as service_list_tbl
from cfme.containers.route import Route, list_tbl as route_list_tbl
from cfme.containers.project import Project, list_tbl as project_list_tbl
from cfme.containers.container import list_tbl as container_list_tbl
from cfme.containers.pod import Pod, list_tbl as pod_list_tbl
from cfme.containers.image_registry import ImageRegistry, \
    list_tbl as image_registry_list_tbl
from cfme.containers.image import Image, list_tbl as image_list_tbl
from cfme.containers.node import Node, list_tbl as node_list_tbl
from cfme.containers.replicator import Replicator, list_tbl as replicator_list_tbl
from cfme.containers.template import Template, list_tbl as template_list_tbl
from cfme.containers.provider import ContainersProvider, navigate_and_get_rows


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


class DataSet(object):
    def __init__(self, obj, list_tbl, obj_base_name):
        self.obj = obj
        self.list_tbl = list_tbl
        self.obj_base_name = obj_base_name


DATA_SETS = [
    DataSet(Service, service_list_tbl, 'service'),
    DataSet(Route, route_list_tbl, 'route'),
    DataSet(Project, project_list_tbl, 'project'),
    DataSet(Pod, pod_list_tbl, 'pod'),
    DataSet(Image, image_list_tbl, 'image'),
    DataSet(ContainersProvider, container_list_tbl, 'provider'),
    DataSet(ImageRegistry, image_registry_list_tbl, 'image regist'),
    DataSet(Node, node_list_tbl, 'node'),
    DataSet(Replicator, replicator_list_tbl, 'replicator'),
    DataSet(Template, template_list_tbl, 'template')
]


@pytest.mark.polarion('CMP-10567')
def test_breadcrumbs(provider, soft_assert):

    for dataset in DATA_SETS:

        if current_version() < '5.7' and dataset.obj == Template:
            continue

        rows = navigate_and_get_rows(provider, dataset.obj, dataset.list_tbl, 1)
        if not rows:
            pytest.skip('Could not test breadcrums: No records found in {}\'s table'
                        .format(dataset.obj.__name__))
        row = rows[-1]
        instance_name = row[2].text
        sel.click(row)

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
