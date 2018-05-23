# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from selenium.common.exceptions import NoSuchElementException

from cfme import test_requirements
from cfme.rest.gen_data import service_catalogs as _service_catalogs
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.log import logger
from cfme.utils.rest import (
    assert_response,
    delete_resources_from_collection,
    delete_resources_from_detail,
)


pytestmark = [
    test_requirements.service,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2)
]


@pytest.fixture(scope="function")
def catalog_item(appliance, dialog, catalog):
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog)
    return catalog_item


def test_delete_catalog_deletes_service(appliance, dialog, catalog):
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
    """
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=item_name,
        description="my catalog", display_in=True, catalog=catalog,
        dialog=dialog)
    catalog.delete()
    service_catalogs = ServiceCatalogs(appliance, catalog, catalog_item.name)
    with pytest.raises(NoSuchElementException):
        service_catalogs.order()


def test_delete_catalog_item_deletes_service(appliance, catalog_item):
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
    """
    catalog_item.delete()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    with pytest.raises(NoSuchElementException):
        service_catalogs.order()


def test_service_circular_reference(appliance, catalog_item):
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
    """
    bundle_name = "first_" + fauxfactory.gen_alphanumeric()
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
        catalog_items=[catalog_item.name])
    sec_bundle_name = "sec_" + fauxfactory.gen_alphanumeric()
    sec_catalog_bundle = appliance.collections.catalog_bundles.create(
        sec_bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog,
        dialog=catalog_item.dialog, catalog_items=[bundle_name])
    msg = ("Error during 'Resource Add': Adding resource <{}> to Service <{}> "
           "will create a circular reference".format(sec_bundle_name, bundle_name))
    with pytest.raises(Exception, match=msg):
        catalog_bundle.update({'catalog_items': sec_catalog_bundle.name})


def test_service_generic_catalog_bundle(appliance, catalog_item):
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: medium
        initialEstimate: 1/8h
    """
    bundle_name = "generic_" + fauxfactory.gen_alphanumeric()
    appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
        catalog_items=[catalog_item.name])
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, bundle_name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', bundle_name)
    request_description = bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Request failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg


def test_bundles_in_bundle(appliance, catalog_item):
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/8h
    """
    bundle_name = "first_" + fauxfactory.gen_alphanumeric()
    appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
        catalog_items=[catalog_item.name])
    sec_bundle_name = "sec_" + fauxfactory.gen_alphanumeric()
    appliance.collections.catalog_bundles.create(
        sec_bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
        catalog_items=[bundle_name])
    third_bundle_name = "third_" + fauxfactory.gen_alphanumeric()
    third_catalog_bundle = appliance.collections.catalog_bundles.create(
        third_bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog,
        catalog_items=[bundle_name, sec_bundle_name])
    service_catalogs = ServiceCatalogs(appliance, third_catalog_bundle.catalog, third_bundle_name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', bundle_name)
    request_description = third_bundle_name
    provision_request = appliance.collections.requests.instantiate(request_description,
                                                                   partial_check=True)
    provision_request.wait_for_request()
    msg = "Request failed with the message {}".format(provision_request.rest.message)
    assert provision_request.is_succeeded(), msg


def test_delete_dialog_before_parent_item(appliance, catalog_item):
    """
    Polarion:
        assignee: sshveta
        casecomponent: services
        caseimportance: low
        initialEstimate: 1/8h
    """
    service_dialog = appliance.collections.service_dialogs
    dialog = service_dialog.instantiate(label=catalog_item.dialog.label)
    error_message = ('Dialog \"{}\": Error during delete: Dialog cannot be'
        ' deleted because it is connected to other components.').format(catalog_item.dialog.label)
    with pytest.raises(Exception, match=error_message):
        dialog.delete()


class TestServiceCatalogViaREST(object):
    @pytest.fixture(scope="function")
    def service_catalogs(self, request, appliance):
        return _service_catalogs(request, appliance.rest_api)

    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_service_catalog(self, service_catalogs, method):
        """Tests delete service catalog via rest.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: sshveta
            caseimportance: low
            initialEstimate: 1/3h
        """
        delete_resources_from_detail(service_catalogs, method=method)

    def test_delete_service_catalogs(self, service_catalogs):
        """Tests delete service catalogs via rest.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: sshveta
            caseimportance: low
            initialEstimate: 1/3h
        """
        delete_resources_from_collection(service_catalogs)

    def test_edit_service_catalog(self, appliance, service_catalogs):
        """Tests editing a service catalog via rest.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_catalogs/<id>/ (method ``edit``) with the ``name``
            * Check if the service_catalog with ``new_name`` exists
        Metadata:
            test_flag: rest

        Polarion:
            assignee: sshveta
            caseimportance: low
            initialEstimate: 1/3h
        """
        for ctl in service_catalogs:
            new_name = fauxfactory.gen_alphanumeric()
            response = ctl.action.edit(name=new_name)
            assert_response(appliance)
            assert response.name == new_name
            ctl.reload()
            assert ctl.name == new_name

    def test_edit_multiple_service_catalogs(self, appliance, service_catalogs):
        """Tests editing multiple service catalogs at time.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_catalogs (method ``edit``)
                with the list of dictionaries used to edit
            * Check if the service_catalogs with ``new_name`` each exist
        Metadata:
            test_flag: rest

        Polarion:
            assignee: sshveta
            caseimportance: low
            initialEstimate: 1/3h
        """

        new_names = []
        scls_data_edited = []
        for scl in service_catalogs:
            new_name = fauxfactory.gen_alphanumeric()
            new_names.append(new_name)
            scls_data_edited.append({
                "href": scl.href,
                "name": new_name,
            })
        response = appliance.rest_api.collections.service_catalogs.action.edit(*scls_data_edited)
        assert_response(appliance)
        assert len(response) == len(new_names)
        for index, resource in enumerate(response):
            assert resource.name == new_names[index]
            scl = service_catalogs[index]
            scl.reload()
            assert scl.name == new_names[index]
