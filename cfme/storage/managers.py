# -*- coding: utf-8 -*-
from functools import partial

from cfme.web_ui.menu import nav

from cfme.exceptions import StorageManagerNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Form, InfoBlock, MultiFill, Region, Select, SplitTable, fill, flash
from cfme.web_ui import form_buttons, paginator, toolbar
from utils.update import Updateable
from utils.wait import wait_for

list_page = Region(locators=dict(
    managers_table=SplitTable(
        header_data=("//div[@id='list_grid']/div[@class='xhdr']/table/tbody", 1),
        body_data=("//div[@id='list_grid']/div[@class='objbox']/table/tbody", 1),
    ),
))

cfg_btn = partial(toolbar.select, "Configuration")


def _get_sm_name(o):
    if isinstance(o, StorageManager):
        return o.name
    else:
        return str(o)


def _find_and_click_sm(context):
    """Incorporates searching through the page listing and clicking in the table. Also ensures
    waiting for the transition as there is no ajax hook."""
    sm_name = _get_sm_name(context["storage_manager"])
    for page in paginator.pages():
        if sel.is_displayed("#no_records_div"):
            break
        if list_page.managers_table.click_cell("name", sm_name):
            sel.wait_for_element("#textual_div")  # No ajax wait there :(
            return
    raise StorageManagerNotFound("Storage manager with name '{}' not found!".format(sm_name))

nav.add_branch(
    "storage_managers",
    {
        "storage_manager_new": lambda _: cfg_btn("Add a New Storage Manager"),
        "storage_manager": [
            _find_and_click_sm,
            {
                "storage_manager_edit": lambda _: cfg_btn("Edit this Storage Manager"),
            }
        ]
    }
)


class StorageManager(Updateable):
    """Represents the Storage / Storage Managers object. Allows interaction

    Args:
        name: Name of the Storage Namager as it appears in the UI.
        type: Type of the Storage Manager (eg. StorageManager.NETAPP_RS, ...)
        hostname: Host name of the machine.
        ip: IP Address of the machine.
        port: Port of the machine.
        credentials: :py:class:`dict` or :py:class:`StorageManager.Credential`
    """
    class Credential(Updateable):
        def __init__(self, username=None, password=None):
            self.username = username
            self.password = password

    form = Form(fields=[
        ("name", "input#name"),
        ("type", Select("select#sm_type")),
        ("hostname", "input#hostname"),
        ("ip", "input#ipaddress"),
        ("port", "input#port"),
        ("credentials", Form(fields=[
            ("username", "input#userid"),
            ("password", MultiFill(
                "input#password", "input#verify"
            ))
        ])),
    ])

    validate = form_buttons.FormButton("Validate the credentials by logging into the Server")
    add = form_buttons.FormButton("Add this Storage Manager")

    ##
    # Types constants. Extend if needed :)
    NETAPP_RS = "NetApp Remote Service"

    def __init__(self, name=None, type=None, hostname=None, ip=None, port=None, credentials=None):
        self.name = name
        self.type = type
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.credentials = credentials

    def create(self, validate=True, cancel=False):
        sel.force_navigate("storage_manager_new")
        fill(self.form, self)
        if validate:
            sel.click(self.validate)
        if cancel:
            sel.click(form_buttons.cancel)
        else:
            sel.click(self.add)
        flash.assert_no_errors()

    def update(self, updates, validate=True, cancel=False):
        sel.force_navigate("storage_manager_edit", context={"storage_manager": self})
        fill(self.form, updates)
        if validate:
            sel.click(self.validate)
        if cancel:
            sel.click(form_buttons.cancel)
        else:
            sel.click(form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        self.navigate()
        cfg_btn("Remove this Storage Manager from the VMDB", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    def navigate(self):
        sel.force_navigate("storage_manager", context={"storage_manager": self})

    def refresh_inventory(self):
        self.navigate()
        cfg_btn("Refresh Inventory", invokes_alert=True)
        sel.handle_alert(cancel=False)
        flash.assert_no_errors()

    def refresh_status(self):
        self.navigate()
        cfg_btn("Refresh Status", invokes_alert=True)
        sel.handle_alert(cancel=False)
        flash.assert_no_errors()

    def wait_until_updated(self, num_sec=300):
        def _wait_func():
            self.navigate()
            return InfoBlock("Properties", "Last Update Status").text.strip().lower() == "ok"
        wait_for(_wait_func, num_sec=num_sec, delay=5)

    @property
    def exists(self):
        try:
            self.navigate()
            return True
        except StorageManagerNotFound:
            return False
