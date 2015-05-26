# -*- coding: utf-8 -*-
from cfme.web_ui import Region
from utils import version

product_assistance = Region(
    locators=version.pick({
        version.LOWEST: {
            'quick_start_guide': "//a[normalize-space(.)='Quick Start Guide']",
            'install_guide': "//a[normalize-space(.)='Installation Guide']",
            'insight_guide': "//a[normalize-space(.)='Insight Guide']",
            'control_guide': "//a[normalize-space(.)='Control Guide']",
            'lifecycle_and_automation_guide':
                "//a[normalize-space(.)='Lifecycle and Automation Guide']",
            'integrate_guide': "//a[normalize-space(.)='Integrate Guide']",
            'settings_and_operations_guide':
                "//a[normalize-space(.)='Settings and Operations Guide']",
            'red_hat_customer_portal': "//a[normalize-space(.)='Red Hat Customer Portal']"
        },
        '5.3': {
            'quick_start_guide': "//a[normalize-space(.)='Quick Start Guide']",
            'insight_guide': "//a[normalize-space(.)='Insight Guide']",
            'control_guide': "//a[normalize-space(.)='Control Guide']",
            'lifecycle_and_automation_guide':
                "//a[normalize-space(.)='Lifecycle and Automation Guide']",
            'integrate_guide': "//a[normalize-space(.)='Integration Services Guide']",
            'settings_and_operations_guide':
                "//a[normalize-space(.)='Settings and Operations Guide']",
            'red_hat_customer_portal': "//a[normalize-space(.)='Red Hat Customer Portal']"
        },
        '5.4': {
            'quick_start_guide': "//a[normalize-space(.)='Quick Start Guide']",
            'insight_guide': "//a[normalize-space(.)='Insight Guide']",
            'control_guide': "//a[normalize-space(.)='Control Guide']",
            'lifecycle_and_automation_guide':
                "//a[normalize-space(.)='Lifecycle and Automation Guide']",
            'rest_guide': "//a[normalize-space(.)='REST API Guide']",
            'soap_guide': "//a[normalize-space(.)='SOAP API Guide']",
            'user_guide': "//a[normalize-space(.)='User Guide']",
            'settings_and_operations_guide':
                "//a[normalize-space(.)='Settings and Operations Guide']",
            'red_hat_customer_portal': "//a[normalize-space(.)='Red Hat Customer Portal']"
        }
    }),
    title='About',
    identifying_loc='quick_start_guide',
    infoblock_type="form"
)
