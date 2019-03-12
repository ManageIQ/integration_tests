# -*- coding: utf-8 -*-
import json

import fauxfactory
import pytest
from widgetastic_patternfly import BootstrapSelect

from cfme import test_requirements
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream"),
    test_requirements.ansible,
]


SERVICE_CATALOG_VALUES = [
    ("default", None, "localhost"),
    ("blank", "", "localhost"),
    ("unavailable_host", "unavailable_host", "unavailable_host")
]


@pytest.fixture(scope="module")
def ansible_credential(appliance):
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=fauxfactory.gen_alpha(),
        password=fauxfactory.gen_alpha()
    )
    yield credential

    if credential.exists:
        credential.delete()


@pytest.fixture
def ansible_amazon_credential(appliance, provider):
    creds = provider.get_credentials_from_config(provider.data["credentials"])
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(),
        "Amazon",
        access_key=creds.principal,
        secret_key=creds.secret
    )
    yield credential

    if credential.exists:
        credential.delete()


@pytest.fixture(scope="module")
def ansible_catalog_item(appliance, ansible_repository):
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_PLAYBOOK,
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        display_in_catalog=True,
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric(),
            "extra_vars": [("some_var", "some_value")]
        },
        retirement={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "extra_vars": [("some_var", "some_value")]
        }
    )
    yield cat_item

    if cat_item.exists:
        cat_item.delete()


@pytest.fixture(scope="module")
def catalog(appliance, ansible_catalog_item):
    catalog_ = appliance.collections.catalogs.create(fauxfactory.gen_alphanumeric(),
                                                     description='my catalog',
                                                     items=[ansible_catalog_item.name])
    ansible_catalog_item.catalog = catalog_
    yield catalog_

    if catalog_.exists:
        catalog_.delete()
        ansible_catalog_item.catalog = None


@pytest.fixture(scope="module")
def service_catalog(appliance, ansible_catalog_item, catalog):
    service_catalog_ = ServiceCatalogs(appliance, catalog, ansible_catalog_item.name)
    return service_catalog_


@pytest.fixture
def service_request(appliance, ansible_catalog_item):
    request_descr = "Provisioning Service [{0}] from [{0}]".format(ansible_catalog_item.name)
    service_request_ = appliance.collections.requests.instantiate(description=request_descr)
    yield service_request_

    if service_request_.exists():
        service_id = appliance.rest_api.collections.service_requests.get(description=request_descr)
        appliance.rest_api.collections.service_requests.action.delete(id=service_id.id)


@pytest.fixture
def service(appliance, ansible_catalog_item):
    service_ = MyService(appliance, ansible_catalog_item.name)
    yield service_

    if service_.exists:
        service_.delete()


@pytest.fixture
def custom_service_button(appliance, ansible_catalog_item):
    buttongroup = appliance.collections.button_groups.create(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=appliance.collections.button_groups.SERVICE)
    button = buttongroup.buttons.create(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_hvr_{}".format(fauxfactory.gen_alphanumeric()),
        dialog=ansible_catalog_item.provisioning["provisioning_dialog_name"],
        system="Request",
        request="Order_Ansible_Playbook"
    )
    yield button
    button.delete_if_exists()
    buttongroup.delete_if_exists()


@pytest.mark.tier(1)
def test_service_ansible_playbook_available(appliance):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: high
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    view = navigate_to(appliance.collections.catalog_items, "Choose Type")
    assert "Ansible Playbook" in [option.text for option in view.select_item_type.all_options]


@pytest.mark.tier(1)
def test_service_ansible_playbook_crud(appliance, ansible_repository):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_PLAYBOOK,
        fauxfactory.gen_alphanumeric(),
        fauxfactory.gen_alphanumeric(),
        provisioning={
            "repository": ansible_repository.name,
            "playbook": "dump_all_variables.yml",
            "machine_credential": "CFME Default Credential",
            "create_new": True,
            "provisioning_dialog_name": fauxfactory.gen_alphanumeric()
        }
    )
    assert cat_item.exists
    with update(cat_item):
        new_name = "edited_{}".format(fauxfactory.gen_alphanumeric())
        cat_item.name = new_name
        cat_item.provisioning = {
            "playbook": "copy_file_example.yml"
        }
    view = navigate_to(cat_item, "Details")
    assert new_name in view.entities.title.text
    assert view.entities.provisioning.info.get_text_of("Playbook") == "copy_file_example.yml"
    cat_item.delete()
    assert not cat_item.exists


def test_service_ansible_playbook_tagging(ansible_catalog_item):
    """ Tests ansible_playbook tag addition, check added tag and removal

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: high
        initialEstimate: 1/2h
        tags: ansible_embed
        testSteps:
            1. Login as a admin
            2. Add tag for ansible_playbook
            3. Check added tag
            4. Remove the given tag
    """
    added_tag = ansible_catalog_item.add_tag()
    assert any(tag.category.display_name == added_tag.category.display_name and
               tag.display_name == added_tag.display_name
               for tag in ansible_catalog_item.get_tags()), (
        'Assigned tag was not found on the details page')
    ansible_catalog_item.remove_tag(added_tag)
    assert ansible_catalog_item.get_tags() == []


@pytest.mark.tier(2)
def test_service_ansible_playbook_negative(appliance):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    collection = appliance.collections.catalog_items
    cat_item = collection.instantiate(collection.ANSIBLE_PLAYBOOK, "", "", {})
    view = navigate_to(cat_item, "Add")
    view.fill({
        "name": fauxfactory.gen_alphanumeric(),
        "description": fauxfactory.gen_alphanumeric()
    })
    assert not view.add.active
    view.browser.refresh()


@pytest.mark.tier(2)
def test_service_ansible_playbook_bundle(appliance, ansible_catalog_item):
    """Ansible playbooks are not designed to be part of a cloudforms service bundle.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    view = navigate_to(appliance.collections.catalog_bundles, "Add")
    options = view.resources.select_resource.all_options
    assert ansible_catalog_item.name not in [o.text for o in options]
    view.browser.refresh()


@pytest.mark.tier(2)
def test_service_ansible_playbook_provision_in_requests(appliance, ansible_catalog_item,
                                                        service_catalog, request):
    """Tests if ansible playbook service provisioning is shown in service requests.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    service_catalog.order()
    cat_item_name = ansible_catalog_item.name
    request_descr = "Provisioning Service [{0}] from [{0}]".format(cat_item_name)
    service_request = appliance.collections.requests.instantiate(description=request_descr)
    service_id = appliance.rest_api.collections.service_requests.get(description=request_descr)

    @request.addfinalizer
    def _finalize():
        _service = MyService(appliance, cat_item_name)
        if service_request.exists():
            service_request.wait_for_request()
            appliance.rest_api.collections.service_requests.action.delete(id=service_id.id)
        if _service.exists:
            _service.delete()

    assert service_request.exists()


@pytest.mark.tier(2)
def test_service_ansible_playbook_confirm(appliance, soft_assert):
    """Tests after selecting playbook additional widgets appear and are pre-populated where
    possible.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    collection = appliance.collections.catalog_items
    cat_item = collection.instantiate(collection.ANSIBLE_PLAYBOOK, "", "", {})
    view = navigate_to(cat_item, "Add")
    assert view.provisioning.is_displayed
    assert view.retirement.is_displayed
    soft_assert(view.provisioning.repository.is_displayed)
    soft_assert(view.provisioning.verbosity.is_displayed)
    soft_assert(view.provisioning.verbosity.selected_option == "0 (Normal)")
    soft_assert(view.provisioning.localhost.is_displayed)
    soft_assert(view.provisioning.specify_host_values.is_displayed)
    soft_assert(view.provisioning.logging_output.is_displayed)
    soft_assert(view.retirement.localhost.is_displayed)
    soft_assert(view.retirement.specify_host_values.is_displayed)
    soft_assert(view.retirement.logging_output.is_displayed)
    soft_assert(view.retirement.remove_resources.selected_option == "Yes")
    soft_assert(view.retirement.repository.is_displayed)
    soft_assert(view.retirement.verbosity.is_displayed)
    soft_assert(view.retirement.remove_resources.is_displayed)
    soft_assert(view.retirement.verbosity.selected_option == "0 (Normal)")


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda host_type, action:
                         host_type == "blank" and action == "retirement")
@pytest.mark.parametrize("host_type,order_value,result", SERVICE_CATALOG_VALUES, ids=[
    value[0] for value in SERVICE_CATALOG_VALUES])
@pytest.mark.parametrize("action", ["provisioning", "retirement"])
def test_service_ansible_playbook_order_retire(appliance, ansible_catalog_item, service_catalog,
        service_request, service, host_type, order_value, result, action):
    """Test ordering and retiring ansible playbook service against default host, blank field and
    unavailable host.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/4h
        casecomponent: Ansible
        caseimportance: medium
        tags: ansible_embed
    """
    service_catalog.ansible_dialog_values = {"hosts": order_value}
    service_catalog.order()
    service_request.wait_for_request()
    if action == "retirement":
        service.retire()
    view = navigate_to(service, "Details")
    assert result == view.provisioning.details.get_text_of("Hosts")


@pytest.mark.tier(3)
def test_service_ansible_playbook_plays_table(service_catalog, service_request, service,
        soft_assert):
    """Plays table in provisioned and retired service should contain at least one row.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: low
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    service_catalog.order()
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    soft_assert(view.provisioning.plays.row_count > 1, "Plays table in provisioning tab is empty")
    service.retire()
    soft_assert(view.provisioning.plays.row_count > 1, "Plays table in retirement tab is empty")


@pytest.mark.tier(3)
def test_service_ansible_playbook_order_credentials(ansible_catalog_item, ansible_credential,
        service_catalog, appliance):
    """Test if credentials avaialable in the dropdown in ordering ansible playbook service
    screen.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {
            "machine_credential": ansible_credential.name
        }
    view = navigate_to(service_catalog, "Order")
    options = [o.text for o in (view.fields('credential')).visible_widget.all_options]
    assert ansible_credential.name in set(options)


@pytest.mark.tier(3)
@pytest.mark.parametrize("action", ["provisioning", "retirement"])
@pytest.mark.meta(blockers=[BZ(1614356, forced_streams=['5.10'])])
def test_service_ansible_playbook_pass_extra_vars(service_catalog, service_request, service,
        action):
    """Test if extra vars passed into ansible during ansible playbook service provision and
    retirement.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    service_catalog.order()
    service_request.wait_for_request()
    if action == "retirement":
        service.retire()
    view = navigate_to(service, "Details")
    stdout = getattr(view, action).standart_output
    stdout.wait_displayed()
    pre = stdout.text
    json_str = pre.split("--------------------------------")
    result_dict = json.loads(json_str[5].replace('", "', "").replace('\\"', '"').replace(
        '\\, "', '",').split('" ] } PLAY')[0])
    assert result_dict["some_var"] == "some_value"


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[
    BZ(1519275, forced_streams=['5.9']),
    BZ(1515841, forced_streams=['5.9'])
])
def test_service_ansible_execution_ttl(request, service_catalog, ansible_catalog_item, service,
         service_request):
    """Test if long running processes allowed to finish. There is a code that guarantees to have 100
    retries with a minimum of 1 minute per retry. So we need to run ansible playbook service more
    than 100 minutes and set max ttl greater than ansible playbook running time.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 2h
        tags: ansible_embed
    """
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {
            "playbook": "long_running_playbook.yml",
            "max_ttl": 200
        }

    def _revert():
        with update(ansible_catalog_item):
            ansible_catalog_item.provisioning = {
                "playbook": "dump_all_variables.yml",
                "max_ttl": ""
            }

    request.addfinalizer(_revert)
    service_catalog.order()
    service_request.wait_for_request(method="ui", num_sec=200 * 60, delay=120)
    view = navigate_to(service, "Details")
    assert view.provisioning.results.get_text_of("Status") == "successful"


@pytest.mark.tier(3)
def test_custom_button_ansible_credential_list(custom_service_button, service_catalog, service,
        service_request, appliance):
    """Test if credential list matches when the Ansible Playbook Service Dialog is invoked from a
    Button versus a Service Order Screen.
    https://bugzilla.redhat.com/show_bug.cgi?id=1448918

    Polarion:
        assignee: sbulage
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/3h
        tags: ansible_embed
    """
    service_catalog.order()
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    view.toolbar.custom_button(custom_service_button.group.text).item_select(
        custom_service_button.text)
    credentials_dropdown = BootstrapSelect(
        appliance.browser.widgetastic,
        locator=".//select[@id='credential']/.."
    )
    wait_for(lambda: credentials_dropdown.is_displayed, timeout=30)
    all_options = [option.text for option in credentials_dropdown.all_options]
    assert ["<Default>", "CFME Default Credential"] == all_options


@pytest.mark.tier(3)
def test_ansible_group_id_in_payload(service_catalog, service_request, service):
    """Test if group id is presented in manageiq payload.
    https://bugzilla.redhat.com/show_bug.cgi?id=1480019
    In order to get manageiq payload the service's standard output should be parsed.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    service_catalog.order()
    service_request.wait_for_request()
    view = navigate_to(service, "Details")
    stdout = view.provisioning.standart_output
    wait_for(lambda: stdout.is_displayed, timeout=10)
    pre = stdout.text
    json_str = pre.split("--------------------------------")
    # Standard output has several sections splitted by --------------------------------
    # Required data is located in 6th section
    # Then we need to replace or remove some characters to get a parsable json string
    result_dict = json.loads(json_str[5].replace('", "', "").replace('\\"', '"').replace(
        '\\, "', '",').split('" ] } PLAY')[0])
    assert "group" in result_dict["manageiq"]


@pytest.mark.provider([EC2Provider], scope="function")
def test_embed_tower_exec_play_against_amazon(request, provider, setup_provider,
        ansible_catalog_item, service, ansible_amazon_credential, service_catalog):
    """
    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {
            "playbook": "list_ec2_instances.yml",
            "cloud_type": "Amazon",
            "cloud_credential": ansible_amazon_credential.name
        }

    @request.addfinalizer
    def _revert():
        with update(ansible_catalog_item):
            ansible_catalog_item.provisioning = {
                "playbook": "dump_all_variables.yml",
                "cloud_type": "<Choose>"
            }

    service_request = service_catalog.order()
    service_request.wait_for_request(method="ui", num_sec=300, delay=20)
    view = navigate_to(service, "Details")
    assert view.provisioning.results.get_text_of("Status") == "successful"
