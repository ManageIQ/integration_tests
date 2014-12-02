# -*- coding: utf-8 -*-
import pytest

from cfme.configure.configuration import Category, Tag
from cfme.control.explorer import PolicyProfile, VMCompliancePolicy, VMCondition
from cfme.infrastructure.virtual_machines import Vm

from cfme.web_ui import mixins
from utils.conf import cfme_data, credentials
from utils.randomness import generate_random_string, generate_lowercase_random_string
from utils.update import update
from utils.wait import wait_for


@pytest.fixture(scope="module")
def appliance_vm():
    """Sets up credentials for provider where the appliance is placed"""
    vm = Vm.appliance
    hosts = {}
    for provider_data in cfme_data.get("management_systems", {}).itervalues():
        for host_data in provider_data.get("hosts", []):
            hosts[host_data["name"]] = {
                "credentials": credentials[host_data["credentials"]],
                "type": host_data["type"]
            }
    for host in vm.provider.hosts:
        if not host.has_valid_credentials and host.name in hosts:
            with update(host):
                host.credentials = host.Credentials(
                    principal=hosts[host.name]["credentials"]["username"],
                    secret=hosts[host.name]["credentials"]["password"],
                    verify_secret=hosts[host.name]["credentials"]["password"],
                )
            host.refresh_host_relationships()
    return vm


def test_simple_tag_policy(request, ssh_client, appliance_vm):
    category = Category(
        name=generate_lowercase_random_string(size=8),
        description=generate_random_string(size=32),
        display_name=generate_random_string(size=32))
    category.create()
    request.addfinalizer(category.delete)

    tag1 = Tag(
        name=generate_lowercase_random_string(size=8),
        display_name=generate_random_string(size=32),
        category=category)
    tag1.create()
    request.addfinalizer(tag1.delete)
    tag2 = Tag(
        name=generate_lowercase_random_string(size=8),
        display_name=generate_random_string(size=32),
        category=category)
    tag2.create()
    request.addfinalizer(tag2.delete)
    condition = VMCondition(
        "Compliance testing condition {}".format(generate_random_string(size=8)),
        expression="fill_tag(VM and Instance.Cloud/Infrastructure Provider.My Company Tags : {},{})"
        .format(category.display_name, tag1.display_name)
    )
    condition.create()
    request.addfinalizer(condition.delete)
    policy = VMCompliancePolicy("Compliance {}".format(generate_random_string(size=8)))
    policy.create()
    request.addfinalizer(policy.delete)
    policy.assign_conditions(condition)
    profile = PolicyProfile(
        "Compliance PP {}".format(generate_random_string(size=8)),
        policies=[policy]
    )
    profile.create()
    request.addfinalizer(profile.delete)
    appliance_vm.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: appliance_vm.unassign_policy_profiles(profile.description))
    # COMPLIANT
    appliance_vm.provider_crud._load_details()
    mixins.add_tag(tag1)
    appliance_vm.check_compliance()
    # Compliant as of Less Than A Minute Ago
    detail = lambda: appliance_vm.get_detail(properties=("Compliance", "Status"))
    wait_for(
        lambda: detail() == "Compliant as of Less Than A Minute Ago",
        num_sec=240,
        delay=0.5,
        message="VM be compliant"
    )
    # NOT COMPLIANT
    appliance_vm.provider_crud._load_details()
    mixins.add_tag(tag2)
    appliance_vm.check_compliance()
    # Compliant as of Less Than A Minute Ago
    detail = lambda: appliance_vm.get_detail(properties=("Compliance", "Status"))
    wait_for(
        lambda: detail() == "Non-Compliant as of Less Than A Minute Ago",
        num_sec=240,
        delay=0.5,
        message="VM be compliant"
    )
