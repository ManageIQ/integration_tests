# -*- coding: utf-8 -*-
import pytest

from cfme.containers.provider import ContainersProvider
from cfme.base.login import BaseLoggedInPage
from cfme.utils.version import current_version
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.8"),
    pytest.mark.provider([ContainersProvider], scope='function')
]


def config_menus_visibility(appliance, is_visible):
    # Configure the menus visibility parameters in config/settings.yaml
    yaml_config = appliance.get_yaml_config()

    if (yaml_config['product']['datawarehouse_manager'] == is_visible) and \
            (yaml_config['prototype']['monitoring'] == is_visible):
        return  # If this is already the state, return

    yaml_config['product']['datawarehouse_manager'] = is_visible
    yaml_config['prototype']['monitoring'] = is_visible

    appliance.set_yaml_config(yaml_config)
    appliance.reboot()


def is_menu_visible(appliance, link_text):
    navigate_to(ContainersProvider, 'All')
    logged_in_page = appliance.browser.create_view(BaseLoggedInPage)
    return link_text in logged_in_page.navigation.nav_links()


@pytest.yield_fixture(scope='module')
def config_menus_visible(appliance):
    config_menus_visibility(appliance, True)
    yield
    config_menus_visibility(appliance, False)


@pytest.mark.polarion('CMP-10614')
def test_datawarehouse_invisible(appliance):
    # This should be the default state
    yaml_config = appliance.get_yaml_config()
    assert not yaml_config['product']['datawarehouse_manager'], \
        'Datawarehouse menu should be configured as invisible by default ' \
        '(currently configured as visible)'
    assert not is_menu_visible(appliance, 'Datawarehouse')


@pytest.mark.polarion('CMP-10613')
def test_monitoring_invisible(appliance):
    # This should be the default state
    yaml_config = appliance.get_yaml_config()
    assert not yaml_config['prototype']['monitoring'], \
        'Monitor menu should be configured as invisible by default ' \
        '(currently configured as visible)'
    assert not is_menu_visible(appliance, 'Monitor')


@pytest.mark.uncollectif(lambda: current_version() < "5.9")
@pytest.mark.polarion('CMP-10649')
def test_monitoring_visible(appliance, config_menus_visible):
    assert is_menu_visible(appliance, 'Monitor'), \
        'Monitor menu should be visible (currently invisible)'
