import fauxfactory
import pytest

from cfme.rest.gen_data import _creating_skeleton
from cfme.utils.blockers import GH


def ansible_tower_dialog_rest(request, appliance):
    """Creates service dialog using REST API."""
    uid = fauxfactory.gen_alphanumeric()
    data = {
        "description": "my ansible dialog {}".format(uid),
        "buttons": "submit,cancel",
        "label": uid,
        "dialog_tabs": [
            {
                "description": "Basic Information",
                "display": "edit",
                "label": "Basic Information",
                "position": 0,
                "dialog_groups": [
                    {
                        "description": "Basic 1",
                        "display": "edit",
                        "label": "Options",
                        "position": 0,
                        "dialog_fields": [
                            {
                                "name": "service_name",
                                "description": "Name of the new service",
                                "data_type": "string",
                                "display": "edit",
                                "required": False,
                                "default_value": uid,
                                "options": {
                                    "protected": False
                                },
                                "label": "Service Name",
                                "position": 0,
                                "reconfigurable": True,
                                "visible": True,
                                "type": "DialogFieldTextBox",
                                "resource_action": {
                                    "resource_type": "DialogField"
                                }
                            },
                            {
                                "name": "limit",
                                "description": "A",
                                "data_type": "string",
                                "display": "edit",
                                "required": False,
                                "options": {
                                    "protected": False
                                },
                                "label": "Limit",
                                "position": 1,
                                "reconfigurable": True,
                                "visible": True,
                                "type": "DialogFieldTextBox",
                                "resource_action": {
                                    "resource_type": "DialogField"
                                }
                            }
                        ]
                    },
                    {
                        "description": "Basic 2",
                        "display": "edit",
                        "label": "Survey",
                        "position": 1,
                        "dialog_fields": [
                            {
                                "name": "param_Department",
                                "description": "",
                                "display": "edit",
                                "required": True,
                                "default_value": "QE",
                                "values": [
                                    [
                                        "HR",
                                        "HR"
                                    ],
                                    [
                                        "PM",
                                        "PM"
                                    ],
                                    [
                                        "QE",
                                        "QE"
                                    ]
                                ],
                                "options": {},
                                "label": "Survey",
                                "position": 0,
                                "reconfigurable": True,
                                "visible": True,
                                "type": "DialogFieldDropDownList",
                                "resource_action": {
                                    "resource_type": "DialogField"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

    service_dialog = _creating_skeleton(request, appliance, "service_dialogs",
        [data])
    return service_dialog[0]


@pytest.fixture(scope="function")
def ansible_tower_dialog(request, appliance):
    """Returns service dialog object."""
    rest_resource = ansible_tower_dialog_rest(request, appliance)
    service_dialogs = appliance.collections.service_dialogs
    service_dialog = service_dialogs.instantiate(
        label=rest_resource.label,
        description=rest_resource.description)
    yield service_dialog

    # if appliance.version < '5.11' or not GH(8836).blocks:
    service_dialog.delete_if_exists()
