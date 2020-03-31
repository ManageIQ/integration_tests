import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    test_requirements.general_ui,
    pytest.mark.tier(3),
    pytest.mark.ignore_stream("upstream")
]


@pytest.fixture(scope="module")
def some_dialogs(appliance, request):
    to_delete = []
    request.addfinalizer(lambda: [obj.delete() for obj in to_delete])
    for i in range(6):
        random_str = fauxfactory.gen_alphanumeric(16)
        element_data = {
            'element_information': {
                'ele_label': f"ele_{random_str}",
                'ele_name': format(random_str),
                'ele_desc': format(random_str),
                'choose_type': "Check Box"
            }
        }
        service_dialogs = appliance.collections.service_dialogs
        sd = service_dialogs.create(label=f'test_paginator_{random_str}',
                                    description="my dialog")
        tab = sd.tabs.create(tab_label=f'tab_{random_str}',
                tab_desc="my tab desc")
        box = tab.boxes.create(box_label=f'box_{random_str}',
                box_desc="my box desc")
        box.elements.create(element_data=[element_data])
        to_delete.append(sd)
    return to_delete


def get_relevant_rows(table):
    result = []
    for row in table.rows():
        text = row.label.text
        if text.startswith("test_paginator_"):
            result.append(text)
    return result


@test_requirements.general_ui
@pytest.mark.meta(blocks=[1125230, 1205235])
@pytest.mark.tier(3)
def test_paginator_service_dialogs(some_dialogs, soft_assert, appliance):
    """ This test tests weird behaviour of the paginator in Service dialogs.

    Prerequisities:
        * There have to be couple of service dialogs, about 16 is recommended.

    Steps:
        * Go to service dialogs page
        * Set the paginator to 50 results per page, then to 5 results per page.
        * Assert there are 5 rows displayed in the table
        * Then cycle through the pages. Note all the dialogs you see, in the end the list of all
            dialogs must contain all idalogs you created before.
        * During the cycling, assert the numbers displayed in the paginator make sense
        * During the cycling, assert the paginator does not get stuck.

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    service_dialog = appliance.collections.service_dialogs
    view = navigate_to(service_dialog, 'All')
    view.paginator.set_items_per_page(50)
    view.paginator.set_items_per_page(5)
    # Now we must have only 5
    soft_assert(len(list(view.table.rows())) == 5, "Changing number of rows failed!")
    # try to browse
    current_rec_offset = None
    dialogs_found = set()
    for _ in view.paginator.pages():
        if view.paginator.min_item == current_rec_offset:
            soft_assert(False, "Paginator is locked, it does not advance to next page")
            break
        for text in get_relevant_rows(view.table):
            dialogs_found.add(text)

        current_total = view.paginator.items_amount
        current_rec_offset = view.paginator.min_item
        current_rec_end = view.paginator.max_item

        assert int(current_rec_offset) <= int(current_rec_end) <= int(current_total), \
            "Incorrect paginator value, expected {} <= {} <= {}".format(
                current_rec_offset, current_rec_end, current_total)

    assert {dlg.label for dlg in some_dialogs} <= dialogs_found, \
        "Could not find all dialogs by clicking the paginator!"


# test_ordering - after it starts working somehow, otherwise cannot test it properly
# BLOCKER: The rails activerecord sorts differently than the python sort
