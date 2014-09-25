# -*- coding: utf-8 -*-
from collections import namedtuple

import cfme.web_ui.menu as menu
assert menu

from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Region, SplitTable, paginator

list_page = Region(locators=dict(
    filers_table=SplitTable(
        header_data=("//div[@id='list_grid']/div[@class='xhdr']/table/tbody", 1),
        body_data=("//div[@id='list_grid']/div[@class='objbox']/table/tbody", 1),
    ),
))

# TODO: Extend it to be a proper class, because you can do stuff with that
Filer = namedtuple("Filer", [
    "name", "element_name", "vms", "hosts", "datastores", "health_status",
    "op_status", "description", "region", "last_upd_status"
])


def all():
    """Returns all of the file shares available"""
    sel.force_navigate("filers")
    for page in paginator.pages():
        for row in list_page.filers_table.rows():
            yield Filer(
                name=sel.text_sane(row.name),
                element_name=sel.text_sane(row.element_name),
                vms=int(sel.text_sane(row.vms)),
                hosts=int(sel.text_sane(row.hosts)),
                datastores=int(sel.text_sane(row.datastores)),
                health_status=sel.text_sane(row.health_status),
                op_status=sel.text_sane(row.operational_status),
                description=sel.text_sane(row.description),
                region=sel.text_sane(row.region),
                last_upd_status=sel.text_sane(row.last_update_status)
            )
