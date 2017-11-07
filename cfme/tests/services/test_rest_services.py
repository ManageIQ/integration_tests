# -*- coding: utf-8 -*-
import datetime

import fauxfactory
import pytest

from manageiq_client.api import ManageIQClient as MiqApi

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.rest.gen_data import (
    TEMPLATE_TORSO,
    _creating_skeleton,
    blueprints as _blueprints,
    copy_role,
    dialog as _dialog,
    groups,
    orchestration_templates as _orchestration_templates,
    service_catalog_obj as _service_catalog_obj,
    service_catalogs as _service_catalogs,
    service_data as _service_data,
    service_templates as _service_templates,
    service_templates_ui,
    vm as _vm,
)
from cfme.services.catalogs.catalog_item import CatalogBundle
from fixtures.provider import setup_one_or_skip
from fixtures.pytest_store import store
from cfme.utils import error, version
from cfme.utils.blockers import BZ
from cfme.utils.providers import ProviderFilter
from cfme.utils.rest import assert_response
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.long_running,
    test_requirements.service,
    pytest.mark.tier(2)
]


NUM_BUNDLE_ITEMS = 4


@pytest.fixture(scope="module")
def a_provider(request):
    pf = ProviderFilter(classes=[InfraProvider], required_fields=[
        ['provisioning', 'template'],
        ['provisioning', 'host'],
        ['provisioning', 'datastore'],
        ['provisioning', 'vlan'],
        ['provisioning', 'catalog_item_type']])
    return setup_one_or_skip(request, filters=[pf])


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
        assert entity.retirement_state == 'retiring'


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
def service_catalogs(request, appliance):
    response = _service_catalogs(request, appliance.rest_api)
    assert_response(appliance)
    return response


@pytest.yield_fixture(scope='function')
def catalog_bundle(request, dialog, service_catalog_obj, appliance, a_provider):
    catalog_items = service_templates_ui(
        request,
        appliance,
        service_dialog=dialog,
        service_catalog=service_catalog_obj,
        a_provider=a_provider,
        num=NUM_BUNDLE_ITEMS)

    uid = fauxfactory.gen_alphanumeric()
    bundle_name = 'test_rest_bundle_{}'.format(uid)
    bundle = CatalogBundle(
        name=bundle_name,
        description='Test REST Bundle {}'.format(uid),
        display_in=True,
        catalog=service_catalog_obj,
        dialog=dialog,
        catalog_items=[item.name for item in catalog_items])
    bundle.create()

    catalog_rest = appliance.rest_api.collections.service_catalogs.get(
        name=service_catalog_obj.name)
    bundle_rest = catalog_rest.service_templates.get(name=bundle_name)

    yield bundle_rest

    if bundle.exists:
        bundle.delete()


@pytest.fixture(scope="function")
def service_catalog_obj(request, appliance):
    return _service_catalog_obj(request, appliance.rest_api)


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
def service_data(request, appliance, a_provider):
    return _service_data(request, appliance, a_provider)


@pytest.fixture(scope="function")
def vm(request, a_provider, appliance):
    return _vm(request, a_provider, appliance.rest_api)


@pytest.yield_fixture(scope="function")
def cart(appliance):
    cart = appliance.rest_api.collections.service_orders.action.create(name="cart")
    assert_response(appliance)
    cart = cart[0]

    yield cart

    if cart.exists:
        cart.action.delete()


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
    def test_edit_service(self, appliance, services):
        """Tests editing a service.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/services (method ``edit``) with the ``name``
            * Check if the service with ``new_name`` exists
        Metadata:
            test_flag: rest
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

    # POST method is not available on < 5.8, as described in BZ 1414852
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_delete_service_post(self, appliance, services):
        """Tests deleting services from detail using POST method.

        Metadata:
            test_flag: rest
        """
        for service in services:
            service.action.delete.POST()
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                service.action.delete.POST()
            assert_response(appliance, http_status=404)

    def test_delete_service_delete(self, appliance, services):
        """Tests deleting services from detail using DELETE method.

        Metadata:
            test_flag: rest
        """
        for service in services:
            service.action.delete.DELETE()
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                service.action.delete.DELETE()
            assert_response(appliance, http_status=404)

    def test_delete_services(self, appliance, services):
        """Tests deleting services from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.services.action.delete(*services)
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.services.action.delete(*services)
        assert_response(appliance, http_status=404)

    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_retire_service_now(self, appliance, service_data, from_detail):
        """Test retiring a service now.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        service = collection.get(name=service_data['service_name'])
        vm = appliance.rest_api.collections.vms.get(name=service_data['vm_name'])

        if from_detail:
            service.action.retire()
            assert_response(appliance)
        else:
            collection.action.retire(service)
            assert_response(appliance)

        wait_for_retired(service)
        wait_for_retired(vm)

    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_retire_service_future(self, appliance, services, from_detail):
        """Test retiring a service in future.

        Metadata:
            test_flag: rest
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

    def test_set_service_owner(self, appliance, services):
        """Tests set_ownership action on /api/services/:id.

        Metadata:
            test_flag: rest
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
    def test_power_service(self, appliance, service_data, from_detail):
        """Tests power operations on /api/services and /api/services/:id.

        * start, stop and suspend actions
        * transition from one power state to another

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        service = collection.get(name=service_data['service_name'])
        vm = appliance.rest_api.collections.vms.get(name=service_data['vm_name'])

        def _action_and_check(action, resulting_state):
            if from_detail:
                getattr(service.action, action)()
            else:
                getattr(collection.action, action)(service)
            assert_response(appliance)
            wait_for_vm_power_state(vm, resulting_state)

        wait_for_vm_power_state(vm, 'on')
        _action_and_check('stop', 'off')
        _action_and_check('start', 'on')
        _action_and_check('suspend', 'suspended')
        _action_and_check('start', 'on')

    def test_service_vm_subcollection(self, appliance, service_data):
        """Tests /api/services/:id/vms.

        Metadata:
            test_flag: rest
        """
        service = appliance.rest_api.collections.services.get(name=service_data['service_name'])
        vm = appliance.rest_api.collections.vms.get(name=service_data['vm_name'])
        assert service.vms[0].id == vm.id

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_service_add_resource(self, request, appliance, vm):
        """Tests adding resource to service.

        Metadata:
            test_flag: rest
        """
        service = services(request, appliance, num=1).pop()
        rest_vm = appliance.rest_api.collections.vms.get(name=vm)

        assert not service.vms
        service.action.add_resource(resource=rest_vm._ref_repr())
        assert_response(appliance)
        assert len(service.vms) == 1

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_service_remove_resource(self, request, appliance, service_data):
        """Tests removing resource from service.

        Metadata:
            test_flag: rest
        """
        service = appliance.rest_api.collections.services.get(name=service_data['service_name'])
        vm = appliance.rest_api.collections.vms.get(name=service_data['vm_name'])
        request.addfinalizer(vm.action.delete)

        vms_num = len(service.vms)
        assert vms_num >= 1
        service.action.remove_resource(resource=vm._ref_repr())
        assert_response(appliance)
        assert len(service.vms) == vms_num - 1

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_service_remove_all_resources(self, request, appliance, vm, service_data):
        """Tests removing all resources from service.

        Metadata:
            test_flag: rest
        """
        service = appliance.rest_api.collections.services.get(name=service_data['service_name'])
        vm_assigned = appliance.rest_api.collections.vms.get(name=service_data['vm_name'])
        vm_added = appliance.rest_api.collections.vms.get(name=vm)

        @request.addfinalizer
        def _delete_vms():
            vm_assigned.action.delete()
            vm_added.action.delete()

        service.action.add_resource(resource=vm_added._ref_repr())
        assert len(service.vms) >= 2
        service.action.remove_all_resources()
        assert_response(appliance)
        assert not service.vms

    def test_create_service_from_parent(self, request, appliance):
        """Tests creation of new service that reference existing service.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        service = collection.action.create(service_body())[0]
        request.addfinalizer(service.action.delete)
        bodies = []
        references = [{'id': service.id}]
        if version.current_version() >= '5.8':
            # referencing using href is not supported in versions < 5.8
            references.append({'href': service.href})
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
            with error.expected("ActiveRecord::RecordNotFound"):
                gen.action.delete()

    def test_add_service_parent(self, request, appliance):
        """Tests adding parent reference to already existing service.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        parent = collection.action.create(service_body())[0]
        request.addfinalizer(parent.action.delete)
        child = collection.action.create(service_body())[0]
        child.action.edit(parent_service=parent._ref_repr())
        assert_response(appliance)
        child.reload()
        assert child.ancestry == str(parent.id)

    @pytest.mark.uncollectif(lambda: store.current_appliance.version < '5.8')
    @pytest.mark.meta(blockers=[BZ(1496936)])
    def test_add_child_resource(self, request, appliance):
        """Tests adding parent reference to already existing service using add_resource.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        parent = collection.action.create(service_body())[0]
        request.addfinalizer(parent.action.delete)
        child = collection.action.create(service_body())[0]
        parent.action.add_resource(resource=child._ref_repr())
        assert_response(appliance)
        child.reload()
        assert child.ancestry == str(parent.id)

    @pytest.mark.skipif(
        store.current_appliance.version < '5.9',
        reason='BZ 1416903 was fixed only for versions >= 5.9')
    def test_power_parent_service(self, request, appliance, service_data):
        """Tests that power operations triggered on service parent affects child service.

        * start, stop and suspend actions
        * transition from one power state to another

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        service = collection.action.create(service_body())[0]
        request.addfinalizer(service.action.delete)
        child = collection.get(name=service_data['service_name'])
        vm = appliance.rest_api.collections.vms.get(name=service_data['vm_name'])
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

    @pytest.mark.uncollectif(lambda: store.current_appliance.version < '5.8')
    @pytest.mark.meta(blockers=[BZ(1496936)])
    def test_retire_parent_service_now(self, request, appliance):
        """Tests that child service is retired together with a parent service.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        parent = collection.action.create(service_body())[0]
        request.addfinalizer(parent.action.delete)
        child = collection.action.create(service_body())[0]
        parent.action.add_resource(resource=child._ref_repr())
        assert_response(appliance)

        parent.action.retire()
        assert_response(appliance)

        wait_for_retired(parent)
        wait_for_retired(child)


class TestServiceDialogsRESTAPI(object):
    @pytest.mark.parametrize("method", ["post", "delete"])
    def test_delete_service_dialog(self, appliance, dialog, method):
        """Tests deleting service dialogs from detail.

        Metadata:
            test_flag: rest
        """
        service_dialog = appliance.rest_api.collections.service_dialogs.get(label=dialog.label)

        if method == "delete":
            del_action = service_dialog.action.delete.DELETE
        else:
            del_action = service_dialog.action.delete.POST

        del_action()
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            del_action()
        assert_response(appliance, http_status=404)

    def test_delete_service_dialogs(self, appliance, dialog):
        """Tests deleting service dialogs from collection.

        Metadata:
            test_flag: rest
        """
        service_dialog = appliance.rest_api.collections.service_dialogs.get(label=dialog.label)
        appliance.rest_api.collections.service_dialogs.action.delete(service_dialog)
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.service_dialogs.action.delete(service_dialog)
        assert_response(appliance, http_status=404)


class TestServiceTemplateRESTAPI(object):
    def test_create_service_templates(self, appliance, service_templates):
        """Tests creation of service templates.

        Metadata:
            test_flag: rest
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
        """
        for service_template in service_templates:
            new_name = fauxfactory.gen_alphanumeric()
            response = service_template.action.edit(name=new_name)
            assert_response(appliance)
            assert response.name == new_name
            service_template.reload()
            assert service_template.name == new_name

    def test_delete_service_templates(self, appliance, service_templates):
        """Tests deleting service templates from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.service_templates.action.delete(*service_templates)
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.service_templates.action.delete(*service_templates)
        assert_response(appliance, http_status=404)

    # POST method is not available on < 5.8, as described in BZ 1427338
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_delete_service_template_post(self, appliance, service_templates):
        """Tests deleting service templates from detail using POST method.

        Metadata:
            test_flag: rest
        """
        for service_template in service_templates:
            service_template.action.delete.POST()
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                service_template.action.delete.POST()
            assert_response(appliance, http_status=404)

    def test_delete_service_template_delete(self, appliance, service_templates):
        """Tests deleting service templates from detail using DELETE method.

        Metadata:
            test_flag: rest
        """
        for service_template in service_templates:
            service_template.action.delete.DELETE()
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                service_template.action.delete.DELETE()
            assert_response(appliance, http_status=404)

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
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit_catalogs(self, appliance, service_catalogs, from_detail):
        """Tests editing catalog items using the REST API.

        Metadata:
            test_flag: rest
        """
        new_descriptions = []
        if from_detail:
            edited = []
            for catalog in service_catalogs:
                new_description = 'Test Catalog {}'.format(fauxfactory.gen_alphanumeric().lower())
                new_descriptions.append(new_description)
                edited.append(catalog.action.edit(description=new_description))
                assert_response(appliance)
        else:
            catalog_edited = []
            for catalog in service_catalogs:
                new_description = 'Test Catalog {}'.format(fauxfactory.gen_alphanumeric().lower())
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

        service_name = str(service_request.options['dialog']['dialog_service_name'])
        assert '[{}]'.format(service_name) in service_request.message
        # this fails if the service with the `service_name` doesn't exist
        new_service = appliance.rest_api.collections.services.get(name=service_name)

        @request.addfinalizer
        def _finished():
            new_service.action.delete()

    def test_order_multiple_catalog_items(
            self, request, appliance, service_catalogs, service_templates):
        """Tests ordering multiple catalog items using the REST API.

        Metadata:
            test_flag: rest
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

        # testing BZ 1480281 that was fixed only for versions >= 5.9
        if appliance.version >= '5.9':
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
            service_name = str(service_request.options['dialog']['dialog_service_name'])
            assert '[{}]'.format(service_name) in service_request.message

            # Service name can no longer be used to uniquely identify service when multiple
            # services are using the same dialog (all services have the same name).
            # Using service template id instead.
            source_id = str(service_request.source_id)
            new_service = appliance.rest_api.collections.services.get(service_template_id=source_id)
            new_services.append(new_service)

        @request.addfinalizer
        def _finished():
            appliance.rest_api.collections.services.action.delete(*new_services)

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_order_catalog_bundle(self, appliance, request, catalog_bundle):
        """Tests ordering catalog bundle using the REST API.

        Metadata:
            test_flag: rest
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

        service_name = str(service_request.options['dialog']['dialog_service_name'])
        assert '[{}]'.format(service_name) in service_request.message
        # this fails if the service with the `service_name` doesn't exist
        new_service = appliance.rest_api.collections.services.get(name=service_name)

        @request.addfinalizer
        def _finished():
            new_service.action.delete()

        vms = new_service.vms
        vms.reload()
        assert len(vms) == NUM_BUNDLE_ITEMS
        children = appliance.rest_api.collections.services.find_by(ancestry=str(new_service.id))
        assert len(children) == NUM_BUNDLE_ITEMS

    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_catalog_from_detail(self, appliance, service_catalogs, method):
        """Tests delete service catalogs from detail using REST API.

        Metadata:
            test_flag: rest
        """
        for catalog in service_catalogs:
            if method == 'post':
                del_action = catalog.action.delete.POST
            else:
                del_action = catalog.action.delete.DELETE

            del_action()
            assert_response(appliance)
            wait_for(
                lambda: not appliance.rest_api.collections.service_catalogs.find_by(
                    name=catalog.name),
                num_sec=100,
                delay=5
            )

            with error.expected('ActiveRecord::RecordNotFound'):
                del_action()
            assert_response(appliance, http_status=404)

    def test_delete_catalog_from_collection(self, appliance, service_catalogs):
        """Tests delete service catalogs from detail using REST API.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.service_catalogs.action.delete.POST(*service_catalogs)
        assert_response(appliance)

        for catalog in service_catalogs:
            wait_for(
                lambda: not appliance.rest_api.collections.service_catalogs.find_by(
                    name=catalog.name),
                num_sec=300,
                delay=5
            )

        with error.expected('ActiveRecord::RecordNotFound'):
            appliance.rest_api.collections.service_catalogs.action.delete.POST(*service_catalogs)
        assert_response(appliance, http_status=404)


@pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
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
        domain = dc.create(name=fauxfactory.gen_alphanumeric(), enabled=True)
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

    def test_create_pending_request(self, pending_request):
        """Tests creating pending service request using the REST API.

        Metadata:
            test_flag: rest
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
    def test_delete_pending_request_from_detail(self, appliance, pending_request, method):
        """Tests deleting pending service request from detail using the REST API.

        Metadata:
            test_flag: rest
        """
        if method == 'delete':
            del_action = pending_request.action.delete.DELETE
        else:
            del_action = pending_request.action.delete.POST

        del_action()
        assert_response(appliance)
        with error.expected('ActiveRecord::RecordNotFound'):
            del_action()
        assert_response(appliance, http_status=404)

    def test_delete_pending_request_from_collection(self, appliance, pending_request):
        """Tests deleting pending service request from detail using the REST API.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.service_requests
        collection.action.delete(pending_request)
        assert_response(appliance)
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(pending_request)
        assert_response(appliance, http_status=404)

    def test_order_manual_approval(self, request, appliance, pending_request):
        """Tests ordering single catalog item with manual approval using the REST API.

        Metadata:
            test_flag: rest
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

        service_name = str(pending_request.options['dialog']['dialog_service_name'])
        assert '[{}]'.format(service_name) in pending_request.message
        # this fails if the service with the `service_name` doesn't exist
        new_service = appliance.rest_api.collections.services.get(name=service_name)

        request.addfinalizer(new_service.action.delete)

    def test_order_manual_denial(self, appliance, pending_request):
        """Tests ordering single catalog item with manual denial using the REST API.

        Metadata:
            test_flag: rest
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
    @pytest.yield_fixture(scope='class')
    def new_role(self, appliance):
        role = copy_role(appliance.rest_api, 'EvmRole-user_self_service')
        # allow role to access all Services, VMs, and Templates
        role.action.edit(settings=None)
        yield role
        role.action.delete()

    @pytest.fixture(scope='class')
    def new_group(self, request, appliance, new_role):
        tenant = appliance.rest_api.collections.tenants.get(name='My Company')
        return groups(request, appliance.rest_api, new_role, tenant, num=1)

    @pytest.fixture(scope='class')
    def user_auth(self, request, appliance, new_group):
        password = fauxfactory.gen_alphanumeric()
        data = [{
            "userid": "rest_{}".format(fauxfactory.gen_alphanumeric(3).lower()),
            "name": "REST User {}".format(fauxfactory.gen_alphanumeric()),
            "password": password,
            "group": {"id": new_group.id}
        }]

        user = _creating_skeleton(request, appliance.rest_api, 'users', data)
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

        service_name = str(service_request.options['dialog']['dialog_service_name'])
        assert '[{}]'.format(service_name) in service_request.message
        # this fails if the service with the `service_name` doesn't exist
        new_service = appliance.rest_api.collections.services.get(name=service_name)
        request.addfinalizer(new_service.action.delete)


class TestBlueprintsRESTAPI(object):
    @pytest.fixture(scope="function")
    def blueprints(self, request, appliance):
        num = 2
        response = _blueprints(request, appliance.rest_api, num=num)
        assert_response(appliance)
        assert len(response) == num
        return response

    @pytest.mark.tier(3)
    def test_create_blueprints(self, appliance, blueprints):
        """Tests creation of blueprints.

        Metadata:
            test_flag: rest
        """
        for blueprint in blueprints:
            record = appliance.rest_api.collections.blueprints.get(id=blueprint.id)
            assert record.name == blueprint.name
            assert record.description == blueprint.description
            assert record.ui_properties == blueprint.ui_properties

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_blueprints_from_detail(self, appliance, blueprints, method):
        """Tests deleting blueprints from detail.

        Metadata:
            test_flag: rest
        """
        for blueprint in blueprints:
            if method == "delete":
                del_action = blueprint.action.delete.DELETE
            else:
                del_action = blueprint.action.delete.POST

            del_action()
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                del_action()
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_delete_blueprints_from_collection(self, appliance, blueprints):
        """Tests deleting blueprints from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.blueprints
        collection.action.delete(*blueprints)
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            collection.action.delete(*blueprints)
        assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_edit_blueprints(self, appliance, blueprints, from_detail):
        """Tests editing of blueprints.

        Metadata:
            test_flag: rest
        """
        response_len = len(blueprints)
        new = [{
            'ui_properties': {
                'automate_entrypoints': {'Reconfigure': 'foo'}
            }
        } for _ in range(response_len)]
        if from_detail:
            edited = []
            for i in range(response_len):
                edited.append(blueprints[i].action.edit(**new[i]))
                assert_response(appliance)
        else:
            for i in range(response_len):
                new[i].update(blueprints[i]._ref_repr())
            edited = appliance.rest_api.collections.blueprints.action.edit(*new)
            assert_response(appliance)
        assert len(edited) == response_len
        for i in range(response_len):
            assert edited[i].ui_properties == new[i]['ui_properties']
            blueprints[i].reload()
            assert blueprints[i].ui_properties == new[i]['ui_properties']


class TestOrchestrationTemplatesRESTAPI(object):
    @pytest.fixture(scope='function')
    def orchestration_templates(self, request, appliance):
        num = 2
        response = _orchestration_templates(request, appliance.rest_api, num=num)
        assert_response(appliance)
        assert len(response) == num
        return response

    @pytest.mark.tier(3)
    def test_create_orchestration_templates(self, appliance, orchestration_templates):
        """Tests creation of orchestration templates.

        Metadata:
            test_flag: rest
        """
        for template in orchestration_templates:
            record = appliance.rest_api.collections.orchestration_templates.get(id=template.id)
            assert record.name == template.name
            assert record.description == template.description
            assert record.type == template.type

    @pytest.mark.tier(3)
    def test_delete_orchestration_templates_from_collection(
            self, appliance, orchestration_templates):
        """Tests deleting orchestration templates from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.orchestration_templates
        collection.action.delete(*orchestration_templates)
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            collection.action.delete(*orchestration_templates)
        assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    @pytest.mark.meta(blockers=[BZ(1414881, forced_streams=['5.7', '5.8', 'upstream'])])
    def test_delete_orchestration_templates_from_detail_post(self, orchestration_templates,
            appliance):
        """Tests deleting orchestration templates from detail using POST method.

        Metadata:
            test_flag: rest
        """
        for ent in orchestration_templates:
            ent.action.delete.POST()
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                ent.action.delete.POST()
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_delete_orchestration_templates_from_detail_delete(self, orchestration_templates,
            appliance):
        """Tests deleting orchestration templates from detail using DELETE method.

        Metadata:
            test_flag: rest
        """
        for ent in orchestration_templates:
            ent.action.delete.DELETE()
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                ent.action.delete.DELETE()
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_edit_orchestration_templates(self, appliance, orchestration_templates, from_detail):
        """Tests editing of orchestration templates.

        Metadata:
            test_flag: rest
        """
        response_len = len(orchestration_templates)
        new = [{
            'description': 'Updated Test Template {}'.format(fauxfactory.gen_alphanumeric(5))
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
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_copy_orchestration_templates(self, request, appliance, orchestration_templates,
            from_detail):
        """Tests copying of orchestration templates.

        Metadata:
            test_flag: rest
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
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_invalid_copy_orchestration_templates(self, appliance, orchestration_templates,
            from_detail):
        """Tests copying of orchestration templates without changing content.

        Metadata:
            test_flag: rest
        """
        num_orch_templates = len(orchestration_templates)
        new = []
        for _ in range(num_orch_templates):
            new.append({
                "name": "test_copied_{}".format(fauxfactory.gen_alphanumeric(5))
            })
        if from_detail:
            for i in range(num_orch_templates):
                with error.expected("content must be unique"):
                    orchestration_templates[i].action.copy(**new[i])
                assert_response(appliance, http_status=400)
        else:
            for i in range(num_orch_templates):
                new[i].update(orchestration_templates[i]._ref_repr())
            with error.expected("content must be unique"):
                appliance.rest_api.collections.orchestration_templates.action.copy(*new)
            assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: store.current_appliance.version < '5.9')
    @pytest.mark.meta(blockers=[BZ(1510215, forced_streams=['5.9', 'upstream'])])
    def test_invalid_template_type(self, appliance):
        """Tests that template creation fails gracefully when invalid type is specified.

        Metadata:
            test_flag: rest
        """
        uniq = fauxfactory.gen_alphanumeric(5)
        payload = {
            'name': 'test_{}'.format(uniq),
            'description': 'Test Template {}'.format(uniq),
            'type': 'OrchestrationTemplateCfn',
            'orderable': False,
            'draft': False,
            'content': TEMPLATE_TORSO.replace('CloudFormation', uniq)
        }
        with error.expected('Api::BadRequestError'):
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

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_create_empty_cart(self, appliance, cart):
        """Tests creating an empty cart.

        Metadata:
            test_flag: rest
        """
        assert cart.state == 'cart'
        cart_dict = appliance.rest_api.get('{}/cart'.format(cart.collection._href))
        assert cart_dict['id'] == cart.id

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_create_second_cart(self, request, appliance, cart):
        """Tests that it's not possible to create second cart.

        Metadata:
            test_flag: rest
        """
        # This will fail somehow once BZ 1493788 is fixed.
        # There can be one and only one shopping cart for the authenticated user.
        second_cart = appliance.rest_api.collections.service_orders.action.create(name="cart2")
        second_cart = second_cart[0]
        request.addfinalizer(second_cart.action.delete)
        assert second_cart.state == 'cart'

    @pytest.mark.tier(3)
    # not testing on version < 5.9 due to BZ1493785 that was fixed only in 5.9
    @pytest.mark.uncollectif(lambda: store.current_appliance.version < '5.9')
    def test_create_cart(self, appliance, service_templates):
        """Tests creating a cart with service requests.

        Metadata:
            test_flag: rest
        """
        requests = [{'service_template_href': tmplt.href} for tmplt in service_templates]
        body = {'service_requests': requests}
        href = appliance.rest_api.collections.service_orders._href
        response = appliance.rest_api.post(href, **body)
        assert_response(appliance)
        response = response['results'].pop()
        cart_dict = appliance.rest_api.get('{}/cart'.format(href))
        assert response['id'] == cart_dict['id']

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_add_to_cart(self, request, cart, service_templates_class):
        """Tests adding service requests to a cart.

        Metadata:
            test_flag: rest
        """
        assert cart.service_requests.subcount == 0
        self.add_requests(cart, service_templates_class)
        request.addfinalizer(cart.action.clear)
        templates_ids = [tmplt.id for tmplt in service_templates_class]
        for service_request in cart.service_requests:
            assert service_request.source_id in templates_ids

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_delete_requests(self, appliance, cart, service_templates_class):
        """Tests that deleting service requests removes them also from a cart.

        Metadata:
            test_flag: rest
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
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_remove_from_cart(self, appliance, cart, service_templates_class):
        """Tests removing service requests from a cart.

        Metadata:
            test_flag: rest
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
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_clear_cart(self, appliance, cart, service_templates_class):
        """Tests removing all service requests from a cart.

        Metadata:
            test_flag: rest
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
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_copy_cart(self, appliance, cart):
        """Tests that it's not possible to copy a cart.

        Metadata:
            test_flag: rest
        """
        with error.expected('Cannot copy a service order in the cart state'):
            cart.action.copy(name='new_cart')
        assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_order_cart(self, request, appliance, cart, service_templates_class):
        """Tests ordering service requests in a cart.

        Metadata:
            test_flag: rest
        """
        self.add_requests(cart, service_templates_class[:2])
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

        for sr in service_requests:
            service_name = str(sr.options['dialog']['dialog_service_name'])
            assert '[{}]'.format(service_name) in sr.message
            # this fails if the service with the `service_name` doesn't exist
            new_service = appliance.rest_api.collections.services.get(name=service_name)
            request.addfinalizer(new_service.action.delete)

        # when cart is ordered, it can not longer be accessed using /api/service_orders/cart
        with error.expected('ActiveRecord::RecordNotFound'):
            appliance.rest_api.get('{}/cart'.format(cart.collection._href))

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_cart_from_detail(self, appliance, cart, method):
        """Tests deleting cart from detail.

        Metadata:
            test_flag: rest
        """
        if method == 'delete':
            del_action = cart.action.delete.DELETE
        else:
            del_action = cart.action.delete.POST

        del_action()
        assert_response(appliance)
        with error.expected('ActiveRecord::RecordNotFound'):
            del_action()
        assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.8')
    def test_delete_cart_from_collection(self, appliance, cart):
        """Tests deleting cart from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.service_orders
        collection.action.delete(cart)
        assert_response(appliance)
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(cart)
        assert_response(appliance, http_status=404)
