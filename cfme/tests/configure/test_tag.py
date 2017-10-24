# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration.region_settings import Category, Tag
from cfme.rest.gen_data import (
    a_provider as _a_provider,
    categories as _categories,
    service_templates as _service_templates,
    tags as _tags,
    tenants as _tenants,
    vm as _vm,
)
from cfme.utils.update import update
from cfme.utils.wait import wait_for
from cfme.utils.rest import assert_response
from cfme.utils.version import current_version
from cfme.utils.blockers import BZ
from cfme.utils import error


@pytest.yield_fixture
def category():
    cg = Category(name=fauxfactory.gen_alphanumeric(8).lower(),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    yield cg
    cg.delete()


@pytest.mark.tier(2)
def test_tag_crud(category):
    tag = Tag(name=fauxfactory.gen_alphanumeric(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(32),
              category=category)
    tag.create()
    with update(tag):
        tag.display_name = fauxfactory.gen_alphanumeric(32)
    tag.delete(cancel=False)


class TestTagsViaREST(object):

    COLLECTIONS_BULK_TAGS = ("services", "vms")

    def _service_body(self, **kwargs):
        uid = fauxfactory.gen_alphanumeric(5)
        body = {
            'name': 'test_rest_service_{}'.format(uid),
            'description': 'Test REST Service {}'.format(uid),
        }
        body.update(kwargs)
        return body

    def _create_services(self, request, rest_api, num=3):
        # create simple service using REST API
        bodies = [self._service_body() for __ in range(num)]
        collection = rest_api.collections.services
        new_services = collection.action.create(*bodies)
        assert_response(rest_api)
        new_services_backup = list(new_services)

        @request.addfinalizer
        def _finished():
            collection.reload()
            ids = [service.id for service in new_services_backup]
            delete_entities = [service for service in collection if service.id in ids]
            if delete_entities:
                collection.action.delete(*delete_entities)

        return new_services

    @pytest.fixture(scope="function")
    def services(self, request, appliance):
        return self._create_services(request, appliance.rest_api)

    @pytest.fixture(scope="function")
    def categories(self, request, appliance, num=3):
        return _categories(request, appliance.rest_api, num)

    @pytest.fixture(scope="function")
    def tags(self, request, appliance, categories):
        return _tags(request, appliance.rest_api, categories)

    @pytest.fixture(scope="module")
    def services_mod(self, request, appliance):
        return self._create_services(request, appliance.rest_api)

    @pytest.fixture(scope="module")
    def categories_mod(self, request, appliance, num=3):
        return _categories(request, appliance.rest_api, num)

    @pytest.fixture(scope="module")
    def tags_mod(self, request, appliance, categories_mod):
        return _tags(request, appliance.rest_api, categories_mod)

    @pytest.fixture(scope="module")
    def tenants(self, request, appliance):
        return _tenants(request, appliance.rest_api, num=1)

    @pytest.fixture(scope="module")
    def a_provider(self, request):
        return _a_provider(request)

    @pytest.fixture(scope="module")
    def service_templates(self, request, appliance):
        return _service_templates(request, appliance)

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, appliance):
        return _vm(request, a_provider, appliance.rest_api)

    @pytest.mark.tier(2)
    def test_edit_tags(self, appliance, tags):
        """Tests tags editing from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.tags
        tags_len = len(tags)
        tags_data_edited = []
        for tag in tags:
            tags_data_edited.append({
                "href": tag.href,
                "name": "test_tag_{}".format(fauxfactory.gen_alphanumeric().lower()),
            })
        edited = collection.action.edit(*tags_data_edited)
        assert_response(appliance, results_num=tags_len)
        for index in range(tags_len):
            record, _ = wait_for(lambda:
                collection.find_by(name="%/{}".format(tags_data_edited[index]["name"])) or False,
                num_sec=180,
                delay=10)
            assert record[0].id == edited[index].id
            assert record[0].name == edited[index].name

    @pytest.mark.tier(2)
    def test_edit_tag(self, appliance, tags):
        """Tests tag editing from detail.

        Metadata:
            test_flag: rest
        """
        edited = []
        new_names = []
        for tag in tags:
            new_name = 'test_tag_{}'.format(fauxfactory.gen_alphanumeric())
            new_names.append(new_name)
            edited.append(tag.action.edit(name=new_name))
            assert_response(appliance)
        for index, name in enumerate(new_names):
            record, _ = wait_for(lambda:
                appliance.rest_api.collections.tags.find_by(name="%/{}".format(name)) or False,
                num_sec=180,
                delay=10)
            assert record[0].id == edited[index].id
            assert record[0].name == edited[index].name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_tags_from_detail(self, appliance, tags, method):
        """Tests deleting tags from detail.

        Metadata:
            test_flag: rest
        """
        for tag in tags:
            tag.action.delete(force_method=method)
            assert_response(appliance)
            with error.expected("ActiveRecord::RecordNotFound"):
                tag.action.delete(force_method=method)
            assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_delete_tags_from_collection(self, appliance, tags):
        """Tests deleting tags from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.tags.action.delete(*tags)
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.tags.action.delete(*tags)
        assert_response(appliance, http_status=404)

    @pytest.mark.tier(3)
    def test_create_tag_with_wrong_arguments(self, appliance):
        """Tests creating tags with missing category "id", "href" or "name".

        Metadata:
            test_flag: rest
        """
        data = {
            "name": "test_tag_{}".format(fauxfactory.gen_alphanumeric().lower()),
            "description": "test_tag_{}".format(fauxfactory.gen_alphanumeric().lower())
        }
        with error.expected("BadRequestError: Category id, href or name needs to be specified"):
            appliance.rest_api.collections.tags.action.create(data)
        assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    @pytest.mark.meta(blockers=[BZ(1451025, forced_streams=['5.7'])])
    @pytest.mark.parametrize(
        "collection_name", ["clusters", "hosts", "data_stores", "providers", "resource_pools",
        "services", "service_templates", "tenants", "vms"])
    def test_assign_and_unassign_tag(self, appliance, tags_mod, a_provider, services_mod,
            service_templates, tenants, vm, collection_name):
        """Tests assigning and unassigning tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        if not collection.all:
            pytest.skip("No available entity in {} to assign tag".format(collection_name))
        entity = collection[-1]
        tag = tags_mod[0]
        entity.tags.action.assign(tag)
        assert_response(appliance)
        entity.reload()
        assert tag.id in [t.id for t in entity.tags.all]
        entity.tags.action.unassign(tag)
        assert_response(appliance)
        entity.reload()
        assert tag.id not in [t.id for t in entity.tags.all]

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_tag(self, appliance, tags_mod, services_mod, vm,
            collection_name):
        """Tests bulk assigning and unassigning tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        entities = collection.all[-2:]

        new_tags = []
        for index, tag in enumerate(tags_mod):
            identifiers = [{'href': tag._href}, {'id': tag.id}]
            new_tags.append(identifiers[index % 2])

        # add some more tags in supported formats
        new_tags.append({'category': 'department', 'name': 'finance'})
        new_tags.append({'name': '/managed/department/presales'})
        tags_ids = {t.id for t in tags_mod}
        tags_ids.add(
            appliance.rest_api.collections.tags.get(name='/managed/department/finance').id)
        tags_ids.add(
            appliance.rest_api.collections.tags.get(name='/managed/department/presales').id)
        tags_count = len(new_tags) * len(entities)

        response = collection.action.assign_tags(*entities, tags=new_tags)
        assert_response(appliance, results_num=tags_count)

        # testing BZ 1460257
        results = appliance.rest_api.response.json()['results']
        entities_hrefs = [e.href for e in entities]
        for result in results:
            assert result['href'] in entities_hrefs

        for index, entity in enumerate(entities):
            entity.tags.reload()
            response[index].id = entity.id
            assert tags_ids.issubset({t.id for t in entity.tags.all})

        collection.action.unassign_tags(*entities, tags=new_tags)
        assert_response(appliance, results_num=tags_count)
        for entity in entities:
            entity.tags.reload()
            assert len({t.id for t in entity.tags.all} - tags_ids) == entity.tags.subcount

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_invalid_tag(self, appliance, services_mod, vm,
            collection_name):
        """Tests bulk assigning and unassigning invalid tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        entities = collection.all[-2:]

        new_tags = ['invalid_tag1', 'invalid_tag2']
        tags_count = len(new_tags) * len(entities)
        tags_per_entities_count = []
        for entity in entities:
            entity.tags.reload()
            tags_per_entities_count.append(entity.tags.subcount)

        def _check_tags_counts():
            for index, entity in enumerate(entities):
                entity.tags.reload()
                assert entity.tags.subcount == tags_per_entities_count[index]

        collection.action.assign_tags(*entities, tags=new_tags)
        assert_response(appliance, success=False, results_num=tags_count)
        _check_tags_counts()

        collection.action.unassign_tags(*entities, tags=new_tags)
        assert_response(appliance, success=False, results_num=tags_count)
        _check_tags_counts()

    @pytest.mark.uncollectif(lambda: current_version() < '5.9')
    @pytest.mark.tier(3)
    def test_query_by_multiple_tags(self, appliance, tags, services):
        """Tests support for multiple tag specification in query.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.services
        collection.reload()
        new_tags = [tag._ref_repr() for tag in tags]
        tagged_services = services[1:]

        # assign tags to selected services
        collection.action.assign_tags(*tagged_services, tags=new_tags)
        assert_response(appliance)

        # get only services that has all the tags assigned
        by_tag = ','.join([tag.name.replace('/managed', '') for tag in tags])
        query_results = collection.query_string(by_tag=by_tag)

        assert len(tagged_services) == len(query_results)
        result_ids = {item.id for item in query_results}
        tagged_ids = {item.id for item in tagged_services}
        assert result_ids == tagged_ids
