# -*- coding: utf-8 -*-
import datetime
import fauxfactory
import pytest

from cfme.rest import dialog as _dialog
from cfme.rest import services as _services
from cfme.rest import service_catalogs as _service_catalogs
from cfme.rest import service_templates as _service_templates
from cfme import test_requirements
from utils.providers import setup_a_provider as _setup_a_provider
from utils.wait import wait_for
from utils import error, version


pytestmark = [test_requirements.service,
              pytest.mark.tier(2)]


class TestServiceRESTAPI(object):
    @pytest.fixture(scope="module")
    def a_provider(self):
        return _setup_a_provider("infra")

    @pytest.fixture(scope="function")
    def dialog(self):
        return _dialog()

    @pytest.fixture(scope="function")
    def service_catalogs(self, request, rest_api):
        return _service_catalogs(request, rest_api)

    @pytest.fixture(scope="function")
    def services(self, request, rest_api, a_provider, dialog, service_catalogs):
        return _services(request, rest_api, a_provider, dialog, service_catalogs)

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    def test_delete_service_dialog(self, rest_api, dialog):
        service_dialog = rest_api.collections.service_dialogs.find_by(label=dialog.label)[0]
        service_dialog.action.delete()
        with error.expected("ActiveRecord::RecordNotFound"):
            service_dialog.action.delete()

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.7')
    def test_delete_service_dialogs(self, rest_api, dialog):
        service_dialog = rest_api.collections.service_dialogs.find_by(label=dialog.label)[0]
        rest_api.collections.service_dialogs.action.delete(service_dialog)
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.service_dialogs.action.delete(service_dialog)

    def test_edit_service(self, rest_api, services):
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

    def test_edit_multiple_services(self, rest_api, services):
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

    def test_delete_service(self, rest_api, services):
        service = rest_api.collections.services[0]
        service.action.delete()
        with error.expected("ActiveRecord::RecordNotFound"):
            service.action.delete()

    def test_delete_services(self, rest_api, services):
        rest_api.collections.services.action.delete(*services)
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.services.action.delete(*services)

    def test_retire_service_now(self, rest_api, services):
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

    def test_retire_service_future(self, rest_api, services):
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

        @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
        def test_set_service_owner(self, rest_api, services):
            if "set_ownership" not in rest_api.collections.services.action.all:
                pytest.skip("Set owner action for service is not implemented in this version")
            service = services[0]
            user = rest_api.collections.users.get(userid='admin')
            data = {
                "owner": {"href": user.href}
            }
            service.action.set_ownership(data)
            service.reload()
            assert hasattr(service, "evm_owner")
            assert service.evm_owner.userid == user.userid

        @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
        def test_set_services_owner(self, rest_api, services):
            if "set_ownership" not in rest_api.collections.services.action.all:
                pytest.skip("Set owner action for service is not implemented in this version")
            data = []
            user = rest_api.collections.users.get(userid='admin')
            for service in services:
                tmp_data = {
                    "href": service.href,
                    "owner": {"href": user.href}
                }
                data.append(tmp_data)
            rest_api.collections.services.action.set_ownership(*data)
            for service in services:
                service.reload()
                assert hasattr(service, "evm_owner")
                assert service.evm_owner.userid == user.userid


class TestServiceTemplateRESTAPI(object):
    @pytest.fixture(scope='function')
    def service_templates(self, request, rest_api, dialog):
        return _service_templates(request, rest_api, dialog)

    @pytest.fixture(scope="function")
    def dialog(self):
        return _dialog()

    @pytest.fixture(scope="function")
    def service_catalogs(self, request, rest_api):
        return _service_catalogs(request, rest_api)

    def test_edit_service_template(self, rest_api, service_templates):
        """Tests cediting a service template.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_templates (method ``edit``) with the ``name``
            * Check if the service_template with ``new_name`` exists
        Metadata:
            test_flag: rest
        """
        scl = rest_api.collections.service_templates[0]
        new_name = fauxfactory.gen_alphanumeric()
        scl.action.edit(name=new_name)
        wait_for(
            lambda: rest_api.collections.service_catalogs.find_by(name=new_name),
            num_sec=180,
            delay=10,
        )

    def test_delete_service_templates(self, rest_api, service_templates):
        rest_api.collections.service_templates.action.delete(*service_templates)
        with error.expected("ActiveRecord::RecordNotFound"):
            rest_api.collections.service_templates.action.delete(*service_templates)

    def test_delete_service_template(self, rest_api, service_templates):
        s_tpl = rest_api.collections.service_templates[0]
        s_tpl.action.delete()
        with error.expected("ActiveRecord::RecordNotFound"):
            s_tpl.action.delete()

    @pytest.mark.uncollectif(lambda: version.current_version() < '5.5')
    def test_assign_unassign_service_template_to_service_catalog(self, rest_api, service_catalogs,
            service_templates):
        """Tests assigning and unassigning the service templates to service catalog.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_catalogs/<id>/service_templates (method ``assign``)
                with the list of dictionaries service templates list
            * Check if the service_templates were assigned to the service catalog
            * POST /api/service_catalogs/<id>/service_templates (method ``unassign``)
                with the list of dictionaries service templates list
            * Check if the service_templates were unassigned to the service catalog
        Metadata:
            test_flag: rest
        """

        scl = service_catalogs[0]
        stpl = service_templates[0]
        scl.service_templates.action.assign(stpl)
        scl.reload()
        assert stpl.id in [st.id for st in scl.service_templates.all]
        scl.service_templates.action.unassign(stpl)
        scl.reload()
        assert stpl.id not in [st.id for st in scl.service_templates.all]

    def test_edit_multiple_service_templates(self, rest_api, service_templates):
        """Tests editing multiple service catalogs at time.
        Prerequisities:
            * An appliance with ``/api`` available.
        Steps:
            * POST /api/service_templates (method ``edit``)
                with the list of dictionaries used to edit
            * Check if the service_templates with ``new_name`` each exists
        Metadata:
            test_flag: rest
        """
        new_names = []
        service_tpls_data_edited = []
        for tpl in service_templates:
            new_name = fauxfactory.gen_alphanumeric()
            new_names.append(new_name)
            service_tpls_data_edited.append({
                "href": tpl.href,
                "name": new_name,
            })
        rest_api.collections.service_templates.action.edit(*service_tpls_data_edited)
        for new_name in new_names:
            wait_for(
                lambda: rest_api.collections.service_templates.find_by(name=new_name),
                num_sec=180,
                delay=10,
            )
