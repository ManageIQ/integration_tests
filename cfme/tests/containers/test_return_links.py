# -*- coding: utf-8 -*-
import pytest
from cfme.fixtures import pytest_selenium as sel
from utils import testgen
from utils.version import current_version
from cfme.containers import service
from cfme.containers import route
from cfme.containers import project
from cfme.containers.service import Service, list_tbl as list_tbl_service
from cfme.containers.route import Route, list_tbl as list_tbl_route
from cfme.containers.project import Project, list_tbl as list_tbl_project


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9906 # CMP-9905 # CMP-9904


def test_services_link(provider):
    """ Module that deals with links that allow user to go back to previous page
    """
    sel.force_navigate('containers_services')
    ui_services = [r.name.text for r in list_tbl_service.rows()]

    for name in ui_services:
        obj = Service(name, provider)
        obj.navigate()
        sel.click(service.link_to_prv_page)
        assert "Services" in sel.title()


def test_routes_link(provider):
    sel.force_navigate('containers_routes')
    ui_routes = [r.name.text for r in list_tbl_route.rows()]

    for name in ui_routes:
        obj = Route(name, provider)
        obj.navigate()
        sel.click(route.link_to_prv_page)
        assert "Routes" in sel.title()


def test_projects_link(provider):
    sel.force_navigate('containers_projects')
    ui_projects = [r.name.text for r in list_tbl_project.rows()]

    for name in ui_projects:
        obj = Project(name, provider)
        obj.navigate()
        sel.click(project.link_to_prv_page)
        assert "Projects" in sel.title()
