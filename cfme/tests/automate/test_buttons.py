import pytest
from cfme.web_ui import flash
from cfme.automate.buttons import Button
from cfme.automate.buttons import ButtonGroup
from cfme.automate.service_dialogs import ServiceDialog
from utils.randomness import generate_random_string
from utils.update import update


pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.yield_fixture(scope="function")
def dialog():
    dialog_name = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog_name, description="my dialog",
                                   submit=True, cancel=True)
    service_dialog.create()
    flash.assert_success_message('Dialog "%s" was added' % dialog_name)
    yield service_dialog
    service_dialog.delete()


def test_button_group_crud(request):
    buttongroup = ButtonGroup(
        text=generate_random_string(), hover="btn_hvr", type=ButtonGroup.SERVICE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    with update(buttongroup):
        buttongroup.hover = "edit_desc_{}".format(generate_random_string())
    buttongroup.delete()


@pytest.mark.bugzilla(1143019)
def test_button_crud(dialog, request):
    buttongroup = ButtonGroup(
        text=generate_random_string(),
        hover="btn_desc_{}".format(generate_random_string()),
        type=ButtonGroup.SERVICE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    button = Button(group=buttongroup,
                    text=generate_random_string(),
                    hover="btn_hvr_{}".format(generate_random_string()),
                    dialog=dialog, system="Request", request="InspectMe")
    request.addfinalizer(button.delete_if_exists)
    button.create()
    with update(button):
        button.hover = "edit_desc_{}".format(generate_random_string())
    button.delete()
