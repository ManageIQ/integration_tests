# -*- coding: utf-8 -*-
import pytest

from cfme.automate.service_dialogs import ServiceDialog, dialogs_table
from cfme.web_ui import paginator
from utils.randomness import generate_random_string


@pytest.fixture(scope="module")
def some_dialogs(request):
    to_delete = []
    request.addfinalizer(lambda: map(lambda obj: obj.delete(), to_delete))
    for i in range(6):
        random_str = generate_random_string(16)
        dialog = ServiceDialog(
            label='test_paginator_{}'.format(random_str),
            tab_label='tab_{}'.format(random_str),
            box_label='box_{}'.format(random_str),
            ele_label='ele_label_{}'.format(random_str),
            ele_name='ele_name_{}'.format(random_str),
            choose_type='Check Box')
        dialog.create()
        to_delete.append(dialog)
    return to_delete


def get_relevant_rows(table):
    result = []
    for row in table.rows():
        text = pytest.sel.text(row.label).encode("utf-8").strip()
        if text.startswith("test_paginator_"):
            result.append(text)
    return result


@pytest.mark.bugzilla(1125230)
def test_paginator(some_dialogs, soft_assert):
    """ Ths test currently fails as this thing is completely broken

    """
    pytest.sel.force_navigate("service_dialogs")
    paginator.results_per_page(50)
    paginator.results_per_page(5)
    # Now we must have only 5
    soft_assert(len(list(dialogs_table.rows())) == 5, "Changing number of rows failed!")
    # try to browse
    current_rec_offset = None
    dialogs_found = set([])
    for page in paginator.pages():
        if paginator.rec_offset() == current_rec_offset:
            soft_assert(False, "Paginator is locked, it does not advance to next page")
            break
        if current_rec_offset is None:
            current_rec_offset = paginator.rec_offset()
        for text in get_relevant_rows(dialogs_table):
            dialogs_found.add(text)
        current_rec_offset = paginator.rec_offset()
    soft_assert(set([dlg.label for dlg in some_dialogs]).issubset(dialogs_found))


# test_ordering - after it starts working somehow, otherwise cannot test it properly
# BLOCKER: The rails activerecord sorts differently than the python sort
