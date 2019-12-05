"""Fixtures that VMware console tests use to configure VM Console type and start websocket."""
import pytest

from cfme.utils.log import logger


@pytest.fixture(scope="module")
def configure_console_vnc(appliance):
    """Configure VMware Console to use VMware VNC."""
    logger.info("Changing VMware console suppport configuration to VNC")
    appliance.server.settings.update_vmware_console({'console_type': 'VNC'})


@pytest.fixture(scope="module")
def configure_console_webmks(appliance):
    """Configure VMware Console to use VMware WebMKS."""
    logger.info("Changing VMware console suppport configuration to VMware WebMKS")
    appliance.server.settings.update_vmware_console({'console_type': 'VMware WebMKS'})


@pytest.fixture(scope="module")
def configure_websocket(appliance):
    """Enable websocket role if it is disabled.

    Currently the fixture cfme/fixtures/base.py:27,
    disables the websocket role to avoid intrusive popups.
    """
    if appliance.version < '5.11':
        logger.info('Enabling the websocket role to allow console connections')
        appliance.server.settings.enable_server_roles('websocket')
