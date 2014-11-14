# -*- coding: utf-8 -*-
import pytest

from utils import error, rest_api, testgen
from utils.randomness import generate_random_string
from utils.wait import wait_for

pytest_generate_tests = testgen.generate(
    testgen.provider_by_type,
    ['virtualcenter', 'rhevm'],
    "small_template",
    scope="module"
)

pytestmark = [pytest.mark.ignore_stream("5.2")]


@pytest.fixture(scope="module")
def provision_data(provider_crud, provider_key, provider_data, small_template):
    return {
        "version": "1.1",
        "template_fields": {
            "guid": rest_api.get_template_guid(small_template)
        },
        "vm_fields": {
            "number_of_cpus": 1,
            "vm_name": "test_rest_prov_{}".format(generate_random_string()),
            "vm_memory": "1024",
            "vlan": provider_data["provisioning"]["vlan"]
        },
        "requester": {
            "user_name": "admin",
            "owner_first_name": "John",
            "owner_last_name": "Doe",
            "owner_email": "jdoe@sample.com",
            "auto_approve": True
        },
        "tags": {
            "network_location": "Internal",
            "cc": "001"
        },
        "additional_values": {
            "request_id": "1001"
        },
        "ems_custom_attributes": {},
        "miq_custom_attributes": {}
    }


@pytest.mark.fixtureconf(server_roles="+automate")
@pytest.mark.usefixtures("setup_provider", "server_roles")
def test_provision(request, provision_data, provider_mgmt):
    vm_name = provision_data["vm_fields"]["vm_name"]
    request.addfinalizer(
        lambda: provider_mgmt.delete_vm(vm_name) if provider_mgmt.does_vm_exist(vm_name) else None)
    request = rest_api.api().provision_requests().post(provision_data)["results"][0]["id"]

    def _finished():
        q = rest_api.api().provision_requests(request).get()
        if q["status"].lower() in {"error"}:
            pytest.fail("Error when provisioning: `{}`".format(q["message"]))
        return q["request_state"].lower() in {"finished", "provisioned"}

    wait_for(_finished, num_sec=300, delay=5, message="REST provisioning finishes")


def test_add_delete_service_catalog():
    scl = rest_api.create_service_catalog(generate_random_string(), generate_random_string(), [])
    rest_api.delete_service_catalog(scl["id"])
    with error.expected("Error 404"):
        rest_api.delete_service_catalog(scl["id"])


def test_add_delete_multiple_service_catalogs():
    def _gen_ctl():
        return {
            "name": generate_random_string(),
            "description": generate_random_string(),
            "service_templates": []
        }

    scls = rest_api.create_service_catalogs(
        _gen_ctl(),
        _gen_ctl(),
        _gen_ctl(),
        _gen_ctl(),
    )
    rest_api.delete_service_catalogs(*map(lambda scl: scl["id"], scls))
    with error.expected("Error 404"):
        rest_api.delete_service_catalogs(*map(lambda scl: scl["id"], scls))
