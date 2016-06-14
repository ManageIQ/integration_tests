# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.service_dialogs import ServiceDialog, common
from cfme.web_ui import paginator


@pytest.fixture(scope="module")
def some_dialogs(request):
    to_delete = []
    request.addfinalizer(lambda: map(lambda obj: obj.delete(), to_delete))
    for i in range(6):
        random_str = fauxfactory.gen_alphanumeric(16)
        element_data = dict(ele_label='ele_label_{}'.format(random_str),
                            ele_name='ele_name_{}'.format(random_str),
                            choose_type='Check Box')
        dialog = ServiceDialog(
            label='test_paginator_{}'.format(random_str),
            tab_label='tab_{}'.format(random_str),
            box_label='box_{}'.format(random_str))
        dialog.create(element_data)
        to_delete.append(dialog)
    return to_delete


def get_relevant_rows(table):
    result = []
    for row in table.rows():
        text = pytest.sel.text(row.label).encode("utf-8").strip()
        if text.startswith("test_paginator_"):
            result.append(text)
    return result


@pytest.mark.meta(blocks=[1125230, 1205235])
@pytest.mark.tier(3)
def test_paginator(some_dialogs, soft_assert):
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
    pytest.sel.force_navigate("service_dialogs")
    paginator.results_per_page(50)
    paginator.results_per_page(5)
    # Now we must have only 5
    soft_assert(len(list(common.dialogs_table.rows())) == 5, "Changing number of rows failed!")
    # try to browse
    current_rec_offset = None
    dialogs_found = set()
    for page in paginator.pages():
        if paginator.rec_offset() == current_rec_offset:
            soft_assert(False, "Paginator is locked, it does not advance to next page")
            break
        if current_rec_offset is None:
            current_rec_offset = paginator.rec_offset()
        for text in get_relevant_rows(common.dialogs_table):
            dialogs_found.add(text)

        current_total = paginator.rec_total()
        current_rec_offset = paginator.rec_offset()
        current_rec_end = paginator.rec_end()

        assert current_rec_offset <= current_rec_end <= current_total, \
            "Incorrect paginator value, expected {0} <= {1} <= {2}".format(
                current_rec_offset, current_rec_end, current_total)

    assert set([dlg.label for dlg in some_dialogs]) <= dialogs_found, \
        "Could not find all dialogs by clicking the paginator!"


# test_ordering - after it starts working somehow, otherwise cannot test it properly
# BLOCKER: The rails activerecord sorts differently than the python sort
