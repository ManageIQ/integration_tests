# -*- coding: utf-8 -*-
import datetime
import fauxfactory
import pytest

from cfme.rest import dialog as _dialog
from cfme.rest import services as _services
from cfme.rest import service_catalogs as _service_catalogs
from utils.providers import setup_a_provider as _setup_a_provider
from utils.wait import wait_for
from utils import error


@pytest.fixture(scope="module")
def a_provider():
    return _setup_a_provider("infra")


@pytest.mark.usefixtures("logged_in")
@pytest.fixture(scope="function")
def dialog():
    return _dialog()


@pytest.fixture(scope="function")
def service_catalogs(request, rest_api):
    return _service_catalogs(request, rest_api)


@pytest.mark.usefixtures("logged_in")
@pytest.fixture(scope="function")
def services(request, rest_api, a_provider, dialog, service_catalogs):
    return _services(request, rest_api, a_provider, dialog, service_catalogs)


def test_edit_service(rest_api, services):
    """Tests editing a service.
    Prerequisities:
        * An appliance with ``/api`` available.
    Steps:
        * POST /api/services (method ``edit``) with the ``name``
        * Check if the service with ``new_name`` exists
    Metadata:
        test_flag: rest
    """
    ser = services[0]
    new_name = fauxfactory.gen_alphanumeric()
    ser.action.edit(name=new_name)
    wait_for(
        lambda: rest_api.collections.services.find_by(name=new_name),
        num_sec=180,
        delay=10,
    )


def test_edit_multiple_services(rest_api, services):
    """Tests editing multiple service catalogs at time.
    Prerequisities:
        * An appliance with ``/api`` available.
    Steps:
        * POST /api/services (method ``edit``) with the list of dictionaries used to edit
        * Check if the services with ``new_name`` each exists
    Metadata:
        test_flag: rest
    """
    new_names = []
    services_data_edited = []
    for ser in services:
        new_name = fauxfactory.gen_alphanumeric()
        new_names.append(new_name)
        services_data_edited.append({
            "href": ser.href,
            "name": new_name,
        })
    rest_api.collections.services.action.edit(*services_data_edited)
    for new_name in new_names:
        wait_for(
            lambda: rest_api.collections.service_templates.find_by(name=new_name),
            num_sec=180,
            delay=10,
        )


def test_delete_service(rest_api, services):
    service = rest_api.collections.services[0]
    service.action.delete()
    with error.expected("ActiveRecord::RecordNotFound"):
        service.action.delete()


def test_delete_services(rest_api, services):
    rest_api.collections.services.action.delete(*services)
    with error.expected("ActiveRecord::RecordNotFound"):
        rest_api.collections.services.action.delete(*services)


def test_retire_service_now(rest_api, services):
    """Test retiring a service
    Prerequisities:
        * An appliance with ``/api`` available.
    Steps:
        * Retrieve list of entities using GET /api/services , pick the first one
        * POST /api/service/<id> (method ``retire``)
    Metadata:
        test_flag: rest
    """
    assert "retire" in rest_api.collections.services.action.all
    retire_service = services[0]
    retire_service.action.retire()
    wait_for(
        lambda: not rest_api.collections.services.find_by(name=retire_service.name),
        num_sec=600,
        delay=10,
    )


def test_retire_service_future(rest_api, services):
    """Test retiring a service
    Prerequisities:
        * An appliance with ``/api`` available.
    Steps:
        * Retrieve list of entities using GET /api/services , pick the first one
        * POST /api/service/<id> (method ``retire``) with the ``retire_date``
    Metadata:
        test_flag: rest
    """
    assert "retire" in rest_api.collections.services.action.all

    retire_service = services[0]
    date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime('%m/%d/%y')
    future = {
        "date": date,
        "warn": "4",
    }
    date_before = retire_service.updated_at
    retire_service.action.retire(future)

    def _finished():
        retire_service.reload()
        if retire_service.updated_at > date_before:
                return True
        return False

    wait_for(_finished, num_sec=600, delay=5, message="REST automation_request finishes")
