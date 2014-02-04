""" A page functions for Availability Zone


:var list_page: A :py:class:`cfme.web_ui.Region` object describing elements on the list page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing elements on the detail page.
"""

from cfme.web_ui import Region, Table


# Common locators
page_specific_locators = {
    'cancel_button': "//img[@title='Cancel']",
    'creds_validate_btn': "//div[@id='default_validate_buttons_on']"
                          "/ul[@id='form_buttons']/li/a/img",
    'creds_verify_disabled_btn': "//div[@id='default_validate_buttons_off']"
                                 "/ul[@id='form_buttons']/li/a/img",
}

# Page specific locators
list_page = Region(
    locators={
        'zone_table': Table(header_data=('//div[@class="xhdr"]/table', 1),
                            row_data=('//div[@class="objbox"]/table', 1))
    },
    title='CloudForms Management Engine: Cloud Providers')


details_page = Region(infoblock='detail')
