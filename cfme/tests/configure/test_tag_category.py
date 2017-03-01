# -*- coding: utf-8 -*-
import fauxfactory
from cfme.configure.configuration import Category
from cfme.rest.gen_data import categories as _categories
import pytest
from utils.update import update
from utils.wait import wait_for
from utils import error


@pytest.mark.tier(2)
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
        response = _categories(request, rest_api, num=5)
        assert rest_api.response.status_code == 200
        assert len(response) == 5
        return response

    @pytest.mark.tier(3)
    def test_create_categories(self, rest_api, categories):
        """Tests creating categories.

        Metadata:
            test_flag: rest
        """
        for ctg in categories:
            record = rest_api.collections.categories.get(id=ctg.id)
            assert rest_api.response.status_code == 200
            assert record.name == ctg.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_edit_categories(self, rest_api, categories, multiple):
        """Tests editing categories.

        Metadata:
            test_flag: rest
        """
        if multiple:
            new_descriptions = []
            ctgs_data_edited = []
            for ctg in categories:
                new_description = "test_category_{}".format(fauxfactory.gen_alphanumeric().lower())
                new_descriptions.append(new_description)
                ctg.reload()
                ctgs_data_edited.append({
                    "href": ctg.href,
                    "description": new_description,
                })
            rest_api.collections.categories.action.edit(*ctgs_data_edited)
            assert rest_api.response.status_code == 200
            for new_description in new_descriptions:
                wait_for(
                    lambda: rest_api.collections.categories.find_by(description=new_description),
                    num_sec=180,
                    delay=10,
                )
        else:
            ctg = rest_api.collections.categories.get(description=categories[0].description)
            new_description = "test_category_{}".format(fauxfactory.gen_alphanumeric().lower())
            ctg.action.edit(description=new_description)
            assert rest_api.response.status_code == 200
            wait_for(
                lambda: rest_api.collections.categories.find_by(description=new_description),
                num_sec=180,
                delay=10,
            )

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_categories_from_detail(self, rest_api, categories, method):
        """Tests deleting categories from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for ctg in categories:
            ctg.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                ctg.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_categories_from_collection(self, rest_api, categories):
        """Tests deleting categories from collection.

        Metadata:
            test_flag: rest
        """
        rest_api.collections.categories.action.delete(*categories)
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.categories.action.delete(*categories)
        assert rest_api.response.status_code == 404
