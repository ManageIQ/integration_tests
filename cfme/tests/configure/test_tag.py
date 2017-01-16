# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from manageiq_client.api import APIException

from cfme.configure.configuration import Category, Tag
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import categories as _categories
from cfme.rest.gen_data import dialog as _dialog
from cfme.rest.gen_data import services as _services
from cfme.rest.gen_data import service_catalogs as _service_catalogs
from cfme.rest.gen_data import service_templates as _service_templates
from cfme.rest.gen_data import tenants as _tenants
from cfme.rest.gen_data import tags as _tags
from cfme.rest.gen_data import vm as _vm
from utils.blockers import BZ
from utils.update import update
from utils.wait import wait_for
from utils import error, version


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


@pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
class TestTagsViaREST(object):

    @pytest.fixture(scope="function")
    def categories(self, request, rest_api, num=3):
        return _categories(request, rest_api, num)

    @pytest.fixture(scope="function")
    def tags(self, request, rest_api, categories):
        return _tags(request, rest_api, categories)

    @pytest.fixture(scope="module")
    def categories_mod(self, request, rest_api_modscope, num=3):
        return _categories(request, rest_api_modscope, num)

    @pytest.fixture(scope="module")
    def tags_mod(self, request, rest_api_modscope, categories_mod):
        return _tags(request, rest_api_modscope, categories_mod)

    @pytest.fixture(scope="module")
    def service_catalogs(self, request, rest_api_modscope):
        return _service_catalogs(request, rest_api_modscope)

    @pytest.fixture(scope="module")
    def tenants(self, request, rest_api_modscope):
        return _tenants(request, rest_api_modscope, num=1)

    @pytest.fixture(scope="module")
    def a_provider(self):
        return _a_provider()

    @pytest.fixture(scope="module")
    def dialog(self):
        return _dialog()

    @pytest.fixture(scope="module")
    def services(self, request, rest_api_modscope, a_provider, dialog, service_catalogs):
        try:
            return _services(request, rest_api_modscope, a_provider, dialog, service_catalogs)
        except:
            pass

    @pytest.fixture(scope="module")
    def service_templates(self, request, rest_api_modscope, dialog):
        return _service_templates(request, rest_api_modscope, dialog)

    @pytest.fixture(scope="module")
    def vm(self, request, a_provider, rest_api_modscope):
        return _vm(request, a_provider, rest_api_modscope)

    @pytest.mark.tier(2)
    def test_edit_tags(self, rest_api, tags):
        new_names = []
        tags_data_edited = []
        for tag in tags:
            new_name = fauxfactory.gen_alphanumeric().lower()
            new_names.append(new_name)
            tag.reload()
            tags_data_edited.append({
                "href": tag.href,
                "name": "test_tag_{}".format(new_name),
            })
        rest_api.collections.tags.action.edit(*tags_data_edited)
        for new_name in new_names:
            wait_for(
                lambda: rest_api.collections.tags.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(2)
    def test_edit_tag(self, rest_api, tags):
        tag = rest_api.collections.tags.get(name=tags[0].name)
        new_name = 'test_tag_{}'.format(fauxfactory.gen_alphanumeric())
        tag.action.edit(name=new_name)
        wait_for(
            lambda: rest_api.collections.tags.find_by(name=new_name),
            num_sec=180,
            delay=10,
        )

    @pytest.mark.tier(3)
    @pytest.mark.meta(blockers=[BZ(1290783, forced_streams=["5.5"])])
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_delete_tags(self, rest_api, tags, multiple):
        if multiple:
            rest_api.collections.tags.action.delete(*tags)
            with error.expected("ActiveRecord::RecordNotFound"):
                rest_api.collections.tags.action.delete(*tags)
        else:
            tag = tags[0]
            tag.action.delete()
            with error.expected("ActiveRecord::RecordNotFound"):
                tag.action.delete()

    @pytest.mark.tier(3)
    def test_create_tag_with_wrong_arguments(self, rest_api):
        data = {
            'name': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'description': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower())
        }
        try:
            rest_api.collections.tags.action.create(data)
        except APIException as e:
            assert "Category id, href or name needs to be specified" in e.args[0]

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", ['clusters', 'hosts', 'data_stores', 'providers', 'resource_pools',
        'services', 'service_templates', 'tenants', 'vms'])
    def test_assign_and_unassign_tag(self, rest_api, tags_mod, a_provider, services,
            service_templates, tenants, vm, collection_name):
        col = getattr(rest_api.collections, collection_name)
        col.reload()
        if len(col.all) == 0:
            pytest.skip("No available entity in {} to assign tag".format(collection_name))
        collection = col[-1]
        tag = tags_mod[0]
        collection.tags.action.assign(tag)
        collection.reload()
        assert tag.id in [t.id for t in collection.tags.all]
        collection.tags.action.unassign(tag)
        collection.reload()
        assert tag.id not in [t.id for t in collection.tags.all]
