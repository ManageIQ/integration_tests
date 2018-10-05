# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.update import update

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    test_requirements.automate,
    pytest.mark.tier(3)
]


def create_dialog(appliance, element_data, label=None):
    service_dialog = appliance.collections.service_dialogs
    if label is None:
        label = 'label_' + fauxfactory.gen_alphanumeric()
    sd = service_dialog.create(label=label, description="my dialog")
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    element = box.elements.create(element_data=[element_data])
    return sd, element


@pytest.mark.sauce
def test_crud_service_dialog(appliance):
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box"
        },
        'options': {
            'default_text_box': "Default text"
        }
    }

    dialog, element = create_dialog(appliance, element_data)
    view_cls = navigator.get_class(element.parent, 'Add').VIEW
    view = element.appliance.browser.create_view(view_cls)
    flash_message = '{} was saved'.format(dialog.label)
    view.flash.assert_message(flash_message)
    with update(dialog):
        dialog.description = "my edited description"
    dialog.delete()


def test_service_dialog_duplicate_name(appliance, request):
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box"
        },
        'options': {
            'default_text_box': "Default text"
        }
    }
    label = 'duplicate_' + fauxfactory.gen_alphanumeric()
    dialog, element = create_dialog(appliance, element_data, label=label)
    request.addfinalizer(dialog.delete_if_exists)
    region_number = appliance.server.zone.region.number
    error_message = ('There was an error editing this dialog: '
                     'Failed to create a new dialog - Validation failed: '
                     'Name is not unique within region {}'.format(region_number))
    with pytest.raises(AssertionError):
        create_dialog(appliance, element_data, label=label)
        view_cls = navigator.get_class(element.parent, 'Add').VIEW
        view = element.appliance.browser.create_view(view_cls)
        view.flash.assert_message(error_message)


def test_checkbox_dialog_element(appliance, request):
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Check Box"
        },
        'options': {
            'default_value': True,
            'field_required': True
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_datecontrol_dialog_element(appliance, request):
    if appliance.version >= "5.9":
        choose_type = "Datepicker"
    else:
        choose_type = "Date Control"
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': choose_type
        },
        'options': {
            'field_past_dates': True
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_tagcontrol_dialog_element(appliance, request):
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Tag Control"
        },
        'options': {
            'field_category': "Service Level",
            'field_required': "Yes"
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_textareabox_dialog_element(appliance, request):
    if appliance.version >= "5.9":
        choose_type = "Text Area"
    else:
        choose_type = "Text Area Box",
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': choose_type,
        },
        'options': {
            'field_required': "Yes"
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_reorder_elements(appliance, request):
    element_1_data = {
        'element_information': {
            'ele_label': "ele_label_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box",
        }
    }
    element_2_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Check Box",

        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label='label_' + fauxfactory.gen_alphanumeric(),
                               description="my dialog")
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
        box_desc="my box desc")
    element = box.elements.create(element_data=[element_1_data, element_2_data])
    request.addfinalizer(sd.delete_if_exists)
    element.reorder_elements(False, element_2_data, element_1_data)


def test_reorder_unsaved_elements(appliance, request):
    # Automate BZ - https://bugzilla.redhat.com/show_bug.cgi?id=1238721
    box_label = 'box_' + fauxfactory.gen_alphanumeric()
    element_1_data = {
        'element_information': {
            'ele_label': "ele_label_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box",
        }
    }
    element_2_data = {
        'element_information': {
            'ele_label': box_label,
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Check Box"
        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label='label_' + fauxfactory.gen_alphanumeric(),
                               description="my dialog")
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
        tab_desc="my tab desc")
    box = tab.boxes.create(box_label=box_label,
        box_desc="my box desc")
    element = box.elements.create(element_data=[element_1_data])
    request.addfinalizer(sd.delete_if_exists)
    element.reorder_elements(True, element_2_data, element_1_data)


def test_dropdownlist_dialog_element(appliance, request):
    if appliance.version >= "5.9":
        choose_type = "Dropdown"
    else:
        choose_type = "Drop Down List"
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': choose_type
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_radiobutton_dialog_element(appliance, request):
    element_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Radio Button"
        }
    }
    dialog, element = create_dialog(appliance, element_data)
    request.addfinalizer(dialog.delete_if_exists)


def test_remove_dialog_element(appliance, request):
    """Tests remove dialog element

    Testing BZ 1522870.
    """
    element_1_data = {
        'element_information': {
            'ele_label': "ele_label_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Text Box",
        }
    }
    element_2_data = {
        'element_information': {
            'ele_label': "ele_" + fauxfactory.gen_alphanumeric(),
            'ele_name': fauxfactory.gen_alphanumeric(),
            'ele_desc': fauxfactory.gen_alphanumeric(),
            'choose_type': "Radio Button",

        }
    }
    service_dialog = appliance.collections.service_dialogs
    sd = service_dialog.create(label='label_' + fauxfactory.gen_alphanumeric(),
                               description="my dialog")
    tab = sd.tabs.create(tab_label='tab_' + fauxfactory.gen_alphanumeric(),
                         tab_desc="my tab desc")
    box = tab.boxes.create(box_label='box_' + fauxfactory.gen_alphanumeric(),
                           box_desc="my box desc")
    element = box.elements.create(element_data=[element_1_data, element_2_data])
    request.addfinalizer(sd.delete_if_exists)
    element.remove_elements(elements=[element_1_data])
