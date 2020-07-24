from urllib.parse import urlparse

import fauxfactory
import pytest

from cfme.rest.gen_data import _creating_skeleton
from cfme.utils.blockers import GH
from cfme.utils.update import update


def ansible_tower_dialog_rest(request, appliance):
    """Creates service dialog using REST API."""
    uid = fauxfactory.gen_alphanumeric()
    data = {
        "description": f"my ansible dialog {uid}",
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
                                "data_type": "string",
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

    if appliance.version < '5.11' or not GH(8836).blocks:
        service_dialog.delete_if_exists()


@pytest.fixture
def ansible_api_version_change(provider, ansible_api_version):
    """
    Fixture to update Tower url to /api/vx in the UI so that all supported versions of API
    can be tested.

    API version defaults to v1. So, if no version is specified, v1 is used except for things
    which don't exist on v1.
    If v2 is specified, v2 is used for everything.

    Ansible Tower 3.4, 3.5 support both API v1 and v2.
    API v1 has been fully deprecated in Ansible Tower 3.6 and Tower 3.6 supports API v2 only.

    """
    original_url = provider.url
    parsed = urlparse(provider.url)

    updated_url = f'{parsed.scheme}://{parsed.netloc}/api/{ansible_api_version}'
    with update(provider, validate_credentials=True):
        provider.url = updated_url

    yield

    with update(provider, validate_credentials=True):
        provider.url = original_url
