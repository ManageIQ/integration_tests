import datetime

import fauxfactory
import pytest
from manageiq_client.api import APIException
from manageiq_client.api import ManageIQClient as MiqApi
from manageiq_client.filters import Q

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import _creating_skeleton
from cfme.rest.gen_data import copy_role
from cfme.rest.gen_data import dialog as _dialog
from cfme.rest.gen_data import dialog_rest as _dialog_rest
from cfme.rest.gen_data import get_dialog_service_name
from cfme.rest.gen_data import groups
from cfme.rest.gen_data import orchestration_templates as _orchestration_templates
from cfme.rest.gen_data import service_catalog_obj as _service_catalog_obj
from cfme.rest.gen_data import service_catalogs as _service_catalogs
from cfme.rest.gen_data import service_templates as _service_templates
from cfme.rest.gen_data import service_templates_ui
from cfme.rest.gen_data import services as _services
from cfme.rest.gen_data import TEMPLATE_TORSO
from cfme.rest.gen_data import vm as _vm
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import get_vms_in_service
from cfme.utils.rest import query_resource_attributes
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(2),
    pytest.mark.provider(
        classes=[InfraProvider],
        required_fields=[
            ["provisioning", "template"],
            ["provisioning", "host"],
            ["provisioning", "datastore"],
            ["provisioning", "vlan"],
        ],
        selector=ONE,
    ),
    pytest.mark.usefixtures('setup_provider')
]


NUM_BUNDLE_ITEMS = 4


def wait_for_vm_power_state(vm, resulting_state):
    wait_for(
        lambda: vm.power_state == resulting_state,
        num_sec=1200, delay=45, fail_func=vm.reload,
        message='Wait for VM to {} (current state: {})'.format(
            resulting_state, vm.power_state))


def wait_for_retired(entity, num_sec=1000):
    def is_retired(entity):
        if not entity.collection.find_by(id=entity.id):
            return True
        try:
            entity.reload()
            return entity.retirement_state == 'retired'
        except Exception:
            pass
        return False

    # wait until retired, if this fails, settle with "retiring" state
    retval = wait_for(lambda: is_retired(entity), num_sec=num_sec, delay=10, silent_failure=True)
    if not retval:
        assert getattr(entity, 'retirement_state', None) == 'retiring'


def service_body(**kwargs):
    uid = fauxfactory.gen_alphanumeric(5)
    body = {
        'name': 'test_rest_service_{}'.format(uid),
        'description': 'Test REST Service {}'.format(uid),
    }
    body.update(kwargs)
    return body


@pytest.fixture(scope="function")
def dialog(request, appliance):
    return _dialog(request, appliance)


@pytest.fixture(scope="function")
def service_dialogs(request, appliance, num=3):
    service_dialogs = [_dialog_rest(request, appliance) for __ in range(num)]
    return service_dialogs


@pytest.fixture(scope="function")
def service_catalogs(request, appliance):
    response = _service_catalogs(request, appliance)
    assert_response(appliance)
    return response


@pytest.fixture(scope='function')
def catalog_bundle(request, dialog, service_catalog_obj, appliance, provider):
    catalog_items = service_templates_ui(
        request,
        appliance,
        service_dialog=dialog,
        service_catalog=service_catalog_obj,
        provider=provider,
        num=NUM_BUNDLE_ITEMS)

    uid = fauxfactory.gen_alphanumeric()
    bundle_name = 'test_rest_bundle_{}'.format(uid)
    bundle = appliance.collections.catalog_bundles.create(
        bundle_name,
        description='Test REST Bundle {}'.format(uid),
        display_in=True,
        catalog=service_catalog_obj,
        dialog=dialog,
        catalog_items=[item.name for item in catalog_items])

    catalog_rest = appliance.rest_api.collections.service_catalogs.get(
        name=service_catalog_obj.name)
    bundle_rest = catalog_rest.service_templates.get(name=bundle_name)

    yield bundle_rest

    if bundle.exists:
        bundle.delete()


@pytest.fixture(scope="function")
def service_catalog_obj(request, appliance):
    return _service_catalog_obj(request, appliance)


@pytest.fixture(scope="function")
def services(request, appliance, num=3):
    # create simple service using REST API
    bodies = [service_body() for _ in range(num)]
    collection = appliance.rest_api.collections.services
    new_services = collection.action.create(*bodies)
    assert_response(appliance)

    @request.addfinalizer
    def _finished():
        collection.reload()
        ids = [service.id for service in new_services]
        delete_entities = [service for service in collection if service.id in ids]
        if delete_entities:
            collection.action.delete(*delete_entities)

    return new_services


@pytest.fixture(scope="function")
def service_templates(request, appliance):
    response = _service_templates(request, appliance)
    assert_response(appliance)
    return response


@pytest.fixture(scope="function")
def vm_service(request, appliance, provider):
    return _services(request, appliance, provider).pop()


@pytest.fixture(scope="function")
def vm(request, provider, appliance):
    return _vm(request, provider, appliance)


@pytest.fixture(scope="function")
def delete_carts(appliance):
    """Makes sure there are no carts present before running the tests."""
    carts = appliance.rest_api.collections.service_orders.find_by(state="cart")
    if not carts:
        return
    carts = list(carts)
    cart_hrefs = [c._ref_repr() for c in carts]
    appliance.rest_api.collections.service_orders.action.delete(*cart_hrefs)
    assert_response(appliance)
    for cart in carts:
        cart.wait_not_exists()


@pytest.fixture(scope="function")
def cart(appliance, delete_carts):
    cart = appliance.rest_api.collections.service_orders.action.create(name="cart")
    assert_response(appliance)
    cart = cart[0]

    yield cart

    if cart.exists:
        cart.action.delete()


@pytest.fixture
def deny_service_ordering(appliance):
    """
    `allow_api_service_ordering` is set to True by default, which allows ordering services
    via API. This fixture sets that value to False, so services cannot be ordered via API.
    """
    reset_setting = appliance.advanced_settings["product"]["allow_api_service_ordering"]
    appliance.update_advanced_settings(
        {"product": {"allow_api_service_ordering": False}}
    )
    assert not appliance.advanced_settings["product"]["allow_api_service_ordering"]

    yield

    appliance.update_advanced_settings(
        {"product": {"allow_api_service_ordering": reset_setting}}
    )
    assert appliance.advanced_settings["product"]["allow_api_service_ordering"] == reset_setting


def unassign_templates(templates):
    rest_api = templates[0].collection.api
    for template in templates:
        template.reload()
        # if the template is already assigned, unassign it first
        if hasattr(template, 'service_template_catalog_id'):
            scl_a = rest_api.collections.service_catalogs.get(
                id=template.service_template_catalog_id)
            scl_a.service_templates.action.unassign(template)
            template.reload()


class TestServiceRESTAPI(object):
    def test_query_service_attributes(self, services, soft_assert):
        """Tests access to service attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/30h
            tags: service
        """
        outcome = query_resource_attributes(services[0])
        for failure in outcome.failed:
            if failure.name == "reconfigure_dialog"and BZ(1663972).blocks:
                continue
            soft_assert(False, '{0} "{1}": status: {2}, error: `{3}`'.format(
                failure.type, failure.name, failure.response.status_code, failure.error))

    def test_edit_service(self, appliance, services):
        """Tests editing a service.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/services (method ``edit``) with the ``name``
            * Check if the service with ``new_name`` exists
        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/3h
            tags: service
        """
        for service in services:
            new_name = fauxfactory.gen_alphanumeric()
            response = service.action.edit(name=new_name)
            assert_response(appliance)
            assert response.name == new_name
            service.reload()
            assert service.name == new_name

    def test_edit_multiple_services(self, appliance, services):
        """Tests editing multiple services at a time.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/services (method ``edit``) with the list of dictionaries used to edit
            * Check if the services with ``new_name`` each exists
        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/3h
            tags: service
        """
        new_names = []
        services_data_edited = []
        for service in services:
            new_name = fauxfactory.gen_alphanumeric()
            new_names.append(new_name)
            services_data_edited.append({
                "href": service.href,
                "name": new_name,
            })
        response = appliance.rest_api.collections.services.action.edit(*services_data_edited)
        assert_response(appliance)
        for i, resource in enumerate(response):
            assert resource.name == new_names[i]
            service = services[i]
            service.reload()
            assert service.name == new_names[i]

    def test_delete_service_post(self, services):
        """Tests deleting services from detail using POST method.

        Metadata:
            test_flag: rest

        Bugzilla:
            1414852

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_detail(services, method='POST')

    def test_delete_service_delete(self, services):
        """Tests deleting services from detail using DELETE method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_detail(services, method='DELETE')

    def test_delete_services(self, services):
        """Tests deleting services from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/3h
            tags: service
        """
        delete_resources_from_collection(services)

    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_retire_service_now(self, appliance, vm_service, from_detail):
        """Test retiring a service now.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        vm = get_vms_in_service(vm_service).pop()

        if from_detail:
            vm_service.action.request_retire()
            assert_response(appliance)
        else:
            collection.action.request_retire(vm_service)
            assert_response(appliance)

        wait_for_retired(vm_service)
        wait_for_retired(vm)

    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_retire_service_future(self, appliance, services, from_detail):
        """Test retiring a service in future.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/3h
            tags: service
        """
        date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%Y/%m/%d")
        future = {
            "date": date,
            "warn": "4",
        }

        if from_detail:
            for service in services:
                service.action.retire(**future)
                assert_response(appliance)
        else:
            appliance.rest_api.collections.services.action.retire(*services, **future)
            assert_response(appliance)

        def _finished(service):
            service.reload()
            return hasattr(service, "retires_on") and hasattr(service, "retirement_warn")

        for service in services:
            wait_for(
                lambda: _finished(service),
                num_sec=60,
                delay=5
            )

    @pytest.mark.parametrize(
        "from_detail", [True, False], ids=["from_detail", "from_collection"]
    )
    @test_requirements.rest
    def test_service_retirement_methods(
        self, request, appliance, services, from_detail
    ):
        """Test retiring a service with old method `retire` and new method `request_retire`.
        Old method is no longer supported and it puts the service into `intializing` state.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            initialEstimate: 1/4h

        Bugzilla:
            1698480
            1713477
        """
        service = services[0]

        auto_log = LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[
                ".*ERROR -- : <AEMethod start_retirement> Service retire task not found",
                ".*ERROR -- : <AEMethod start_retirement> The old style retirement is incompatible"
                " with the new retirement state machine.",
                ".*ERROR -- : State=<StartRetirement> running  raised exception:"
                " <Method exited with rc=MIQ_ABORT>",
                ".*ERROR -- : <AEMethod update_service_retirement_status> Service Retire Error:",
            ],
        )
        auto_log.start_monitoring()

        if from_detail:
            service.action.retire()
        else:
            appliance.rest_api.collections.services.action.retire(service)

        assert_response(appliance)
        wait_for(
            lambda: hasattr(service, "retirement_state"),
            fail_func=service.reload,
            num_sec=50,
            delay=5,
        )
        assert auto_log.validate(wait="180s")

        assert service.retirement_state == "initializing"

        if from_detail:
            service.action.request_retire()
        else:
            appliance.rest_api.collections.services.action.request_retire(service)

        assert_response(appliance)
        wait_for_retired(service)

    def test_set_service_owner(self, appliance, services):
        """Tests set_ownership action on /api/services/:id.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        user = appliance.rest_api.collections.users.get(userid="admin")
        data = {
            "owner": {"href": user.href}
        }
        for service in services:
            service.action.set_ownership(**data)
            assert_response(appliance)
            service.reload()
            assert hasattr(service, "evm_owner_id")
            assert service.evm_owner_id == user.id

    def test_set_services_owner(self, appliance, services):
        """Tests set_ownership action on /api/services collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        user = appliance.rest_api.collections.users.get(userid="admin")
        requests = [{
            "href": service.href,
            "owner": {"href": user.href}
        } for service in services]
        appliance.rest_api.collections.services.action.set_ownership(*requests)
        assert_response(appliance)
        for service in services:
            service.reload()
            assert hasattr(service, "evm_owner_id")
            assert service.evm_owner_id == user.id

    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_power_service(self, appliance, vm_service, from_detail):
        """Tests power operations on /api/services and /api/services/:id.

        * start, stop and suspend actions
        * transition from one power state to another

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        vm = get_vms_in_service(vm_service).pop()

        def _action_and_check(action, resulting_state):
            if from_detail:
                getattr(vm_service.action, action)()
            else:
                getattr(collection.action, action)(vm_service)
            assert_response(appliance)
            wait_for_vm_power_state(vm, resulting_state)

        wait_for_vm_power_state(vm, 'on')
        _action_and_check('stop', 'off')
        _action_and_check('start', 'on')
        _action_and_check('suspend', 'suspended')
        _action_and_check('start', 'on')

    def test_service_vm_subcollection(self, vm_service):
        """Tests /api/services/:id/vms.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        vm = get_vms_in_service(vm_service).pop()
        assert vm_service.vms[0].id == vm.id

    def test_service_add_resource(self, request, appliance, vm):
        """Tests adding resource to service.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        service = services(request, appliance, num=1).pop()
        rest_vm = appliance.rest_api.collections.vms.get(name=vm)

        assert not service.vms
        service.action.add_resource(resource=rest_vm._ref_repr())
        assert_response(appliance)
        assert len(service.vms) == 1

    def test_service_remove_resource(self, request, appliance, vm_service):
        """Tests removing resource from service.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        vm = get_vms_in_service(vm_service).pop()
        request.addfinalizer(vm.action.delete)

        vms_num = len(vm_service.vms)
        assert vms_num >= 1
        vm_service.action.remove_resource(resource=vm._ref_repr())
        assert_response(appliance)
        assert len(vm_service.vms) == vms_num - 1

    def test_service_remove_all_resources(self, request, appliance, vm, vm_service):
        """Tests removing all resources from service.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        vm_assigned = get_vms_in_service(vm_service).pop()
        vm_added = appliance.rest_api.collections.vms.get(name=vm)

        @request.addfinalizer
        def _delete_vms():
            vm_assigned.action.delete()
            vm_added.action.delete()

        vm_service.action.add_resource(resource=vm_added._ref_repr())
        assert len(vm_service.vms) >= 2
        vm_service.action.remove_all_resources()
        assert_response(appliance)
        assert not vm_service.vms

    def test_create_service_from_parent(self, request, appliance):
        """Tests creation of new service that reference existing service.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        service = collection.action.create(service_body())[0]
        request.addfinalizer(service.action.delete)
        bodies = []
        references = [{'id': service.id}, {'href': service.href}]
        for ref in references:
            bodies.append(service_body(parent_service=ref))
        response = collection.action.create(*bodies)
        assert_response(appliance)
        for ent in response:
            assert ent.ancestry == str(service.id)

    def test_delete_parent_service(self, appliance):
        """Tests that when parent service is deleted, child service is deleted automatically.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        grandparent = collection.action.create(service_body())[0]
        parent = collection.action.create(service_body(parent_service={'id': grandparent.id}))[0]
        child = collection.action.create(service_body(parent_service={'id': parent.id}))[0]
        assert parent.ancestry == str(grandparent.id)
        assert child.ancestry == '{}/{}'.format(grandparent.id, parent.id)
        grandparent.action.delete()
        assert_response(appliance)
        wait_for(
            lambda: not appliance.rest_api.collections.services.find_by(name=grandparent.name),
            num_sec=600,
            delay=10,
        )
        for gen in child, parent, grandparent:
            with pytest.raises(Exception, match="ActiveRecord::RecordNotFound"):
                gen.action.delete()

    def test_add_service_parent(self, request, appliance):
        """Tests adding parent reference to already existing service.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        parent = collection.action.create(service_body())[0]
        request.addfinalizer(parent.action.delete)
        child = collection.action.create(service_body())[0]
        child.action.edit(parent_service=parent._ref_repr())
        assert_response(appliance)
        child.reload()
        assert child.ancestry == str(parent.id)

    @pytest.mark.meta(blockers=[BZ(1496936)])
    def test_add_child_resource(self, request, appliance):
        """Tests adding parent reference to already existing service using add_resource.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        parent = collection.action.create(service_body())[0]
        request.addfinalizer(parent.action.delete)
        child = collection.action.create(service_body())[0]
        parent.action.add_resource(resource=child._ref_repr())
        assert_response(appliance)
        child.reload()
        assert child.ancestry == str(parent.id)

    def test_power_parent_service(self, request, appliance, vm_service):
        """Tests that power operations triggered on service parent affects child service.

        * start, stop and suspend actions
        * transition from one power state to another

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        service = collection.action.create(service_body())[0]
        request.addfinalizer(service.action.delete)
        child = vm_service
        vm = get_vms_in_service(child).pop()
        service.action.add_resource(resource=child._ref_repr())
        assert_response(appliance)

        def _action_and_check(action, resulting_state):
            getattr(service.action, action)()
            assert_response(appliance)
            wait_for_vm_power_state(vm, resulting_state)

        wait_for_vm_power_state(vm, 'on')
        _action_and_check('stop', 'off')
        _action_and_check('start', 'on')
        _action_and_check('suspend', 'suspended')
        _action_and_check('start', 'on')

    @pytest.mark.meta(blockers=[BZ(1496936), BZ(1608958)])
    def test_retire_parent_service_now(self, request, appliance):
        """Tests that child service is retired together with a parent service.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        collection = appliance.rest_api.collections.services
        parent = collection.action.create(service_body())[0]
        request.addfinalizer(parent.action.delete)
        child = collection.action.create(service_body())[0]
        parent.action.add_resource(resource=child._ref_repr())
        assert_response(appliance)

        parent.action.request_retire()
        assert_response(appliance)

        wait_for_retired(parent)
        wait_for_retired(child)


@test_requirements.rest
class TestServiceDialogsRESTAPI(object):
    def check_returned_dialog(self, appliance):
        returned = appliance.rest_api.response.json()
        if 'results' in returned:
            results = returned['results']
        else:
            results = [returned]
        for result in results:
            dialog_tabs, = result['dialog_tabs']
            dialog_groups, = dialog_tabs['dialog_groups']
            dialog_fields, = dialog_groups['dialog_fields']
            assert dialog_fields['name']

    def test_query_service_dialog_attributes(self, service_dialogs, soft_assert):
        """Tests access to service dialog attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(service_dialogs[0], soft_assert=soft_assert)

    def test_check_dialog_returned_create(self, request, appliance):
        """Tests that the full dialog is returned as part of the API response on create.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        _dialog_rest(request, appliance)
        assert_response(appliance)
        self.check_returned_dialog(appliance)

    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_service_dialogs(self, appliance, service_dialogs, from_detail):
        """Tests editing service dialog using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        new_descriptions = []
        if from_detail:
            edited = []
            for dialog in service_dialogs:
                new_description = fauxfactory.gen_alphanumeric(18, start="Test Dialog ").lower()
                new_descriptions.append(new_description)
                edited.append(dialog.action.edit(description=new_description))
                assert_response(appliance)
                self.check_returned_dialog(appliance)
        else:
            catalog_edited = []
            for dialog in service_dialogs:
                new_description = fauxfactory.gen_alphanumeric(18, start="Test Dialog ").lower()
                new_descriptions.append(new_description)
                dialog.reload()
                catalog_edited.append({
                    'href': dialog.href,
                    'description': new_description,
                })
            edited = appliance.rest_api.collections.service_dialogs.action.edit(*catalog_edited)
            assert_response(appliance)
            self.check_returned_dialog(appliance)
        assert len(edited) == len(service_dialogs)
        for index, dialog in enumerate(service_dialogs):
            record, __ = wait_for(
                lambda: appliance.rest_api.collections.service_dialogs.find_by(
                    description=new_descriptions[index]) or False,
                num_sec=180,
                delay=10,
            )
            dialog.reload()
            assert dialog.description == edited[index].description
            assert dialog.description == record[0].description
            assert dialog.description == new_descriptions[index]

    @pytest.mark.parametrize("method", ["post", "delete"])
    def test_delete_service_dialog(self, service_dialogs, method):
        """Tests deleting service dialogs from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_detail(service_dialogs, method=method)

    def test_delete_service_dialogs(self, service_dialogs):
        """Tests deleting service dialogs from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_collection(service_dialogs)


class TestServiceTemplateRESTAPI(object):
    def test_query_service_templates_attributes(self, service_templates, soft_assert):
        """Tests access to service template attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(service_templates[0], soft_assert=soft_assert)

    def test_create_service_templates(self, appliance, service_templates):
        """Tests creation of service templates.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        for service_template in service_templates:
            record = appliance.rest_api.collections.service_templates.get(id=service_template.id)
            assert record.name == service_template.name
            assert record.description == service_template.description

    def test_edit_service_template(self, appliance, service_templates):
        """Tests editing a service template.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_templates (method ``edit``) with the ``name``
            * Check if the service_template with ``new_name`` exists
        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        for service_template in service_templates:
            new_name = fauxfactory.gen_alphanumeric()
            response = service_template.action.edit(name=new_name)
            assert_response(appliance)
            assert response.name == new_name
            service_template.reload()
            assert service_template.name == new_name

    def test_delete_service_templates(self, service_templates):
        """Tests deleting service templates from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_collection(service_templates)

    def test_delete_service_template_post(self, service_templates):
        """Tests deleting service templates from detail using POST method.

        Metadata:
            test_flag: rest

        Bugzilla:
            1427338

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_detail(service_templates, method='POST')

    def test_delete_service_template_delete(self, service_templates):
        """Tests deleting service templates from detail using DELETE method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_detail(service_templates, method='DELETE')

    def test_assign_unassign_service_template_to_service_catalog(self, appliance, service_catalogs,
            service_templates):
        """Tests assigning and unassigning the service templates to service catalog.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_catalogs/<id>/service_templates (method ``assign``)
                with the list of dictionaries service templates list
            * Check if the service_templates were assigned to the service catalog
            * POST /api/service_catalogs/<id>/service_templates (method ``unassign``)
                with the list of dictionaries service templates list
            * Check if the service_templates were unassigned to the service catalog
        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """

        stpl = service_templates[0]
        scl = service_catalogs[0]

        unassign_templates([stpl])

        scl.service_templates.action.assign(stpl)
        assert_response(appliance)
        scl.reload()
        stpl.reload()
        assert stpl.id in [st.id for st in scl.service_templates.all]
        assert stpl.service_template_catalog_id == scl.id

        scl.service_templates.action.unassign(stpl)
        assert_response(appliance)
        scl.reload()
        assert stpl.id not in [st.id for st in scl.service_templates.all]
        # load data again so we get rid of attributes that are no longer there
        stpl = appliance.rest_api.collections.service_templates.get(id=stpl.id)
        assert not hasattr(stpl, 'service_template_catalog_id')

    def test_edit_multiple_service_templates(self, appliance, service_templates):
        """Tests editing multiple service templates at time.

        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_templates (method ``edit``)
                with the list of dictionaries used to edit
            * Check if the service_templates with ``new_name`` each exists
        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        new_names = []
        service_tpls_data_edited = []
        for tpl in service_templates:
            new_name = fauxfactory.gen_alphanumeric()
            new_names.append(new_name)
            service_tpls_data_edited.append({
                "href": tpl.href,
                "name": new_name,
            })
        response = appliance.rest_api.collections.service_templates.action.edit(
            *service_tpls_data_edited)
        assert_response(appliance)
        for i, resource in enumerate(response):
            assert resource.name == new_names[i]
            service_template = service_templates[i]
            service_template.reload()
            assert service_template.name == new_names[i]


class TestServiceCatalogsRESTAPI(object):
    def test_query_service_catalog_attributes(self, service_catalogs, soft_assert):
        """Tests access to service catalog attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        outcome = query_resource_attributes(service_catalogs[0])
        for failure in outcome.failed:
            soft_assert(False, '{0} "{1}": status: {2}, error: `{3}`'.format(
                failure.type, failure.name, failure.response.status_code, failure.error))

    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_catalogs(self, appliance, service_catalogs, from_detail):
        """Tests editing catalog items using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        new_descriptions = []
        if from_detail:
            edited = []
            for catalog in service_catalogs:
                new_description = fauxfactory.gen_alphanumeric(18, start="Test Catalog ").lower()
                new_descriptions.append(new_description)
                edited.append(catalog.action.edit(description=new_description))
                assert_response(appliance)
        else:
            catalog_edited = []
            for catalog in service_catalogs:
                new_description = fauxfactory.gen_alphanumeric(18, start="Test Catalog ").lower()
                new_descriptions.append(new_description)
                catalog.reload()
                catalog_edited.append({
                    'href': catalog.href,
                    'description': new_description,
                })
            edited = appliance.rest_api.collections.service_catalogs.action.edit(*catalog_edited)
            assert_response(appliance)
        assert len(edited) == len(service_catalogs)
        for index, catalog in enumerate(service_catalogs):
            record, __ = wait_for(
                lambda: appliance.rest_api.collections.service_catalogs.find_by(
                    description=new_descriptions[index]) or False,
                num_sec=180,
                delay=10,
            )
            catalog.reload()
            assert catalog.description == edited[index].description
            assert catalog.description == record[0].description

    def test_order_single_catalog_item(
            self, request, appliance, service_catalogs, service_templates):
        """Tests ordering single catalog item using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        catalog = service_catalogs[0]
        unassign_templates(service_templates)

        for template in service_templates:
            catalog.service_templates.action.assign(template)

        catalog.service_templates.reload()
        template = catalog.service_templates[0]

        # this doesn't return resource in the "service_requests" collection
        # using workaround with `response.json()`
        template.action.order()
        results = appliance.rest_api.response.json()
        assert_response(appliance)

        service_request = appliance.rest_api.get_entity('service_requests', results['id'])

        def _order_finished():
            service_request.reload()
            return (
                service_request.status.lower() == 'ok' and
                service_request.request_state.lower() == 'finished')

        wait_for(_order_finished, num_sec=180, delay=10)

        service_name = get_dialog_service_name(appliance, service_request, template.name)
        assert '[{}]'.format(service_name) in service_request.message
        source_id = str(service_request.source_id)
        new_service = appliance.rest_api.collections.services.get(service_template_id=source_id)
        assert new_service.name == service_name

        @request.addfinalizer
        def _finished():
            new_service.action.delete()

    def test_order_multiple_catalog_items(
            self, request, appliance, service_catalogs, service_templates):
        """Tests ordering multiple catalog items using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        catalog = service_catalogs[0]
        unassign_templates(service_templates)

        for template in service_templates:
            catalog.service_templates.action.assign(template)
            template.reload()

        # this doesn't return resource in the "service_requests" collection
        # using workaround with `response.json()`
        catalog.service_templates.action.order(*service_templates)
        results = appliance.rest_api.response.json()
        results = results['results']
        assert_response(appliance)

        assert 'href' in results[0], "BZ 1480281 doesn't seem to be fixed"

        def _order_finished(service_request):
            service_request.reload()
            return (
                service_request.status.lower() == 'ok' and
                service_request.request_state.lower() == 'finished')

        new_services = []
        for result in results:
            service_request = appliance.rest_api.get_entity('service_requests', result['id'])
            wait_for(_order_finished, func_args=[service_request], num_sec=180, delay=10)

            # service name check
            service_name = get_dialog_service_name(
                appliance,
                service_request,
                *[t.name for t in catalog.service_templates.all]
            )
            assert '[{}]'.format(service_name) in service_request.message

            # Service name can no longer be used to uniquely identify service when multiple
            # services are using the same dialog (all services have the same name).
            # Using service template id instead.
            source_id = str(service_request.source_id)
            new_service = appliance.rest_api.collections.services.get(service_template_id=source_id)
            assert new_service.name == service_name
            new_services.append(new_service)

        @request.addfinalizer
        def _finished():
            appliance.rest_api.collections.services.action.delete(*new_services)

    def test_order_catalog_bundle(self, appliance, request, catalog_bundle):
        """Tests ordering catalog bundle using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        # this doesn't return resource in the "service_requests" collection
        # using workaround with `response.json()`
        catalog_bundle.action.order()
        results = appliance.rest_api.response.json()
        assert_response(appliance)

        service_request = appliance.rest_api.get_entity('service_requests', results['id'])

        def _order_finished():
            service_request.reload()
            return (
                service_request.status.lower() == 'ok' and
                service_request.request_state.lower() == 'finished')

        wait_for(_order_finished, num_sec=2000, delay=10)

        service_name = get_dialog_service_name(appliance, service_request, catalog_bundle.name)
        assert '[{}]'.format(service_name) in service_request.message
        source_id = str(service_request.source_id)
        new_service = appliance.rest_api.collections.services.get(service_template_id=source_id)
        assert new_service.name == service_name

        @request.addfinalizer
        def _finished():
            new_service.action.delete()

        vms = new_service.vms
        vms.reload()
        assert len(vms) == NUM_BUNDLE_ITEMS
        children = appliance.rest_api.collections.services.find_by(ancestry=str(new_service.id))
        assert len(children) == NUM_BUNDLE_ITEMS

    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_catalog_from_detail(self, service_catalogs, method):
        """Tests delete service catalogs from detail using REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_detail(service_catalogs, method=method, num_sec=100, delay=5)

    def test_delete_catalog_from_collection(self, service_catalogs):
        """Tests delete service catalogs from detail using REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_collection(service_catalogs, num_sec=300, delay=5)


class TestPendingRequestsRESTAPI(object):
    def _get_instance(self, miq_domain):
        auto_class = (miq_domain
                      .namespaces.instantiate(name='Service')
                      .namespaces.instantiate(name='Provisioning')
                      .namespaces.instantiate(name='StateMachines')
                      .classes.instantiate(name='ServiceProvisionRequestApproval'))
        instance = auto_class.instances.instantiate(
            name='Default',
            display_name=None,
            description=None,
            fields=None)
        return instance

    @pytest.fixture(scope='class')
    def new_domain(self, request, appliance):
        """Creates new domain and copy instance from ManageIQ to this domain."""
        dc = appliance.collections.domains
        domain = dc.create(name=fauxfactory.gen_alphanumeric(12, start="domain_"), enabled=True)
        request.addfinalizer(domain.delete_if_exists)
        miq_domain = dc.instantiate(name='ManageIQ')
        instance = self._get_instance(miq_domain)
        instance.copy_to(domain)
        return domain

    @pytest.fixture(scope='class')
    def modified_instance(self, new_domain):
        """Modifies the instance in new domain to change it to manual approval instead of auto."""
        instance = self._get_instance(new_domain)
        with update(instance):
            instance.fields = {'approval_type': {'value': 'manual'}}

    @pytest.fixture(scope='function')
    def pending_request(
            self, request, appliance, service_catalogs, service_templates, modified_instance):
        catalog = service_catalogs[0]
        unassign_templates(service_templates)

        for template in service_templates:
            catalog.service_templates.action.assign(template)

        catalog.service_templates.reload()
        template = catalog.service_templates[0]

        # this doesn't return resource in the "service_requests" collection
        # using workaround with `response.json()`
        template.action.order()
        results = appliance.rest_api.response.json()
        assert_response(appliance)

        service_request = appliance.rest_api.get_entity('service_requests', results['id'])

        @request.addfinalizer
        def _delete_if_exists():
            try:
                service_request.action.delete()
            except Exception:
                # can be already deleted
                pass

        def _order_pending():
            service_request.reload()
            return (
                service_request.request_state.lower() == 'pending' and
                service_request.approval_state.lower() == 'pending_approval')

        wait_for(_order_pending, num_sec=30, delay=2)

        return service_request

    def test_query_service_request_attributes(self, pending_request, soft_assert):
        """Tests access to service request attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(pending_request, soft_assert=soft_assert)

    def test_create_pending_request(self, pending_request):
        """Tests creating pending service request using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        # Wait a bit to check that it will not get auto-approved
        # This `wait_for` is expected to fail.
        wait_for(
            lambda: pending_request.approval_state.lower() != 'pending_approval',
            fail_func=pending_request.reload,
            silent_failure=True,
            num_sec=10,
            delay=2)
        assert pending_request.approval_state.lower() == 'pending_approval'

    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_pending_request_from_detail(self, pending_request, method):
        """Tests deleting pending service request from detail using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        delete_resources_from_detail([pending_request], method=method)

    def test_delete_pending_request_from_collection(self, pending_request):
        """Tests deleting pending service request from detail using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        delete_resources_from_collection([pending_request])

    def test_order_manual_approval(self, request, appliance, pending_request):
        """Tests ordering single catalog item with manual approval using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        pending_request.action.approve(reason='I said so.')
        assert_response(appliance)

        def _order_approved():
            pending_request.reload()
            return (
                pending_request.request_state.lower() == 'finished' and
                pending_request.approval_state.lower() == 'approved' and
                pending_request.status.lower() == 'ok')

        wait_for(_order_approved, num_sec=180, delay=10)

        source_id = str(pending_request.source_id)
        new_service = appliance.rest_api.collections.services.get(service_template_id=source_id)
        assert '[{}]'.format(new_service.name) in pending_request.message

        request.addfinalizer(new_service.action.delete)

    def test_order_manual_denial(self, appliance, pending_request):
        """Tests ordering single catalog item with manual denial using the REST API.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        pending_request.action.deny(reason='I said so.')
        assert_response(appliance)

        def _order_denied():
            pending_request.reload()
            return (
                pending_request.request_state.lower() == 'finished' and
                pending_request.approval_state.lower() == 'denied' and
                pending_request.status.lower() == 'denied')

        wait_for(_order_denied, num_sec=30, delay=2)


class TestServiceRequests(object):
    @pytest.fixture(scope='class')
    def new_role(self, appliance):
        role = copy_role(appliance, 'EvmRole-user_self_service')
        # allow role to access all Services, VMs, and Templates
        role.action.edit(settings=None)
        yield role
        role.action.delete()

    @pytest.fixture(scope='class')
    def new_group(self, request, appliance, new_role):
        return groups(request, appliance, new_role, num=1)

    @pytest.fixture(scope='class')
    def user_auth(self, request, appliance, new_group):
        password = fauxfactory.gen_alphanumeric()
        data = [{
            "userid": fauxfactory.gen_alphanumeric(start="rest_").lower(),
            "name": fauxfactory.gen_alphanumeric(15, start="REST User "),
            "password": password,
            "group": {"id": new_group.id}
        }]

        user = _creating_skeleton(request, appliance, 'users', data)
        user = user[0]
        return user.userid, password

    @pytest.fixture(scope='class')
    def user_api(self, appliance, user_auth):
        entry_point = appliance.rest_api._entry_point
        return MiqApi(entry_point, user_auth, verify_ssl=False)

    def test_user_item_order(self, appliance, request, user_api):
        """Tests ordering a catalog item using the REST API as a non-admin user.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        new_template = _service_templates(request, appliance, num=1)
        new_template = new_template[0]
        catalog_id = new_template.service_template_catalog_id
        template_id = new_template.id

        catalog = user_api.get_entity('service_catalogs', catalog_id)
        templates_collection = catalog.service_templates
        template_href = '{}/service_templates/{}'.format(catalog.href, template_id)

        # The "order" action doesn't return resource in the "service_requests" collection
        # using workaround with `response.json()`
        templates_collection.action.order(href=template_href)
        assert user_api.response
        result = user_api.response.json()
        result = result['results'][0]

        service_request = appliance.rest_api.get_entity('service_requests', result['id'])

        def _order_finished():
            service_request.reload()
            return (
                service_request.status.lower() == 'ok' and
                service_request.request_state.lower() == 'finished')

        wait_for(_order_finished, num_sec=180, delay=10)

        service_name = get_dialog_service_name(appliance, service_request, new_template.name)
        assert '[{}]'.format(service_name) in service_request.message
        source_id = str(service_request.source_id)
        new_service = appliance.rest_api.collections.services.get(service_template_id=source_id)
        assert new_service.name == service_name
        request.addfinalizer(new_service.action.delete)


class TestOrchestrationTemplatesRESTAPI(object):
    @pytest.fixture(scope='function')
    def orchestration_templates(self, request, appliance):
        num = 2
        response = _orchestration_templates(request, appliance, num=num)
        assert_response(appliance)
        assert len(response) == num
        return response

    def test_query_orchestration_templates_attributes(self, orchestration_templates, soft_assert):
        """Tests access to orchestration templates attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(orchestration_templates[0], soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_orchestration_templates(self, appliance, orchestration_templates):
        """Tests creation of orchestration templates.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        for template in orchestration_templates:
            record = appliance.rest_api.collections.orchestration_templates.get(id=template.id)
            assert record.name == template.name
            assert record.description == template.description
            assert record.type == template.type

    @pytest.mark.tier(3)
    def test_delete_orchestration_templates_from_collection(self, orchestration_templates):
        """Tests deleting orchestration templates from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(orchestration_templates, not_found=True)

    @pytest.mark.tier(3)
    def test_delete_orchestration_templates_from_detail_post(self, orchestration_templates):
        """Tests deleting orchestration templates from detail using POST method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(orchestration_templates, method='POST')

    @pytest.mark.tier(3)
    def test_delete_orchestration_templates_from_detail_delete(self, orchestration_templates):
        """Tests deleting orchestration templates from detail using DELETE method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(orchestration_templates, method='DELETE')

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_edit_orchestration_templates(self, appliance, orchestration_templates, from_detail):
        """Tests editing of orchestration templates.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        response_len = len(orchestration_templates)
        new = [{
            'description': fauxfactory.gen_alphanumeric(26, start="Updated Test Template ")
        } for _ in range(response_len)]
        if from_detail:
            edited = []
            for i in range(response_len):
                edited.append(orchestration_templates[i].action.edit(**new[i]))
                assert_response(appliance)
        else:
            for i in range(response_len):
                new[i].update(orchestration_templates[i]._ref_repr())
            edited = appliance.rest_api.collections.orchestration_templates.action.edit(*new)
            assert_response(appliance)
        assert len(edited) == response_len
        for i in range(response_len):
            assert edited[i].description == new[i]['description']
            orchestration_templates[i].reload()
            assert orchestration_templates[i].description == new[i]['description']

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_copy_orchestration_templates(self, request, appliance, orchestration_templates,
            from_detail):
        """Tests copying of orchestration templates.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        num_orch_templates = len(orchestration_templates)
        new = []
        for _ in range(num_orch_templates):
            uniq = fauxfactory.gen_alphanumeric(5)
            new.append({
                "name": "test_copied_{}".format(uniq),
                "content": "{{ 'Description' : '{}' }}\n".format(uniq)
            })
        if from_detail:
            copied = []
            for i in range(num_orch_templates):
                copied.append(orchestration_templates[i].action.copy(**new[i]))
                assert_response(appliance)
        else:
            for i in range(num_orch_templates):
                new[i].update(orchestration_templates[i]._ref_repr())
            copied = appliance.rest_api.collections.orchestration_templates.action.copy(*new)
            assert_response(appliance)

        request.addfinalizer(
            lambda: appliance.rest_api.collections.orchestration_templates.action.delete(*copied))

        assert len(copied) == num_orch_templates
        for i in range(num_orch_templates):
            orchestration_templates[i].reload()
            assert copied[i].name == new[i]['name']
            assert orchestration_templates[i].id != copied[i].id
            assert orchestration_templates[i].name != copied[i].name
            assert orchestration_templates[i].description == copied[i].description
            new_record = appliance.rest_api.collections.orchestration_templates.get(id=copied[i].id)
            assert new_record.name == copied[i].name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_invalid_copy_orchestration_templates(self, appliance, orchestration_templates,
            from_detail):
        """Tests copying of orchestration templates without changing content.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        num_orch_templates = len(orchestration_templates)
        new = []
        for _ in range(num_orch_templates):
            new.append({
                "name": fauxfactory.gen_alphanumeric(18, start="test_copied_")
            })
        if from_detail:
            for i in range(num_orch_templates):
                with pytest.raises(Exception, match="content must be unique"):
                    orchestration_templates[i].action.copy(**new[i])
                assert_response(appliance, http_status=400)
        else:
            for i in range(num_orch_templates):
                new[i].update(orchestration_templates[i]._ref_repr())
            with pytest.raises(Exception, match="content must be unique"):
                appliance.rest_api.collections.orchestration_templates.action.copy(*new)
            assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    def test_invalid_template_type(self, appliance):
        """Tests that template creation fails gracefully when invalid type is specified.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        uniq = fauxfactory.gen_alphanumeric(5)
        payload = {
            'name': 'test_{}'.format(uniq),
            'description': 'Test Template {}'.format(uniq),
            'type': 'InvalidOrchestrationTemplateType',
            'orderable': False,
            'draft': False,
            'content': TEMPLATE_TORSO.replace('CloudFormation', uniq)
        }
        with pytest.raises(Exception, match='Api::BadRequestError'):
            appliance.rest_api.collections.orchestration_templates.action.create(payload)
        assert_response(appliance, http_status=400)


class TestServiceOrderCart(object):
    @pytest.fixture(scope="class")
    def service_templates_class(self, request, appliance):
        return service_templates(request, appliance)

    def add_requests(self, cart, service_templates):
        body = [{'service_template_href': tmplt.href} for tmplt in service_templates]
        response = cart.service_requests.action.add(*body)
        assert_response(cart.collection._api)
        assert len(response) == len(service_templates)
        assert cart.service_requests.subcount == len(response)
        return response

    def test_query_cart_attributes(self, cart, soft_assert):
        """Tests access to cart attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Services
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(cart, soft_assert=soft_assert)

    @pytest.mark.tier(3)
    def test_create_empty_cart(self, appliance, cart):
        """Tests creating an empty cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        assert cart.state == 'cart'
        cart_dict = appliance.rest_api.get('{}/cart'.format(cart.collection._href))
        assert cart_dict['id'] == cart.id

    @pytest.mark.tier(3)
    def test_create_second_cart(self, request, appliance, cart):
        """Tests that it's not possible to create second cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        # This will fail somehow once BZ 1493788 is fixed.
        # There can be one and only one shopping cart for the authenticated user.
        second_cart = appliance.rest_api.collections.service_orders.action.create(name="cart2")
        second_cart = second_cart[0]
        request.addfinalizer(second_cart.action.delete)
        assert second_cart.state == 'cart'

    @pytest.mark.tier(3)
    def test_create_cart(self, request, appliance, service_templates):
        """Tests creating a cart with service requests.

        Metadata:
            test_flag: rest

        Bugzilla:
            1493785

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        requests = [{'service_template_href': tmplt.href} for tmplt in service_templates]
        body = {'service_requests': requests}
        href = appliance.rest_api.collections.service_orders._href
        response = appliance.rest_api.post(href, **body)
        response = response['results'].pop()

        @request.addfinalizer
        def delete_cart():
            cart = appliance.rest_api.get_entity('service_orders', response['id'])
            cart.action.delete()

        assert_response(appliance)
        cart_dict = appliance.rest_api.get('{}/cart'.format(href))
        assert response['id'] == cart_dict['id']

    @pytest.mark.tier(3)
    def test_add_to_cart(self, request, cart, service_templates_class):
        """Tests adding service requests to a cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        assert cart.service_requests.subcount == 0
        self.add_requests(cart, service_templates_class)
        request.addfinalizer(cart.action.clear)
        templates_ids = [tmplt.id for tmplt in service_templates_class]
        for service_request in cart.service_requests:
            assert service_request.source_id in templates_ids

    @pytest.mark.tier(3)
    def test_delete_requests(self, appliance, cart, service_templates_class):
        """Tests that deleting service requests removes them also from a cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        self.add_requests(cart, service_templates_class)
        cart_req_ids = {req.id for req in cart.service_requests}
        body = [{'id': req.id} for req in cart.service_requests]
        response = cart.collection._api.collections.service_requests.action.delete(*body)
        assert_response(appliance)
        assert len(response) == len(service_templates_class)
        cart.service_requests.reload()
        assert cart.service_requests.subcount == 0
        all_req_ids = {req.id for req in appliance.rest_api.collections.service_requests}
        # check that all service requests that were in the cart were deleted
        assert all_req_ids - cart_req_ids == all_req_ids

    @pytest.mark.tier(3)
    def test_remove_from_cart(self, appliance, cart, service_templates_class):
        """Tests removing service requests from a cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        self.add_requests(cart, service_templates_class)
        cart_req_ids = {req.id for req in cart.service_requests}
        body = [{'id': req.id} for req in cart.service_requests]
        response = cart.service_requests.action.remove(*body)
        assert_response(appliance)
        assert len(response) == len(service_templates_class)
        cart.service_requests.reload()
        assert cart.service_requests.subcount == 0
        all_req_ids = {req.id for req in appliance.rest_api.collections.service_requests}
        # check that all service requests that were in the cart were deleted
        assert all_req_ids - cart_req_ids == all_req_ids

    @pytest.mark.tier(3)
    def test_clear_cart(self, appliance, cart, service_templates_class):
        """Tests removing all service requests from a cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        self.add_requests(cart, service_templates_class)
        cart_req_ids = {req.id for req in cart.service_requests}
        cart.action.clear()
        assert_response(appliance)
        cart.service_requests.reload()
        assert cart.service_requests.subcount == 0
        all_req_ids = {req.id for req in appliance.rest_api.collections.service_requests}
        # check that all service requests that were in the cart were deleted
        assert all_req_ids - cart_req_ids == all_req_ids

    @pytest.mark.tier(3)
    def test_copy_cart(self, appliance, cart):
        """Tests that it's not possible to copy a cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        with pytest.raises(Exception, match='Cannot copy a service order in the cart state'):
            cart.action.copy(name='new_cart')
        assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    def test_order_cart(self, request, appliance, cart, service_templates_class):
        """Tests ordering service requests in a cart.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        selected_templates = service_templates_class[:2]
        self.add_requests(cart, selected_templates)
        cart.action.order()
        assert_response(appliance)
        cart.reload()
        assert cart.state == 'ordered'
        service_requests = list(cart.service_requests)

        def _order_finished():
            for sr in service_requests:
                sr.reload()
                if sr.status.lower() != 'ok' or sr.request_state.lower() != 'finished':
                    return False
            return True

        wait_for(_order_finished, num_sec=180, delay=10)

        for index, sr in enumerate(service_requests):
            service_name = get_dialog_service_name(
                appliance,
                sr,
                *[t.name for t in selected_templates]
            )
            assert '[{}]'.format(service_name) in sr.message
            service_description = selected_templates[index].description
            new_service = appliance.rest_api.collections.services.get(
                description=service_description)
            request.addfinalizer(new_service.action.delete)
            assert service_name == new_service.name

        # when cart is ordered, it can not longer be accessed using /api/service_orders/cart
        with pytest.raises(Exception, match='ActiveRecord::RecordNotFound'):
            appliance.rest_api.get('{}/cart'.format(cart.collection._href))

    @pytest.mark.tier(3)
    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_cart_from_detail(self, cart, method):
        """Tests deleting cart from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_detail([cart], method=method)

    @pytest.mark.tier(3)
    def test_delete_cart_from_collection(self, cart):
        """Tests deleting cart from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: nansari
            casecomponent: Rest
            initialEstimate: 1/4h
            tags: service
        """
        delete_resources_from_collection([cart])


@test_requirements.rest
@pytest.mark.tier(3)
def test_deny_service_ordering_via_api(
    appliance, deny_service_ordering, service_templates
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Services
        caseimportance: high
        initialEstimate: 1/10h
        setup:
            1. In advanced settings, update `:product:`-`:allow_api_service_ordering:` to `false`
            2. Create a dialog, catalog and catalog item.
        testSteps:
            1. Order the service via API.
        expectedResults:
            1. Service must not be ordered and response must return error.

    Bugzilla:
        1632416
    """
    # more than 1 service templates are created by the fixture, but we only need to access one
    template = service_templates[0]
    with pytest.raises(APIException):
        template.action.order()
    assert_response(appliance, http_status=400)


@pytest.fixture(scope="module")
def set_run_automate_method(appliance):
    reset_setting = appliance.advanced_settings["product"][
        "run_automate_methods_on_service_api_submit"
    ]
    appliance.update_advanced_settings(
        {"product": {"run_automate_methods_on_service_api_submit": True}}
    )
    yield
    appliance.update_advanced_settings(
        {"product": {"run_automate_methods_on_service_api_submit": reset_setting}}
    )


@pytest.fixture(scope="module")
def automate_env_setup(klass):
    # this script sets default value for the dialog element
    script = """
    dialog_field = $evm.object
    dialog_field["sort_by"] = "value"
    dialog_field["sort_order"] = "ascending"
    dialog_field["data_type"] = "integer"
    dialog_field["required"] = "true"
    dialog_field["default_value"] = 7
    dialog_field["values"] = {1 => "one", 2 => "two", 10 => "ten", 7 => "seven", 50 => "fifty"}
    """
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(start="meth_"),
        display_name=fauxfactory.gen_alphanumeric(start="meth_"),
        location="inline",
        script=script,
    )

    klass.schema.add_fields({"name": "meth", "type": "Method", "data_type": "Integer"})

    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(start="inst_"),
        display_name=fauxfactory.gen_alphanumeric(start="inst_"),
        description=fauxfactory.gen_alphanumeric(),
        fields={"meth": {"value": method.name}},
    )

    yield instance
    method.delete()
    instance.delete()


@pytest.fixture(scope="module")
def get_service_template(appliance, request, automate_env_setup):
    instance = automate_env_setup
    data = {
        "buttons": "submit, cancel",
        "label": fauxfactory.gen_alpha(12, start="dialog_"),
        "dialog_tabs": [
            {
                "display": "edit",
                "label": "Basic Information",
                "position": 0,
                "dialog_groups": [
                    {
                        "display": "edit",
                        "label": "New section",
                        "position": 0,
                        "dialog_fields": [
                            {
                                "name": "static",
                                "data_type": "integer",
                                "display": "edit",
                                "required": True,
                                "default_value": "2",
                                "values": [["1", "One"], ["2", "Two"], ["3", "Three"]],
                                "label": "Static Dropdown",
                                "position": 0,
                                "dynamic": False,
                                "read_only": True,
                                "type": "DialogFieldDropDownList",
                                "resource_action": {"resource_type": "DialogField"},
                            },
                            {
                                "name": "dynamic",
                                "data_type": "integer",
                                "display": "edit",
                                "required": True,
                                "default_value": "",
                                "label": "Dynamic Dropdown",
                                "position": 1,
                                "dynamic": True,
                                "read_only": True,
                                "type": "DialogFieldDropDownList",
                                "resource_action": {
                                    "resource_type": "DialogField",
                                    "ae_namespace": instance.namespace.name,
                                    "ae_class": instance.klass.name,
                                    "ae_instance": instance.name,
                                },
                            },
                        ],
                    }
                ],
            }
        ],
    }
    service_dialog = appliance.rest_api.collections.service_dialogs.action.create(
        **data
    )[0]
    service_catalog = _service_catalogs(request, appliance, num=1)[0]
    service_template = _service_templates(
        request,
        appliance,
        service_dialog=service_dialog,
        service_catalog=service_catalog,
    )[0]
    yield service_template
    service_template.action.delete()
    service_catalog.action.delete()
    service_dialog.action.delete()


@pytest.mark.tier(3)
@pytest.mark.parametrize("auth_type", ["token", "basic_auth"])
@test_requirements.rest
def test_populate_default_dialog_values(
    appliance, request, auth_type, set_run_automate_method, get_service_template
):
    """
    This test case checks if the default value set for static and dynamic elements are returned
    when ordering service via API with both basic and token based authentication.

    Polarion:
        assignee: pvala
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/10h
        setup:
            1. Update appliance advanced settings by setting
                `run_automate_methods_on_service_api_submit` to `true`.
            2. Create a new domain, namespace, klass, method, schema, and instance.
                (Method is attached in the Bugzilla 1639413).
                This method sets value 7 for dynamic element
            3. Create a Dialog with one static element(name="static") with some default value,
                and one dynamic element(name="dynamic") with the endpoint pointing to
                the newly created instance which returns a default value.
                (value_type="Integer", read_only=True, required=True)
            4. Create a catalog and create a generic catalog item assigned to it.
        testSteps:
            1. Order the catalog item with the given auth_type
                and check if the response contains default values that were initially set.
        expectedResults:
            1. Response must include default values that were initially set.

    Bugzilla:
        1635673
        1650252
        1639413
        1660237
    """
    if auth_type == "token":
        # obtaining authentication token
        auth_token = appliance.rest_api.get(appliance.url_path("/api/auth"))
        assert_response(appliance)
        # creating new API instance that uses the authentication token
        api = appliance.new_rest_api_instance(auth={"token": auth_token["auth_token"]})
        template = api.collections.service_templates.get(id=get_service_template.id)
    else:
        template = get_service_template

    response = template.action.order()
    assert_response(appliance)

    # every dialog element label changes to `dialog_label` in the response
    # default value for static element was set while creating the dialog
    assert response.options["dialog"]["dialog_static"] == 2
    # default value for dynamic element is returned by the automate method
    assert response.options["dialog"]["dialog_dynamic"] == 7


@pytest.fixture
def request_task(appliance, service_templates):
    service_request = service_templates[0].action.order()
    assert_response(appliance)

    wait_for(
        lambda: service_request.request_state == "finished",
        fail_func=service_request.reload,
        num_sec=200,
        delay=5,
    )
    service_template_name = service_templates[0].name
    return service_request.request_tasks.filter(
        Q(
            "description",
            "=",
            f"Provisioning [{service_template_name}] for Service [{service_template_name}]*",
        )
    ).resources[0]


def test_edit_service_request_task(appliance, request_task):
    """
        Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: Rest
        initialEstimate: 1/4h
        setup:
            1. Create a service request.
        testSteps:
            1. Edit the service request task:
                POST /api/service_requests/:id/request_tasks/:request_task_id
                {
                "action" : "edit",
                "resource" : {
                    "options" : {
                    "request_param_a" : "value_a",
                    "request_param_b" : "value_b"
                    }
                }
        expectedResults:
            1. Task must be edited successfully.

    """
    # edit the request_task by adding new elements
    request_task.action.edit(
        options={"request_param_a": "value_a", "request_param_b": "value_b"}
    )
    assert_response(appliance)

    # assert the presence of newly added elements
    request_task.reload()
    assert request_task.options["request_param_a"] == "value_a"
    assert request_task.options["request_param_b"] == "value_b"


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1716847])
@pytest.mark.customer_scenario
def test_embedded_ansible_cat_item_edit_rest(appliance, request, ansible_catalog_item):
    """
    Bugzilla:
        1716847
        1732117

    Polarion:
        assignee: pvala
        casecomponent: Rest
        initialEstimate: 1/4h
        setup:
            1. Create an Ansible Playbook Catalog Item
        testSteps:
            1. Edit the Catalog Item via REST and check if it is updated.
    """
    service_template = appliance.rest_api.collections.service_templates.get(
        name=ansible_catalog_item.name
    )
    new_data = {
        "name": fauxfactory.gen_alphanumeric(),
        "description": fauxfactory.gen_alphanumeric(),
    }
    service_template.action.edit(**new_data)
    assert_response(appliance)

    service_template.reload()
    assert service_template.name == new_data["name"]
    assert service_template.description == new_data["description"]


@pytest.mark.meta(automates=[1730813])
@test_requirements.rest
@pytest.mark.customer_scenario
@pytest.mark.parametrize("file_name", ["testgear-dialog.yaml"], ids=[''])
def test_service_refresh_dialog_fields_default_values(
    appliance, request, file_name, import_dialog, soft_assert
):
    """
    Bugzilla:
        1730813
        1731977

    Polarion:
        assignee: pvala
        caseimportance: high
        casecomponent: Rest
        initialEstimate: 1/4h
        setup:
            1. Import dialog `RTP Testgear Client Provision` from the BZ attachments and create
                a service_template and service catalog to attach it.
        testSteps:
            1. Perform action `refresh_dialog_fields` by sending a request
                POST /api/service_catalogs/<:id>/sevice_templates/<:id>
                    {
                    "action": "refresh_dialog_fields",
                    "resource": {
                        "fields": [
                            "tag_1_region",
                            "tag_0_function"
                            ]
                        }
                    }
        expectedResults:
            1. Request must be successful and evm must have the default values
                for the fields mentioned in testStep 1.
    """
    dialog, _ = import_dialog
    service_template = _service_templates(
        request, appliance, service_dialog=dialog.rest_api_entity, num=1
    )[0]

    # We cannot directly call `refresh_dialog_fields` action from service_template, it has to be
    # accessed via service_catalog.
    service_catalog = appliance.rest_api.collections.service_catalogs.get(
        id=service_template.service_template_catalog_id
    )
    service_catalog.service_templates.get(id=service_template.id).action.refresh_dialog_fields(
        **{"fields": ["tag_1_region", "tag_0_function"]}
    )
    assert_response(appliance)

    response = appliance.rest_api.response.json()["result"]
    expected_tag_1_region = [["rtp", "rtp-vaas-vc.cisco.com"]]
    expected_tag_0_function = [["ixia", "IXIA"]]

    soft_assert(
        expected_tag_1_region == response["tag_1_region"]["values"],
        "Default values for 'tag_1_region' did not match.",
    )
    soft_assert(
        expected_tag_0_function == response["tag_0_function"]["values"],
        "Default values for 'tag_0_function' did not match.",
    )
