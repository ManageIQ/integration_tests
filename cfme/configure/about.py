# -*- coding: utf-8 -*-
import re

import cfme.fixtures.pytest_selenium as sel
from cfme.exceptions import ElementOrBlockNotFound
from cfme.web_ui import Region, InfoBlock
from utils import version
from utils.appliance import current_appliance
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger
from utils.version import current_version


product_assistance = Region(
    locators={
        'quick_start_guide': {
            version.LOWEST: "//a[normalize-space(.)='Quick Start Guide']",
            "5.4.0.1": None
        },
        'insight_guide': {
            version.LOWEST: "//a[normalize-space(.)='Insight Guide']",
            '5.5': "//a[normalize-space(.)='Infrastructure Inventory Guide']"
        },
        'control_guide': {
            version.LOWEST: "//a[normalize-space(.)='Control Guide']",
            '5.5': "//a[normalize-space(.)='Defining Policies Profiles Guide']"
        },
        'lifecycle_and_automation_guide': {
            version.LOWEST: "//a[normalize-space(.)='Lifecycle and Automation Guide']",
            '5.5': "//a[normalize-space(.)='Methods For Automation Guide']"
        },
        'integrate_guide': {
            '5.4': "//a[normalize-space(.)='REST API Guide']",
            '5.5': None
        },
        'user_guide': {
            version.LOWEST: None,
            "5.4.0.1": "//a[normalize-space(.)='User Guide']",
            '5.5': "//a[normalize-space(.)='General Configuration Guide']"
        },
        'monitoring_guide': {
            version.LOWEST: None,
            '5.5': "//a[normalize-space(.)='Monitoring Alerts Reporting Guide']"
        },
        'providers_guide': {
            version.LOWEST: None,
            '5.5': "//a[normalize-space(.)='Providers Guide']"
        },
        'scripting_actions_guide': {
            version.LOWEST: None,
            '5.5': "//a[normalize-space(.)='Scripting Actions Guide']"
        },
        'vm_hosts_guide': {
            version.LOWEST: None,
            '5.5': "//a[normalize-space(.)='Virtual Machines Hosts Guide']"
        },
        'settings_and_operations_guide': {
            version.LOWEST: "//a[normalize-space(.)='Settings and Operations Guide']",
            '5.5': None
        },
        'red_hat_customer_portal': "//a[normalize-space(.)='Red Hat Customer Portal']"
    },
    title='About',
    identifying_loc='quick_start_guide',
    infoblock_type="form"
)


def get_detail(properties):
    navigate_to(current_appliance().server, 'About')
    if current_version() < '5.7':
        return InfoBlock.text(*properties).encode(
            "utf-8").strip()
    else:
        locator = '//div[@class="product-versions-pf"]//li'
        sel.wait_for_element(locator)
        for element in sel.elements(locator):
            logger.debug('Checking for detail match for "{}" in  "{}"'.format(properties,
                                                                              element.text))
            match = re.match("{}\s(?P<value>.*)".format(properties), element.text)
            if match:
                return match.group('value')
        else:
            raise ElementOrBlockNotFound('Could not match about detail {}'.format(properties))
