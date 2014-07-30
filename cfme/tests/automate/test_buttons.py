import pytest
from cfme.web_ui import flash
from cfme.automate.buttons import Buttons
from cfme.automate.buttons import ButtonGroup
from cfme.automate.service_dialogs import ServiceDialog
from utils.randomness import generate_random_string
from utils.update import update


pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.fixture(scope="function")
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                                   submit=True, cancel=True)
    service_dialog.create()
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    return dialog


def test_add_button_group():
    buttongroup = ButtonGroup(group_text=generate_random_string(),
                              group_hover_text="btn_hvr")
    buttongroup.create()


def test_edit_button_group():
    buttongroup = ButtonGroup(group_text=generate_random_string(),
                              group_hover_text="btn_hvr_" +
                              generate_random_string())
    buttongroup.create()
    with update(buttongroup):
        buttongroup.group_hover_text = "edit_desc_" + generate_random_string()


def test_delete_button_group():
    buttongroup = ButtonGroup(group_text=generate_random_string(),
                              group_hover_text="btn_hvr_" +
                              generate_random_string())
    buttongroup.create()
    buttongroup.delete()


def test_add_button(dialog):
    buttongroup = ButtonGroup(group_text=generate_random_string(),
                              group_hover_text="btn_desc_" +
                              generate_random_string())
    buttongroup.create()
    button = Buttons(buttongroup=buttongroup.group_text,
                     btn_text=generate_random_string(),
                     btn_hvr_text="btn_hvr_" + generate_random_string(),
                     dialog=dialog, system="Request", request="InspectMe")
    button.create()


def test_edit_button(dialog):
    buttongroup = ButtonGroup(group_text=generate_random_string(),
                              group_hover_text="btn_desc_" +
                              generate_random_string())
    buttongroup.create()
    button = Buttons(buttongroup=buttongroup.group_text,
                     btn_text=generate_random_string(),
                     btn_hvr_text="btn_hvr_" + generate_random_string(),
                     dialog=dialog, system="Request", request="InspectMe")
    button.create()
    with update(button):
        button.btn_hvr_text = "edit_desc_" + generate_random_string()


def test_delete_button(dialog):
    buttongroup = ButtonGroup(group_text=generate_random_string(),
                              group_hover_text="btn_desc_" +
                              generate_random_string())
    buttongroup.create()
    button = Buttons(buttongroup=buttongroup.group_text,
                     btn_text=generate_random_string(),
                     btn_hvr_text="btn_hvr_" + generate_random_string(),
                     dialog=dialog, system="Request", request="InspectMe")
    button.create()
    button.delete()
