# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration import Category, Tag
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import categories as _categories
from cfme.rest.gen_data import services as _services
from cfme.rest.gen_data import service_templates as _service_templates
from cfme.rest.gen_data import tenants as _tenants
from cfme.rest.gen_data import tags as _tags
from cfme.rest.gen_data import vm as _vm
from utils.update import update
from utils.wait import wait_for
from utils.version import current_version
from utils.blockers import BZ
from utils import error


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

    @pytest.fixture(scope="function")
    def categories(self, request, appliance, num=3):
        return _categories(request, appliance.rest_api, num)

    @pytest.fixture(scope="function")
    def tags(self, request, appliance, categories):
        return _tags(request, appliance.rest_api, categories)

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
    def services(self, request, appliance, a_provider):
        try:
            return _services(request, appliance.rest_api, a_provider)
        except Exception:
            pass

    def service_body(self, **kwargs):
        uid = fauxfactory.gen_alphanumeric(5)
        body = {
            'name': 'test_rest_service_{}'.format(uid),
            'description': 'Test REST Service {}'.format(uid),
        }
        body.update(kwargs)
        return body

    @pytest.fixture(scope="module")
    def dummy_services(self, request, appliance):
        # create simple service using REST API
        bodies = [self.service_body() for _ in range(3)]
        collection = appliance.rest_api.collections.services
        new_services = collection.action.create(*bodies)
        assert appliance.rest_api.response.status_code == 200

        @request.addfinalizer
        def _finished():
            collection.reload()
            ids = [service.id for service in new_services]
            delete_entities = [service for service in collection if service.id in ids]
            if delete_entities:
                collection.action.delete(*delete_entities)

        return new_services

    @pytest.fixture(scope="module")
    def service_templates(self, request, appliance):
        return _service_templates(request, appliance.rest_api)

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
        assert appliance.rest_api.response.status_code == 200
        assert len(edited) == tags_len
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
            assert appliance.rest_api.response.status_code == 200
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
        status = 204 if method == "delete" else 200
        for tag in tags:
            tag.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                tag.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_tags_from_collection(self, appliance, tags):
        """Tests deleting tags from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.tags.action.delete(*tags)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.tags.action.delete(*tags)
        assert appliance.rest_api.response.status_code == 404

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
        assert appliance.rest_api.response.status_code == 400

    @pytest.mark.tier(3)
    @pytest.mark.meta(blockers=[BZ(1451025)])
    @pytest.mark.parametrize(
        "collection_name", ["clusters", "hosts", "data_stores", "providers", "resource_pools",
        "services", "service_templates", "tenants", "vms"])
    def test_assign_and_unassign_tag(self, appliance, tags_mod, a_provider, services,
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
        assert appliance.rest_api.response.status_code == 200
        entity.reload()
        assert tag.id in [t.id for t in entity.tags.all]
        entity.tags.action.unassign(tag)
        assert appliance.rest_api.response.status_code == 200
        entity.reload()
        assert tag.id not in [t.id for t in entity.tags.all]

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_tag(self, appliance, tags_mod, dummy_services, vm,
            collection_name):
        """Tests bulk assigning and unassigning tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        if len(collection) > 1:
            entities = [collection[-2], collection[-1]]  # slice notation doesn't work here
        else:
            entities = [collection[-1]]

        new_tags = []
        for index, tag in enumerate(tags_mod):
            identifiers = [{'href': tag._href}, {'id': tag.id}]
            new_tags.append(identifiers[index % 2])

        # add some more tags in supported formats
        new_tags.append({'category': 'department', 'name': 'finance'})
        new_tags.append({'name': '/managed/department/presales'})
        tags_ids = set([t.id for t in tags_mod])
        tags_ids.add(
            appliance.rest_api.collections.tags.get(name='/managed/department/finance').id)
        tags_ids.add(
            appliance.rest_api.collections.tags.get(name='/managed/department/presales').id)
        tags_count = len(new_tags) * len(entities)

        def _verify_action_result():
            assert appliance.rest_api.response.status_code == 200
            response = appliance.rest_api.response.json()
            assert len(response['results']) == tags_count
            num_success = 0
            for result in response['results']:
                if result['success']:
                    num_success += 1
            assert num_success == tags_count

        collection.action.assign_tags(*entities, tags=new_tags)
        _verify_action_result()
        for entity in entities:
            entity.tags.reload()
            assert len(tags_ids - set([t.id for t in entity.tags.all])) == 0

        collection.action.unassign_tags(*entities, tags=new_tags)
        _verify_action_result()
        for entity in entities:
            entity.tags.reload()
            assert len(set([t.id for t in entity.tags.all]) - tags_ids) == entity.tags.subcount

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_invalid_tag(self, appliance, dummy_services, vm,
            collection_name):
        """Tests bulk assigning and unassigning invalid tags.

        Metadata:
            test_flag: rest
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        if len(collection) > 1:
            entities = [collection[-2], collection[-1]]  # slice notation doesn't work here
        else:
            entities = [collection[-1]]

        new_tags = ['invalid_tag1', 'invalid_tag2']
        tags_count = len(new_tags) * len(entities)
        tags_per_entities_count = []
        for entity in entities:
            entity.tags.reload()
            tags_per_entities_count.append(entity.tags.subcount)

        def _verify_action_result():
            assert appliance.rest_api.response.status_code == 200
            response = appliance.rest_api.response.json()
            assert len(response['results']) == tags_count
            num_fail = 0
            for result in response['results']:
                if not result['success']:
                    num_fail += 1
            assert num_fail == tags_count

        def _check_tags_counts():
            for index, entity in enumerate(entities):
                entity.tags.reload()
                assert entity.tags.subcount == tags_per_entities_count[index]

        collection.action.assign_tags(*entities, tags=new_tags)
        _verify_action_result()
        _check_tags_counts()

        collection.action.unassign_tags(*entities, tags=new_tags)
        _verify_action_result()
        _check_tags_counts()
