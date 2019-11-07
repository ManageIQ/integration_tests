# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.tests.configure.test_access_control as tac
from cfme import test_requirements
from cfme.services.catalogs.catalog import CatalogsView
from cfme.services.catalogs.catalog import DetailsCatalogView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update


pytestmark = [test_requirements.service, pytest.mark.tier(2)]


@pytest.mark.rhel_testing
@pytest.mark.sauce
def test_catalog_crud(request, appliance):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/8h
        tags: service
    """
    # Create Catalog
    catalog_name = fauxfactory.gen_alphanumeric(start="cat_")
    cat = appliance.collections.catalogs.create(name=catalog_name, description='my catalog')
    request.addfinalizer(cat.delete_if_exists)

    view = cat.create_view(CatalogsView, wait="10s")
    assert view.is_displayed
    if BZ(1766276, forced_streams=['5.11']).blocks:
        saved_message = f"Catalog was saved"
    else:
        saved_message = f'Catalog "{catalog_name}" was saved'
    view.flash.assert_success_message(saved_message)
    assert cat.exists

    # Edit Catalog
    update_descr = 'my edited description'
    with update(cat):
        cat.description = update_descr

    assert cat.description == update_descr

    view.flash.assert_success_message(saved_message)

    view = navigate_to(cat, 'Edit')
    view.fill(value={'description': 'test_cancel'})
    view.cancel_button.click()
    view = cat.create_view(DetailsCatalogView, wait="10s")
    assert view.is_displayed
    view.flash.assert_message(f'Edit of Catalog "{catalog_name}" was cancelled by the user')
    assert cat.description == update_descr

    # Delete Catalog
    cat.delete()
    view = cat.create_view(CatalogsView, wait="10s")
    if BZ(1765107).blocks:
        delete_message = f'Catalog "{cat.description}": Delete successful'
    else:
        delete_message = f'Catalog "{catalog_name}": Delete successful'
    view.flash.assert_success_message(delete_message)
    assert not cat.exists


@pytest.mark.sauce
def test_permissions_catalog_add(appliance, request):
    """ Tests that a catalog can be added only with the right permissions

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        tags: service
    """

    def _create_catalog(appliance):
        cat = appliance.collections.catalogs.create(
            name=fauxfactory.gen_alphanumeric(start="cat_"),
            description="my catalog"
        )
        request.addfinalizer(lambda: cat.delete())

    test_product_features = [['Everything', 'Services', 'Catalogs Explorer', 'Catalogs']]
    test_actions = {'Add Catalog': _create_catalog}

    tac.single_task_permission_test(appliance, test_product_features, test_actions)
