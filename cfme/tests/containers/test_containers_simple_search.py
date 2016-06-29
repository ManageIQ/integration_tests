import pytest
from itertools import product
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Table
from cfme.web_ui import search

from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(3)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


PROJECTS_SEARCH_STRINGS = ['*', 'infra', '$', 'management-infra']
ROUTES_SEARCH_STRINGS = ['*', 'front', '$', 'frontend']
table_el = '//table[contains(@class, ' \
           '"table table-striped table-bordered table-hover table-selectable")]'

# CMP-9871


@pytest.mark.parametrize('projects_search_strings', product(PROJECTS_SEARCH_STRINGS))
def test_projects_search(projects_search_strings):
    """ Projects summary page - Search bar

           This test checks Search bar functionality on the Projects summary page

           Steps:
               * Goes to Containers Projects page
               * Inserts: Irregular symbol, '*' character, full search string, partial search string
               * Verify proper results
           """
    if ''.join(projects_search_strings) == '*':
        sel.force_navigate('containers_projects')
        full_name_to_search = '*'
        names_list = []
        located_names = []
        projects_table = Table(table_el)
        for row in projects_table.rows():
            names_list.append(row.name.text)
        search.normal_search(full_name_to_search)
        for row in projects_table.rows():
            located_names.append(row.name.text)
        for name in located_names:
            assert name in names_list
    elif ''.join(projects_search_strings) == 'infra':
        sel.force_navigate('containers_projects')
        full_name_to_search = 'infra'
        search.normal_search(full_name_to_search)
        projects_table = Table(table_el)
        for row in projects_table.rows():
            name = row.name.text
            assert full_name_to_search in name
    elif ''.join(projects_search_strings) == '$':
        sel.force_navigate('containers_projects')
        full_name_to_search = '$'
        search.normal_search(full_name_to_search)
        assert sel.is_displayed_text("No Records Found.")
    else:
        sel.force_navigate('containers_projects')
        full_name_to_search = ''.join(projects_search_strings)
        search.normal_search(full_name_to_search)
        projects_table = Table(table_el)
        for row in projects_table.rows():
            name = row.name.text
            assert name == full_name_to_search


# CMP-9921

@pytest.mark.parametrize('routes_search_strings', product(ROUTES_SEARCH_STRINGS))
def test_routes_search(routes_search_strings):
    """ Routes summary page - Search bar

           This test checks Search bar functionality on the Routes summary page

           Steps:
               * Goes to Containers Routes page
               * Inserts: Irregular symbol, '*' character, full search string, partial search string
               * Verify proper results
           """
    if ''.join(routes_search_strings) == '*':
        sel.force_navigate('containers_routes')
        full_name_to_search = '*'
        names_list = []
        located_names = []
        projects_table = Table(table_el)
        for row in projects_table.rows():
            names_list.append(row.name.text)
        search.normal_search(full_name_to_search)
        for row in projects_table.rows():
            located_names.append(row.name.text)
        for name in located_names:
            assert name in names_list
    elif ''.join(routes_search_strings) == 'front':
        sel.force_navigate('containers_routes')
        full_name_to_search = 'front'
        search.normal_search(full_name_to_search)
        projects_table = Table(table_el)
        for row in projects_table.rows():
            name = row.name.text
            assert full_name_to_search in name
    elif ''.join(routes_search_strings) == '$':
        sel.force_navigate('containers_routes')
        full_name_to_search = '$'
        search.normal_search(full_name_to_search)
        assert sel.is_displayed_text("No Records Found.")
    else:
        sel.force_navigate('containers_routes')
        full_name_to_search = ''.join(routes_search_strings)
        search.normal_search(full_name_to_search)
        projects_table = Table(table_el)
        for row in projects_table.rows():
            name = row.name.text
            assert name == full_name_to_search
