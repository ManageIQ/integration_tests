import pytest
import utils.randomness as rand
from utils.update import update
from utils import error, version
from cfme.automate.service_dialogs import ServiceDialog


pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.mark.meta(blockers=[1204899])
def test_create_service_dialog():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_update_service_dialog():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)
    with update(dialog):
        dialog.description = "my edited description"


@pytest.mark.meta(blockers=[1204899])
def test_delete_service_dialog():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)
    dialog.delete()


@pytest.mark.meta(blockers=[1204899])
def test_service_dialog_duplicate_name():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)
    error_msg = version.pick({
        version.LOWEST: "Dialog Label has already been taken",
        '5.3': "Label has already been taken"
    })
    with error.expected(error_msg):
        dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_checkbox_dialog_element():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Check Box",
        'default_text_box': True,
        'field_required': True
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_datecontrol_dialog_element():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Date Control",
        'field_past_dates': True
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_dropdownlist_dialog_element():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Drop Down List"
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_radiobutton_dialog_element():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Radio Button"
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_tagcontrol_dialog_element():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Tag Control",
        'field_category': "Service Level",
        'field_required': True
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_textareabox_dialog_element():
    element_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Text Area Box",
        'field_required': True
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_data)


@pytest.mark.meta(blockers=[1204899])
def test_reorder_elements():
    element_1_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Text Box",
        'default_text_box': "Default text"
    }
    element_2_data = {
        'ele_label': "ele_" + rand.generate_random_string(),
        'ele_name': rand.generate_random_string(),
        'ele_desc': rand.generate_random_string(),
        'choose_type': "Check Box",
        'default_text_box': True,
        'field_required': True
    }
    dialog = ServiceDialog(label=rand.generate_random_string(),
                           description="my dialog", submit=True, cancel=True,
                           tab_label="tab_" + rand.generate_random_string(),
                           tab_desc="my tab desc",
                           box_label="box_" + rand.generate_random_string(),
                           box_desc="my box desc")
    dialog.create(element_1_data, element_2_data)
    dialog.reorder_elements(dialog.box_label, element_1_data, element_2_data)
