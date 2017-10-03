# -*- coding: utf-8 -*-
import pytest

from cfme.infrastructure.provider import InfraProvider
from cfme.services.myservice import MyService
from cfme import test_requirements
from cfme.utils import testgen
from cfme.utils.appliance import ViaSSUI
from cfme.utils.log import logger
from cfme.utils.version import current_version

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.ssui,
    pytest.mark.long_running
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.fixture(scope="module")
def configure_websocket(appliance):
    """
    Enable websocket role if it is disabled.
    Currently the fixture cfme/fixtures/base.py:27,
    disables the websocket role to avoid intrusive popups.
    """
    appliance.server.settings.enable_server_roles('websocket')
    logger.info('Enabling the websocket role to allow console connections')
    yield
    appliance.server.settings.disable_server_roles('websocket')
    logger.info('Disabling the websocket role to avoid intrusive popups')


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize('context', [ViaSSUI])
def test_myservice_crud(appliance, setup_provider, context, order_catalog_item_in_ops_ui):
    """Tests Myservice crud in SSUI."""
    service_name = order_catalog_item_in_ops_ui
    with appliance.context.use(context):
        appliance.server.login()
        myservice = MyService(appliance, service_name)
        myservice.update({'name': '{}_edited'.format(service_name)})
        # TODO - add rest of myservice crud like delete in next phase.


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize('context', [ViaSSUI])
@pytest.mark.parametrize('order_catalog_item_in_ops_ui', [['console_test']], indirect=True)
def test_vm_console(appliance, setup_provider, context, configure_websocket,
        order_catalog_item_in_ops_ui):
    """Tests Myservice VM Console in SSUI."""
    service_name = order_catalog_item_in_ops_ui
    with appliance.context.use(context):
        appliance.server.login()
        myservice = MyService(appliance, service_name)
        myservice.launch_vm_console()
