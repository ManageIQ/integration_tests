# -*- coding: utf-8 -*-
from cfme.web_ui import Region
from utils import version

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
        'soap_api_guide': {
            version.LOWEST: None,
            "5.4.0.1": "//a[normalize-space(.)='SOAP API Guide']",
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
