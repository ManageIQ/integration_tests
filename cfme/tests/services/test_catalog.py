# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.tests.configure.test_access_control as tac
from cfme import test_requirements
from cfme.services.catalogs.catalog import CatalogsView
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [test_requirements.service, pytest.mark.tier(2)]


@pytest.mark.rhel_testing
@pytest.mark.sauce
def test_catalog_crud(appliance):
    """
    Polarion:
        assignee: sshveta
        casecomponent: Services
        initialEstimate: 1/8h
    """
    catalog_name = fauxfactory.gen_alphanumeric()
    cat = appliance.collections.catalogs.create(name=catalog_name, description='my catalog')

    view = cat.create_view(CatalogsView)
    assert view.is_displayed
    view.flash.assert_success_message('Catalog "{}" was saved'.format(catalog_name))

    with update(cat):
        cat.description = 'my edited description'
    cat.delete()


@pytest.mark.sauce
def test_catalog_duplicate_name(appliance):
    """
    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
    """
    catalog_name = fauxfactory.gen_alphanumeric()
    cat = appliance.collections.catalogs.create(name=catalog_name, description='my catalog')
    with pytest.raises(AssertionError):
        appliance.collections.catalogs.create(name=catalog_name, description='my catalog')
    view = cat.create_view(CatalogsView)
    view.flash.assert_message('Name has already been taken')


@pytest.mark.sauce
def test_permissions_catalog_add(appliance, request):
    """ Tests that a catalog can be added only with the right permissions

    Polarion:
        assignee: sshveta
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
    """

    def _create_catalog(appliance):
        cat = appliance.collections.catalogs.create(name=fauxfactory.gen_alphanumeric(),
                                                    description="my catalog")
        request.addfinalizer(lambda: cat.delete())

    test_product_features = [['Everything', 'Services', 'Catalogs Explorer', 'Catalogs']]
    test_actions = {'Add Catalog': _create_catalog}

    tac.single_task_permission_test(appliance, test_product_features, test_actions)
