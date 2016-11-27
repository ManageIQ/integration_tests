import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.pod import list_tbl
from utils import testgen
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.service import Service
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider
from random import choice
from cfme.web_ui import breadcrumbs
from collections import namedtuple
from cfme.web_ui import toolbar as tb


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP_9903  CMP_9904  CMP_9905  CMP_9906

DataSet = namedtuple('DataSet', ['object', 'breadcrumb_member'])

DATA_SETS = [DataSet(Service, 'Container Services'),
             DataSet(Route, 'Routes'),
             DataSet(Project, 'Projects'),
             DataSet(ContainersProvider, 'Containers Providers')]


@pytest.mark.parametrize(('cls'), DATA_SETS, ids=[cls.object.__name__ for cls in DATA_SETS])
def test_summary_pages_links(provider, cls):

    navigate_to(cls.object, 'All')
    all_url = sel.current_url()
    tb.select('List View')
    name = choice([r[2].text for r in list_tbl.rows()])
    obj = cls.object(name, provider)
    obj.summary  # <- reload summary

    breads = breadcrumbs()
    bread_names = map(sel.text_sane, breads)

    if cls.breadcrumb_member.startswith('Container') and\
       cls.breadcrumb_member not in bread_names:
        breadcrumb_member = cls.breadcrumb_member.split(' ')[-1]
    else:
        breadcrumb_member = cls.breadcrumb_member

    assert breadcrumb_member in bread_names

    chosen_link = next(b for b in breads
                       if sel.text_sane(b) == breadcrumb_member)

    sel.click(chosen_link)

    # TODO: replace with widgetastic view.is_displayed function when available
    assert sel.current_url().split('?')[0] == all_url.split('?')[0]
