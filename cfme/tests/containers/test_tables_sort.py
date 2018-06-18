import pytest

from widgetastic.utils import attributize_string

from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.replicator import Replicator
from cfme.containers.route import Route
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9924')(ContainersTestItem(
        ContainersProvider, 'CMP-9924', collection_name=None)),
    pytest.mark.polarion('CMP-9926')(ContainersTestItem(
        Route, 'CMP-9926', collection_name='container_routes')),
    pytest.mark.polarion('CMP-9928')(ContainersTestItem(
        Replicator, 'CMP-9928', collection_name='container_replicators'))
]


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ti.args[1].pretty_id() for ti in TEST_ITEMS])
def test_tables_sort(test_item, soft_assert, appliance):

    view = navigate_to((test_item.obj if test_item.obj is ContainersProvider
        else getattr(appliance.collections, test_item.collection_name)), 'All')
    view.toolbar.view_selector.select('List View')
    view.entities.paginator.set_items_per_page(1000)

    for col, header_text in enumerate(view.entities.elements.headers):
        if not header_text:
            continue
        # Checking both orders
        view.entities.elements.sort_by(column=header_text, order='asc')
        # sorted_by returns attributized string
        # in CFME 5.8, the sort on IP Address column for container providers fails to sort?
        soft_assert((view.entities.elements.sorted_by == attributize_string(header_text) and
                    view.entities.elements.sort_order == 'asc'),
                    'Failed checking sorted_by {} and sort_order asc'.format(header_text))
        rows_ascending = [r[col].text for r in view.entities.elements.rows()]
        # opposite sort order
        view.entities.elements.sort_by(column=header_text, order='desc')
        soft_assert((view.entities.elements.sorted_by == attributize_string(header_text) and
                    view.entities.elements.sort_order == 'desc'),
                    'Failed checking sorted_by {} and sort_order desc'.format(header_text))
        rows_descending = [r[col].text for r in view.entities.elements.rows()]

        soft_assert(
            rows_ascending[::-1] == rows_descending,
            'Malfunction in the table sort: {} != {}'.format(
                rows_ascending[::-1], rows_descending
            )
        )
