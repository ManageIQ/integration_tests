# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration import Category, Tag
from cfme.rest import tags as _tags
from cfme.rest import categories as _categories
from utils.api import APIException
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


def test_tag_crud(category):
    tag = Tag(name=fauxfactory.gen_alphanumeric(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(32),
              category=category)
    tag.create()
    with update(tag):
        tag.display_name = fauxfactory.gen_alphanumeric(32)
    tag.delete(cancel=False)


class TestTagsViaREST(object):

    @pytest.fixture(scope="function")
    def categories(self, request, rest_api, num=3):
        return _categories(request, rest_api, num)

    @pytest.fixture(scope="function")
    def tags(self, request, rest_api, categories):
        return _tags(request, rest_api, categories)

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
    def test_edit_tags(self, rest_api, tags):
        if "edit" not in rest_api.collections.tags.action.all:
            pytest.skip("Edit tags action is not implemented in this version")

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

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
    def test_edit_tag(self, rest_api, tags):
        if "edit" not in rest_api.collections.tags.action.all:
            pytest.skip("Edit tags action is not implemented in this version")

        tag = rest_api.collections.tags.get(name=tags[0].name)
        new_name = 'test_tag_{}'.format(fauxfactory.gen_alphanumeric())
        tag.action.edit(name=new_name)
        wait_for(
            lambda: rest_api.collections.tags.find_by(name=new_name),
            num_sec=180,
            delay=10,
        )

    @pytest.mark.meta(blockers=[BZ(1290783, forced_streams=["5.5"])])
    @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_delete_tags(self, rest_api, tags, multiple):
        if "delete" not in rest_api.collections.tags.action.all:
            pytest.skip("Delete tags action is not implemented in this version")

        if multiple:
            rest_api.collections.tags.action.delete(*tags)
            with error.expected("ActiveRecord::RecordNotFound"):
                rest_api.collections.tags.action.delete(*tags)
        else:
            tag = tags[0]
            tag.action.delete()
            with error.expected("ActiveRecord::RecordNotFound"):
                tag.action.delete()

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
    def test_create_tag_with_wrong_arguments(self, rest_api):
        data = {
            'name': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower()),
            'description': 'test_tag_{}'.format(fauxfactory.gen_alphanumeric().lower())
        }
        try:
            rest_api.collections.tags.action.create(data)
        except APIException as e:
            assert "Category id, href or name needs to be specified" in e.args[0]
