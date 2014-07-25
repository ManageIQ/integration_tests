# -*- coding: utf-8 -*-
from collections import namedtuple

import cfme.web_ui.menu as menu
assert menu  # To stop complaining

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import SplitTable, Region, paginator


list_page = Region(locators=dict(
    file_shares_table=SplitTable(
        header_data=("//div[@id='list_grid']/div[@class='xhdr']/table/tbody", 1),
        body_data=("//div[@id='list_grid']/div[@class='objbox']/table/tbody", 1),
    ),
))

# TODO: Extend it to be a proper class, because you can do stuff with that
FileShare = namedtuple("FileShare", [
    "name", "element_name", "vms", "hosts", "datastores", "op_status", "region", "last_upd_status"
])


def all():
    """Returns all of the file shares available"""
    sel.force_navigate("file_shares")
    for page in paginator.pages():
        for row in list_page.file_shares_table.rows():
            yield FileShare(
                name=sel.text_sane(row.name),
                element_name=sel.text_sane(row.element_name),
                vms=int(sel.text_sane(row.vms)),
                hosts=int(sel.text_sane(row.hosts)),
                datastores=int(sel.text_sane(row.datastores)),
                op_status=sel.text_sane(row.operational_status),
                region=sel.text_sane(row.region),
                last_upd_status=sel.text_sane(row.last_update_status)
            )
