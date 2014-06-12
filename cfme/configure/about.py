# -*- coding: utf-8 -*-
from cfme.web_ui import Region
from utils import version

product_assistance = Region(
    locators={
        'quick_start_guide': "//a[.='Quick Start Guide']",
        'installation_guide': "//a[.='Installation Guide']",
        'insight_guide': "//a[.='Insight Guide']",
        'control_guide': "//a[.='Control Guide']",
        'lifecycle_and_automation_guide': "//a[.='Lifecycle and Automation Guide']",
        'integrate_guide': version.pick({'default': "//a[.='Integrate Guide']",
                                        '5.3': "//a[.='Integration Services Guide']"}),
        'settings_and_operations_guide': "//a[.='Settings and Operations Guide']",
        'red_hat_customer_portal': "//a[.='Red Hat Customer Portal']"
    },
    title='CloudForms Management Engine: About',
    identifying_loc='quick_start_guide',
    infoblock_type="form"
)