# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.service_dialogs import DialogCollection
from cfme.web_ui import Table
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [test_requirements.service, pytest.mark.tier(3), pytest.mark.ignore_stream("upstream")]

dialogs_table = Table(".//div[@id='list_grid']/table")


@pytest.fixture(scope="module")
def some_dialogs(appliance, request):
    to_delete = []
    request.addfinalizer(lambda: map(lambda obj: obj.delete(), to_delete))
    for i in range(6):
        random_str = fauxfactory.gen_alphanumeric(16)
        element_data = dict(ele_label='ele_label_{}'.format(random_str),
                            ele_name='ele_name_{}'.format(random_str),
                            choose_type='Check Box')
        service_dialogs = DialogCollection(appliance)
        sd = service_dialogs.create(label='test_paginator_{}'.format(random_str),
                description="my dialog", submit=True, cancel=True,)
        tab = sd.tabs.create(tab_label='tab_{}'.format(random_str),
                tab_desc="my tab desc")
        box = tab.boxes.create(box_label='box_{}'.format(random_str),
                box_desc="my box desc")
        box.elements.create(element_data=[element_data])
        to_delete.append(sd)
    return to_delete


def get_relevant_rows(table):
    result = []
    for row in table.rows():
        text = pytest.sel.text(row.label).encode("utf-8").strip()
        if text.startswith("test_paginator_"):
            result.append(text)
    return result


@test_requirements.general_ui
@pytest.mark.meta(blocks=[1125230, 1205235])
@pytest.mark.tier(3)
def test_paginator(some_dialogs, soft_assert, appliance):
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
    """
    navigate_to(DialogCollection(appliance), 'All')
    from cfme.web_ui import paginator
    paginator.results_per_page(50)
    paginator.results_per_page(5)
    # Now we must have only 5
    soft_assert(len(list(dialogs_table.rows())) == 5, "Changing number of rows failed!")
    # try to browse
    current_rec_offset = None
    dialogs_found = set()
    for page in paginator.pages():
        if paginator.rec_offset() == current_rec_offset:
            soft_assert(False, "Paginator is locked, it does not advance to next page")
            break
        if current_rec_offset is None:
            current_rec_offset = paginator.rec_offset()
        for text in get_relevant_rows(dialogs_table):
            dialogs_found.add(text)

        current_total = paginator.rec_total()
        current_rec_offset = paginator.rec_offset()
        current_rec_end = paginator.rec_end()

        assert current_rec_offset <= current_rec_end <= current_total, \
            "Incorrect paginator value, expected {0} <= {1} <= {2}".format(
                current_rec_offset, current_rec_end, current_total)

    assert {dlg.label for dlg in some_dialogs} <= dialogs_found, \
        "Could not find all dialogs by clicking the paginator!"


# test_ordering - after it starts working somehow, otherwise cannot test it properly
# BLOCKER: The rails activerecord sorts differently than the python sort
