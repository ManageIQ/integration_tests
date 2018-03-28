# -*- coding: utf-8 -*-
import pytest

import fauxfactory

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.common.vm import VM
from cfme.infrastructure.provider import CloudInfraProvider, InfraProvider
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.rest import assert_response, delete_resources_from_collection


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.provider([CloudInfraProvider], scope='module'),
    test_requirements.rest,
    pytest.mark.rhv3
]

COLLECTIONS = ['providers', 'vms']
COLLECTIONS_ADDED_IN_59 = ['instances', 'services']
COLLECTIONS.extend(COLLECTIONS_ADDED_IN_59)


@pytest.yield_fixture(scope='module')
def vm_obj(provider, setup_provider_modscope, small_template_modscope):
    """Creates new VM or instance"""
    vm_name = random_vm_name('attrs')
    new_vm = VM.factory(vm_name, provider, template_name=small_template_modscope.name)

    yield new_vm

    new_vm.cleanup_on_provider()


@pytest.fixture(scope='module')
def get_provider(appliance, provider, setup_provider_modscope):
    resource = appliance.rest_api.collections.providers.get(name=provider.name)
    return lambda: resource


@pytest.fixture(scope='module')
def get_vm(appliance, provider, vm_obj):
    if provider.one_of(InfraProvider):
        collection = appliance.rest_api.collections.vms
    else:
        collection = appliance.rest_api.collections.instances

    def _get_vm():
        vms = collection.find_by(name=vm_obj.name)
        if not vms:
            vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip='default')
            vms = collection.find_by(name=vm_obj.name)
        return vms[0]

    return _get_vm


@pytest.yield_fixture(scope='module')
def get_service(appliance):
    uid = fauxfactory.gen_alphanumeric(5)
    name = 'test_rest_service_{}'.format(uid)

    def _get_service():
        service = appliance.rest_api.collections.services.find_by(name=name)
        if not service:
            body = {
                'name': name,
                'description': 'Test REST Service {}'.format(uid),
            }
            service = appliance.rest_api.collections.services.action.create(body)
        return service[0]

    yield _get_service

    try:
        service = appliance.rest_api.collections.services.get(name=name)
        service.delete()
    except (AttributeError, ValueError):
        pass


@pytest.fixture(scope='module')
def get_resource(get_provider, get_vm, get_service):
    db = {
        'providers': get_provider,
        'instances': get_vm,
        'vms': get_vm,
        'services': get_service,
    }
    return db


def add_custom_attributes(request, resource):
    body = []
    attrs_num = 2
    for __ in range(attrs_num):
        uid = fauxfactory.gen_alphanumeric(5)
        body.append({
            'name': 'ca_name_{}'.format(uid),
            'value': 'ca_value_{}'.format(uid)
        })
    attrs = resource.custom_attributes.action.add(*body)

    @request.addfinalizer
    def _delete():
        resource.custom_attributes.reload()
        ids = [attr.id for attr in attrs]
        delete_attrs = [attr for attr in resource.custom_attributes if attr.id in ids]
        if delete_attrs:
            resource.custom_attributes.action.delete(*delete_attrs)

    assert_response(resource.collection._api)
    assert len(attrs) == attrs_num
    return attrs


def _uncollectif(appliance, provider, collection_name):
    return (
        (appliance.version < '5.9' and collection_name in COLLECTIONS_ADDED_IN_59) or
        (provider.one_of(InfraProvider) and collection_name == 'instances') or
        (provider.one_of(CloudProvider) and collection_name == 'vms')
    )


class TestCustomAttributesRESTAPI(object):
    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.rhv2
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    def test_add(self, request, collection_name, get_resource):
        """Test adding custom attributes to resource using REST API.

        Metadata:
            test_flag: rest
        """
        resource = get_resource[collection_name]()
        attributes = add_custom_attributes(request, resource)
        for attr in attributes:
            record = resource.custom_attributes.get(id=attr.id)
            assert record.name == attr.name
            assert record.value == attr.value

    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    def test_delete_from_detail_post(self, request, collection_name, appliance, get_resource):
        """Test deleting custom attributes from detail using POST method.

        Metadata:
            test_flag: rest
        """
        attributes = add_custom_attributes(request, get_resource[collection_name]())
        for entity in attributes:
            entity.action.delete.POST()
            assert_response(appliance)
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete.POST()
            assert_response(appliance, http_status=404)

    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        appliance.version < '5.9' or  # BZ 1422596 was not fixed for versions < 5.9
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    def test_delete_from_detail_delete(self, request, collection_name, appliance, get_resource):
        """Test deleting custom attributes from detail using DELETE method.

        Metadata:
            test_flag: rest
        """
        attributes = add_custom_attributes(request, get_resource[collection_name]())
        for entity in attributes:
            entity.action.delete.DELETE()
            assert_response(appliance)
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete.DELETE()
            assert_response(appliance, http_status=404)

    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    def test_delete_from_collection(self, request, collection_name, get_resource):
        """Test deleting custom attributes from collection using REST API.

        Metadata:
            test_flag: rest
        """
        resource = get_resource[collection_name]()
        attributes = add_custom_attributes(request, resource)
        collection = resource.custom_attributes
        delete_resources_from_collection(collection, attributes, not_found=True)

    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    def test_delete_single_from_collection(self, request, collection_name, get_resource):
        """Test deleting single custom attribute from collection using REST API.

        Metadata:
            test_flag: rest
        """
        resource = get_resource[collection_name]()
        attributes = add_custom_attributes(request, resource)
        attribute = attributes[0]
        collection = resource.custom_attributes
        delete_resources_from_collection(collection, [attribute], not_found=True)

    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_edit(self, request, from_detail, collection_name, appliance, get_resource):
        """Test editing custom attributes using REST API.

        Metadata:
            test_flag: rest
        """
        resource = get_resource[collection_name]()
        attributes = add_custom_attributes(request, resource)
        response_len = len(attributes)
        body = []
        for __ in range(response_len):
            uid = fauxfactory.gen_alphanumeric(5)
            body.append({
                'name': 'ca_name_{}'.format(uid),
                'value': 'ca_value_{}'.format(uid),
                'section': 'metadata'
            })
        if from_detail:
            edited = []
            for i in range(response_len):
                edited.append(attributes[i].action.edit(**body[i]))
                assert_response(appliance)
        else:
            for i in range(response_len):
                body[i].update(attributes[i]._ref_repr())
            edited = resource.custom_attributes.action.edit(*body)
            assert_response(appliance)
        assert len(edited) == response_len
        for i in range(response_len):
            attributes[i].reload()
            assert edited[i].name == body[i]['name'] == attributes[i].name
            assert edited[i].value == body[i]['value'] == attributes[i].value
            assert edited[i].section == body[i]['section'] == attributes[i].section

    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        # BZ 1516762 was not fixed for versions < 5.9
        (appliance.version < '5.9' and collection_name != 'providers') or
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    @pytest.mark.meta(blockers=[
        BZ(
            1516762,
            forced_streams=['5.9', 'upstream'],
            unblock=lambda collection_name: collection_name not in ('vms', 'instances')
        )])
    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_bad_section_edit(self, request, from_detail, collection_name, appliance, get_resource):
        """Test that editing custom attributes using REST API and adding invalid section fails.

        Metadata:
            test_flag: rest
        """
        resource = get_resource[collection_name]()
        attributes = add_custom_attributes(request, resource)
        response_len = len(attributes)
        body = []
        for __ in range(response_len):
            body.append({'section': 'bad_section'})
        if from_detail:
            for i in range(response_len):
                with error.expected('Api::BadRequestError'):
                    attributes[i].action.edit(**body[i])
                assert_response(appliance, http_status=400)
        else:
            for i in range(response_len):
                body[i].update(attributes[i]._ref_repr())
            with error.expected('Api::BadRequestError'):
                resource.custom_attributes.action.edit(*body)
            assert_response(appliance, http_status=400)

    @pytest.mark.uncollectif(lambda appliance, provider, collection_name:
        # BZ 1516762 was not fixed for versions < 5.9
        (appliance.version < '5.9' and collection_name != 'providers') or
        _uncollectif(appliance, provider, collection_name)
    )
    @pytest.mark.parametrize("collection_name", COLLECTIONS)
    @pytest.mark.meta(blockers=[
        BZ(
            1516762,
            forced_streams=['5.9', 'upstream'],
            unblock=lambda collection_name: collection_name not in ('vms', 'instances')
        )])
    def test_bad_section_add(self, request, collection_name, appliance, get_resource):
        """Test adding custom attributes with invalid section to resource using REST API.

        Metadata:
            test_flag: rest
        """
        resource = get_resource[collection_name]()
        add_custom_attributes(request, resource)
        uid = fauxfactory.gen_alphanumeric(5)
        body = {
            'name': 'ca_name_{}'.format(uid),
            'value': 'ca_value_{}'.format(uid),
            'section': 'bad_section'
        }
        with error.expected('Api::BadRequestError'):
            resource.custom_attributes.action.add(body)
        assert_response(appliance, http_status=400)
