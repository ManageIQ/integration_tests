""" A model of Instances page in CFME

:var edit_page: A :py:class:`cfme.web_ui.Region` object describing the edit page.
:var details_page: A :py:class:`cfme.web_ui.Region` object describing the details page.
:var policy_page: A :py:class:`cfme.web_ui.Region` object describing the policy page.
:var edit_form: A :py:class:`cfme.web_ui.Form` object describing the instance edit form.
"""

from cfme.web_ui import Region, Form, Tree, Select


# Common locators
page_specific_locators = Region(
    locators={
        'cancel_button': "//img[@title='Cancel']",
        'creds_validate_btn': "//div[@id='default_validate_buttons_on']"
                              "/ul[@id='form_buttons']/li/a/img",
        'creds_verify_disabled_btn': "//div[@id='default_validate_buttons_off']"
                                     "/ul[@id='form_buttons']/li/a/img",
        'save_button': "//img[@title='Save Changes']",
    }
)

# Page specific locators
list_page = Region(
    title='CloudForms Management Engine: Instances'
)

edit_page = Region(
    locators={
        'save_btn': "//img[@title='Save Changes']",
        'reset_btn': "//img[@title='Reset Changes']",
        'cancel_btn': "//img[@title='Cancel']",
    })

details_page = Region(infoblock_type='detail')

policy_page = Region(
    locators={
        'policy_tree': Tree('//div[@class="containerTableStyle"]/table')
    })

# Forms
edit_form = Form(
    fields=[
        ('custom_ident', "//*[@id='custom_1']"),
        ('description_tarea', "//textarea[@id='description']"),
        ('parent_sel', "//*[@id='chosen_parent']"),
        ('child_sel', Select("//select[@id='kids_chosen']", multi=True)),
        ('vm_sel', Select("//select[@id='choices_chosen']", multi=True)),
        ('add_btn', "//img[@alt='Move selected VMs to left']"),
        ('remove_btn', "//img[@alt='Move selected VMs to right']"),
        ('remove_all_btn', "//img[@alt='Move all VMs to right']"),
    ])
