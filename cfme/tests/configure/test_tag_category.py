# -*- coding: utf-8 -*-
import fauxfactory
from cfme.configure.configuration import Category
from cfme.rest import categories as _categories
import pytest
from utils.update import update
from utils.wait import wait_for
from utils import error, version


@pytest.mark.sauce
def test_category_crud():
    cg = Category(name=fauxfactory.gen_alphanumeric(8).lower(),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    with update(cg):
        cg.description = fauxfactory.gen_alphanumeric(32)
    cg.delete(cancel=False)


class TestCategoriesViaREST(object):

    @pytest.fixture(scope="function")
    def categories(self, request, rest_api):
        return _categories(request, rest_api, num=5)

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_edit_categories(self, rest_api, categories, multiple):
        if "edit" not in rest_api.collections.categories.action.all:
            pytest.skip("Edit categories action is not implemented in this version")

        if multiple:
            new_names = []
            ctgs_data_edited = []
            for ctg in categories:
                new_name = fauxfactory.gen_alphanumeric().lower()
                new_names.append(new_name)
                ctg.reload()
                ctgs_data_edited.append({
                    "href": ctg.href,
                    "description": "test_category_{}".format(new_name),
                })
            rest_api.collections.categories.action.edit(*ctgs_data_edited)
            for new_name in new_names:
                wait_for(
                    lambda: rest_api.collections.categories.find_by(description=new_name),
                    num_sec=180,
                    delay=10,
                )
        else:
            ctg = rest_api.collections.categories.get(description=categories[0].description)
            new_name = 'test_category_{}'.format(fauxfactory.gen_alphanumeric().lower())
            ctg.action.edit(description=new_name)
            wait_for(
                lambda: rest_api.collections.categories.find_by(description=new_name),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_delete_categories(self, rest_api, categories, multiple):
        if "delete" not in rest_api.collections.categories.action.all:
            pytest.skip("Delete categories action is not implemented in this version")

        if multiple:
            rest_api.collections.categories.action.delete(*categories)
            with error.expected("ActiveRecord::RecordNotFound"):
                rest_api.collections.categories.action.delete(*categories)
        else:
            ctg = categories[0]
            ctg.action.delete()
            with error.expected("ActiveRecord::RecordNotFound"):
                ctg.action.delete()
