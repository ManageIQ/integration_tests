import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.utils.appliance.implementations.ui import navigate_to


COMMON_FEATURES = {
    "auth_key_pair_cloud": ["Compute / Clouds / Key Pairs"],
    "automation_manager": ["Automation / Ansible Tower / Explorer"],
    "availability_zone": ["Compute / Clouds / Availability Zones"],
    "catalog": ["Services / Catalogs"],
    "cloud_network": ["Networks / Networks"],
    "cloud_object_store_container": ["Storage / Object Storage / Object Store Containers"],
    "cloud_object_store_object": ["Storage / Object Storage / Object Store Objects"],
    "cloud_subnet": ["Networks / Subnets"],
    "cloud_tenant": ["Compute / Clouds / Tenants"],
    "cloud_topology": ["Compute / Clouds / Topology"],
    "cloud_volume": ["Storage / Block Storage / Volumes"],
    "cloud_volume_backup": ["Storage / Block Storage / Volume Backups"],
    "cloud_volume_snapshot": ["Storage / Block Storage / Volume Snapshots"],
    "configuration_job": ["Automation / Ansible Tower / Jobs"],
    "container": ["Compute / Containers / Containers"],
    "container_build": ["Compute / Containers / Container Builds"],
    "container_dashboard": ["Compute / Containers / Overview"],
    "container_group": ["Compute / Containers / Pods"],
    "container_image": ["Compute / Containers / Container Images"],
    "container_image_registry": ["Compute / Containers / Image Registries"],
    "container_node": ["Compute / Containers / Container Nodes"],
    "container_project": ["Compute / Containers / Projects"],
    "container_replicator": ["Compute / Containers / Replicators"],
    "container_route": ["Compute / Containers / Routes"],
    "container_service": ["Compute / Containers / Container Services"],
    "container_template": ["Compute / Containers / Container Templates"],
    "container_topology": ["Compute / Containers / Topology"],
    "control_explorer": ["Control / Explorer"],
    "embedded_automation_manager": [
        "Automation / Ansible / Playbooks",
        "Automation / Ansible / Repositories",
        "Automation / Ansible / Credentials",
    ],
    "ems_block_storage": ["Storage / Block Storage / Managers"],
    "ems_cloud": ["Compute / Clouds / Providers"],
    "ems_cluster": ["Compute / Infrastructure / Clusters"],
    "ems_container": ["Compute / Containers / Providers"],
    "ems_infra": ["Compute / Infrastructure / Providers"],
    "ems_network": ["Networks / Providers"],
    "ems_object_storage": ["Storage / Object Storage / Managers"],
    "flavor": ["Compute / Clouds / Flavors"],
    "floating_ip": ["Networks / Floating IPs"],
    "generic_object_definition": ["Automation / Automate / Generic Objects"],
    "host": ["Compute / Infrastructure / Hosts / Nodes"],
    "host_aggregate": ["Compute / Clouds / Host Aggregates"],
    "infra_networking": ["Compute / Infrastructure / Networking"],
    "infra_topology": ["Compute / Infrastructure / Topology"],
    "miq_ae_class_explorer": ["Automation / Automate / Explorer"],
    "miq_ae_class_import_export": ["Automation / Automate / Import / Export"],
    "miq_ae_class_log": ["Automation / Automate / Log"],
    "miq_ae_class_simulation": ["Automation / Automate / Simulation"],
    "miq_ae_customization_explorer": ["Automation / Automate / Customization"],
    "miq_request": ["Services / Requests", "Automation / Automate / Requests"],
    "monitor_alerts_list": ["Monitor / Alerts / All Alerts"],
    "monitor_alerts_overview": ["Monitor / Alerts / Overview"],
    "network_port": ["Networks / Network Ports"],
    "network_router": ["Networks / Network Routers"],
    "network_topology": ["Networks / Topology"],
    "orchestration_stack": ["Compute / Clouds / Stacks"],
    "persistent_volume": ["Compute / Containers / Volumes"],
    "policy_import_export": ["Control / Import / Export"],
    "policy_log": ["Control / Log"],
    "policy_simulation": ["Control / Simulation"],
    "provider_foreman_explorer": ["Configuration / Management"],
    "pxe": ["Compute / Infrastructure / PXE"],
    "resource_pool": ["Compute / Infrastructure / Resource Pools"],
    "security_group": ["Networks / Security Groups"],
    "service": ["Services / My Services"],
    "storage": ["Compute / Infrastructure / Datastores"],
    "tasks": ["Settings / Tasks"],
    "vm_cloud_explorer": [
        "Compute / Clouds / Instances / Instances By Providers",
        "Compute / Clouds / Instances / Images By Providers",
        "Compute / Clouds / Instances / Instances",
        "Compute / Clouds / Instances / Images",
    ],
    "vm_explorer": [
        "Services / Workloads / VMs & Instances",
        "Services / Workloads / Templates & Images",
    ],
    "vm_infra_explorer": [
        "Compute / Infrastructure / Virtual Machines / VMs & Templates",
        "Compute / Infrastructure / Virtual Machines / VMs",
        "Compute / Infrastructure / Virtual Machines / Templates",
    ],
}

FEATURES_NOT_IN_511 = {
    "bottlenecks": ["Optimize / Bottlenecks"],
    "chargeback": ["Cloud Intel / Chargeback"],
    "dashboard": ["Cloud Intel / Dashboard"],
    "load_balancer": ["Networks / Load Balancers"],
    "miq_report": ["Cloud Intel / Reports"],
    "planning": ["Optimize / Planning"],
    "rss": ["Cloud Intel / RSS"],
    "timeline": ["Cloud Intel / Timelines"],
    "utilization": ["Optimize / Utilization"],
}

FEATURES_NOT_IN_510 = {
    "chargeback": ["Overview / Chargeback"],
    "cloud_volume_type": ["Storage / Block Storage / Volume Types"],
    "dashboard": ["Overview / Dashboard"],
    "ems_physical_infra": ["Compute / Physical Infrastructure / Providers"],
    "mappings": ["Migration / Infrastructure Mappings"],
    "migration": ["Migration / Migration Plans"],
    "migration_settings": ["Migration / Migration Settings"],
    "miq_report": ["Overview / Reports"],
    "physical_chassis": ["Compute / Physical Infrastructure / Chassis"],
    "physical_infra_overview": ["Compute / Physical Infrastructure / Overview"],
    "physical_infra_topology": ["Compute / Physical Infrastructure / Topology"],
    "physical_rack": ["Compute / Physical Infrastructure / Racks"],
    "physical_server": ["Compute / Physical Infrastructure / Servers"],
    "physical_storage": ["Compute / Physical Infrastructure / Storages"],
    "physical_switch": ["Compute / Physical Infrastructure / Switches"],
    "utilization": ["Overview / Utilization"],
}

FEATURES_IN_511 = {**COMMON_FEATURES, **FEATURES_NOT_IN_510}
FEATURES_IN_510 = {**COMMON_FEATURES, **FEATURES_NOT_IN_511}

ALL_FEATURES_LST = {*FEATURES_IN_510, *FEATURES_IN_511}

# These keys are present in both the versions but with different values
DIFFERENT_VALUE_LST = ["chargeback", "dashboard", "miq_report", "utilization"]


@pytest.fixture
def setup_user(appliance, feature):
    uid = fauxfactory.gen_alpha(length=4)
    role = appliance.rest_api.collections.roles.action.create(
        {
            "name": f"test_role_{uid}",
            "settings": {"restrictions": {"vms": "user"}},
            "features": [{"identifier": feature}, {"identifier": "my_settings"}],
        }
    )[0]
    group = appliance.rest_api.collections.groups.action.create(
        {
            "description": f"test_group_{uid}",
            "role": {"id": role.id},
            "tenant": {"href": appliance.rest_api.collections.tenants.all[0].href},
        }
    )[0]
    user = appliance.rest_api.collections.users.action.create(
        {
            "userid": f"test_user_{uid}",
            "password": "smartvm",
            "name": f"{group.description} User",
            "group": {"id": group.id},
        }
    )[0]

    yield appliance.collections.users.instantiate(
        name=user.name, credential=Credential(user.userid, "smartvm")
    )

    user.action.delete()
    group.action.delete()
    role.action.delete()


@pytest.mark.meta(automates=[1450012])
@test_requirements.settings
@pytest.mark.uncollectif(
    lambda feature, appliance: (
        appliance.version > "5.11"
        and feature in FEATURES_NOT_IN_511
        and feature not in DIFFERENT_VALUE_LST
    )
    or (
        appliance.version < "5.11"
        and feature in FEATURES_NOT_IN_510
        and feature not in DIFFERENT_VALUE_LST
    ),
    reason="Feature not supported by the appliance",
)
@pytest.mark.parametrize("feature", ALL_FEATURES_LST)
def test_validate_landing_pages_for_rbac(appliance, feature, setup_user):
    """
    Bugzilla:
        1450012

    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/5h
        setup:
            1. Create a new role by selecting a few product features.
            2. Create a group with the new role.
            3. Create a new user with the new group.
            4. Logout.
            5. Login back with the new user.
            6. Navigate to My Settings > Visual.
        testSteps:
            1.Check the start page entries in `Show at login` dropdown list
        expectedResults:
            1. Landing pages which user has access to must be present in the dropdown list.
    """
    expected = FEATURES_IN_511[feature] if appliance.version > "5.11" else FEATURES_IN_510[feature]
    with setup_user:
        view = navigate_to(appliance.user.my_settings, "Visual")
        all_options = [
            option.text for option in view.tabs.visual.start_page.show_at_login.all_options
        ]
        assert set(all_options) == set(expected)
