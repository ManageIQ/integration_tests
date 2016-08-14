# -*- coding: utf-8 -*-

""" Polarion test case CMP-9884.
"""
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.service import Service, list_tbl as list_tbl_srvc
from utils import testgen
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


@pytest.mark.parametrize('rel',
                         ['name',
                          'creation_timestamp',
                          'resource_version',
                          'session_affinity',
                          'type',
                          'portal_ip'
                          ])
def test_services_properties_rel(provider, rel):
    sel.force_navigate('containers_services')
    ui_services = [r.name.text for r in list_tbl_srvc.rows()]
    mgmt_objs = provider.mgmt.list_service()  # run only if table is not empty

    if ui_services:
        # verify that mgmt services exist in ui listed services
        assert set(ui_services).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_services:
        obj = Service(name, provider)
        field_content = getattr(obj.summary.properties, rel).text_value

        if field_content:
            assert len(field_content) != 0
