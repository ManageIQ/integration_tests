# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.web_ui import flash
from cfme.automate.buttons import Button, ButtonGroup
from cfme.automate.service_dialogs import ServiceDialog
from cfme.infrastructure import host
from utils.appliance.endpoints.ui import navigate_to
from utils.update import update

pytestmark = [pytest.mark.ignore_stream("upstream"),
              pytest.mark.usefixtures('uses_infra_providers')]


@pytest.yield_fixture(scope="function")
def dialog():
    dialog_name = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name=fauxfactory.gen_alphanumeric(),
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box="default value"
    )

    service_dialog = ServiceDialog(label=dialog_name, description="my dialog", submit=True,
                                   cancel=True, tab_label="tab_" + fauxfactory.gen_alphanumeric(),
                                   tab_desc="my tab desc",
                                   box_label="box_" + fauxfactory.gen_alphanumeric(),
                                   box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "%s" was added' % dialog_name)
    yield service_dialog


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_button_group_crud(request):
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(), hover="btn_hvr", type=ButtonGroup.SERVICE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    with update(buttongroup):
        buttongroup.hover = "edit_desc_{}".format(fauxfactory.gen_alphanumeric())
    buttongroup.delete()


@pytest.mark.meta(blockers=[1143019, 1205235])
@pytest.mark.tier(2)
def test_button_crud(dialog, request):
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=ButtonGroup.SERVICE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    button = Button(group=buttongroup,
                    text=fauxfactory.gen_alphanumeric(),
                    hover="btn_hvr_{}".format(fauxfactory.gen_alphanumeric()),
                    dialog=dialog, system="Request", request="InspectMe")
    request.addfinalizer(button.delete_if_exists)
    button.create()
    with update(button):
        button.hover = "edit_desc_{}".format(fauxfactory.gen_alphanumeric())
    button.delete()


@pytest.mark.meta(blockers=[1193758, 1205235])
@pytest.mark.tier(3)
def test_button_on_host(dialog, request):
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=ButtonGroup.HOST)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    button = Button(group=buttongroup,
                    text=fauxfactory.gen_alphanumeric(),
                    hover="btn_hvr_{}".format(fauxfactory.gen_alphanumeric()),
                    dialog=dialog, system="Request", request="InspectMe")
    request.addfinalizer(button.delete_if_exists)
    button.create()
    myhost = host.get_from_config('esx')
    if not myhost.exists:
        myhost.create()
    myhost.execute_button(buttongroup.hover, button.text)


@pytest.mark.meta(blockers=[1229348], automates=[1229348])
@pytest.mark.tier(2)
def test_button_avp_displayed(request):
    """This test checks whether the Attribute/Values pairs are displayed in the dialog.

    Steps:
        * Open a dialog to create a button.
        * Locate the section with attribute/value pairs.
    """
    # This is optional, our nav tree does not have unassigned button
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=ButtonGroup.VM_INSTANCE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    navigate_to(buttongroup, 'Details')
    pytest.sel.force_navigate("new_button", context={'buttongroup': buttongroup})
    section_loc = "//*[(self::h3 or self::p) and normalize-space(text())='Attribute/Value Pairs']"
    assert pytest.sel.is_displayed(section_loc),\
        "The Attribute/Value Pairs part of the form is not displayed"
