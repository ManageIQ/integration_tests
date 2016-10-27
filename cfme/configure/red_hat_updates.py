# -*- coding: utf-8 -*-
import re

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import CheckboxTable, Form, Input, Region, Select, fill, flash, form_buttons
from cfme.configure.configuration import nav  # noqa
from utils import version
from utils.appliance import current_appliance
from utils.appliance.implementations.ui import navigate_to


"""
Represents Configure/Configuration/Region/RedHatUpdates

Usage:
    update_registration(
        "rhsm",
        "subscription.rhn.redhat.com",
        "user",
        "secret",
        "rhel-6-server-cfme-repo",
        "",
        True,
        "10.20.30.40:1234",
        "proxy_user",
        "proxy_secret"
    )
    register_appliances('EVM_1', 'EVM_2')
    are_registered('EVM_1')
    are_subscribed('EVM_1')
    checked_updates('EVM_1', 'EVM_2')
    update_appliances('EVM_1', 'EVM_2')
    versions_match('1.2.3.4', 'EVM_1', 'EVM_2')
    platform_updates_available('EVM_1', 'EVM_2')

Note:
    Argument `organization` can be only used with Satellite 5/6
    (i.e. when service is either `sat5` or `sat6`).
"""


def make_update_button(text):
    return "//div[@id='settings_rhn']//button[normalize-space(.)='{}']".format(text)


update_buttons = Region(
    locators={
        'edit_registration': make_update_button("Edit Registration"),
        'refresh': make_update_button("Refresh List"),
        'check_updates': make_update_button("Check for Updates"),
        'register': make_update_button("Register"),
        'apply_updates': make_update_button("Apply CFME Update")
    },
    identifying_loc="edit_registration"
)


registration_form = Form(
    fields=[
        ("service", Select("//select[@id='register_to']")),
        ("url", Input('server_url')),
        ("repo_name", Input('repo_name')),
        ("use_proxy", Input('use_proxy')),
        ("proxy_url", Input('proxy_address')),
        ("proxy_username", Input('proxy_userid')),
        ("proxy_password", Input('proxy_password')),
        ("proxy_password_verify", Input('proxy_password2')),  # 5.4+
        ("username", Input('customer_userid')),
        ("password", Input('customer_password')),
        ("password_verify", Input('customer_password2')),  # 5.4+
        ("organization_sat5", Input('customer_org')),
        ("organization_sat6", Select("//select[@id='customer_org']"))
    ]
)


registration_buttons = Region(
    locators={
        'url_default': "//button[@id='rhn_default_button']",
        'repo_default': "//button[@id='repo_default_name']",
    },
    identifying_loc="url_default"
)


service_types = {
    'rhsm': 'sm_hosted',
    'sat5': 'rhn_satellite',
    'sat6': 'rhn_satellite6'
}


appliances_table = lambda: version.pick({
    version.LOWEST: CheckboxTable("//div[@id='form_div']/table[@class='style3']"),
    '5.4': CheckboxTable("//div[@id='form_div']/table")
})


def update_registration(service,
                        url,
                        username,
                        password,
                        password_verify=None,
                        repo_name=None,
                        organization=None,
                        use_proxy=False,
                        proxy_url=None,
                        proxy_username=None,
                        proxy_password=None,
                        proxy_password_verify=None,
                        validate=True,
                        cancel=False,
                        set_default_rhsm_address=False,
                        set_default_repository=False):
    """ Fill in the registration form, validate and save/cancel

    Args:
        service: Service type (registration method).
        url: Service server URL address.
        username: Username to use for registration.
        password: Password to use for registration.
        password_verify: 2nd entry of password for verification.
                         Same as 'password' if None.
        repo_or_channel: Repository/channel to enable.
        organization: Organization (sat5/sat6 only).
        use_proxy: `True` if proxy should be used, `False` otherwise
                   (default `False`).
        proxy_url: Address of the proxy server.
        proxy_username: Username for the proxy server.
        proxy_password: Password for the proxy server.
        proxy_password_verify: 2nd entry of proxy server password for verification.
                               Same as 'proxy_password' if None.
        validate: Click the Validate button and check the
                  flash message for errors if `True` (default `True`)
        cancel: Click the Cancel button if `True` or the Save button
                if `False` (default `False`)
        set_default_rhsm_address: Click the Default button connected to
                                  the RHSM (only) address if `True`
        set_default_repository: Click the Default button connected to
                                the repo/channel if `True`

    Warning:
        'password_verify' and 'proxy_password_verify' are available in 5.4+ only.

    Note:
        With satellite 6, it is necessary to validate credentials to obtain
        available organizations from the server.
        With satellite 5, 'validate' parameter is ignored because there is
        no validation button available.
    """
    assert service in service_types, "Unknown service type '{}'".format(service)
    service_value = service_types[service]

    # In 5.4+, we have verification inputs as well
    if version.current_version() >= '5.4':
        password_verify = password_verify or password
        proxy_password_verify = proxy_password_verify or proxy_password
    # Otherwise, verification inputs are ignored df even if specified
    else:
        password_verify = None
        proxy_password_verify = None

    # Sat6 organization can be selected only after successful validation
    # while Sat5 organization is selected normally
    if service == 'sat6':
        organization_sat5 = None
        organization_sat6 = organization
    else:
        organization_sat5 = organization
        organization_sat6 = None

    navigate_to(current_appliance.server.zone.region, 'RedHatUpdates')
    sel.click(update_buttons.edit_registration)
    details = dict(
        service=sel.ByValue(service_value),
        url=url,
        username=username,
        password=password,
        password_verify=password_verify,
        repo_name=repo_name,
        organization_sat5=organization_sat5,
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        proxy_password_verify=proxy_password_verify
    )

    fill(registration_form, details)

    if set_default_rhsm_address:
        sel.click(registration_buttons.url_default)

    if set_default_repository:
        sel.click(registration_buttons.repo_default)

    if validate and service != 'sat5':
        sel.click(form_buttons.validate_short)
        flash.assert_no_errors()
        flash.dismiss()

    if organization_sat6:
        sel.select(registration_form.locators['organization_sat6'], organization_sat6)

    if cancel:
        form_buttons.cancel()
    else:
        form_buttons.save()
        flash.assert_message_match("Customer Information successfully saved")
        flash.dismiss()


def refresh():
    """ Click refresh button to update statuses of appliances
    """
    sel.click(update_buttons.refresh)


def register_appliances(*appliance_names):
    """ Register appliances by names

    Args:
        appliance_names: Names of appliances to register; will register all if empty
    """
    select_appliances(*appliance_names)
    sel.click(update_buttons.register)
    flash.assert_message_match("Registration has been initiated for the selected Servers")
    flash.dismiss()


def update_appliances(*appliance_names):
    """ Update appliances by names

    Args:
        appliance_names: Names of appliances to update; will update all if empty
    """
    select_appliances(*appliance_names)
    sel.click(update_buttons.apply_updates)
    flash.assert_message_match("Update has been initiated for the selected Servers")
    flash.dismiss()


def check_updates(*appliance_names):
    """ Run update check on appliances by names

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    select_appliances(*appliance_names)
    sel.click(update_buttons.check_updates)
    flash.assert_message_match("Check for updates has been initiated for the selected Servers")
    flash.dismiss()


def are_registered(*appliance_names):
    """ Check if appliances are registered

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    for row in get_appliance_rows(*appliance_names):
        if row.update_status.text.lower() == 'not registered':
            return False
    return True


def are_subscribed(*appliance_names):
    """ Check if appliances are subscribed

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    for row in get_appliance_rows(*appliance_names):
        if row.update_status.text.lower() in {'not registered', 'unsubscribed'}:
            return False
    return True


def versions_match(version, *appliance_names):
    """ Check if versions of appliances match version

    Args:
        version: Version to match against
        appliance_names: Names of appliances to check; will check all if empty
    """
    for row in get_appliance_rows(*appliance_names):
        if row.cfme_version.text != version:
            return False
    return True


def checked_updates(*appliance_names):
    """ Check if appliances checked if there is an update available

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    for row in get_appliance_rows(*appliance_names):
        if row.last_checked_for_updates.text == '':
            return False
    return True


def platform_updates_available(*appliance_names):
    """ Check if appliances have a platform update available

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    for row in get_appliance_rows(*appliance_names):
        if row.platform_updates_available.text.lower() != 'yes':
            return False
    return True


def get_available_version():
    """ Get available version printed on the page

    Returns:
        `None` if not available; string with version otherwise
         e.g. ``1.2.2.3``
    """
    if not update_buttons.is_displayed():
        navigate_to(current_appliance.server.zone.region, 'RedHatUpdates')
    available_version_loc = "div#rhn_buttons > table > tbody > tr > td"
    available_version_raw = sel.text(available_version_loc)
    available_version_search_res = re.search(r"([0-9]+\.)*[0-9]+", available_version_raw)
    if available_version_search_res:
        return available_version_search_res.group(0)
    return None


def select_appliances(*appliance_names):
    """ Select appliances by names

    Args:
        appliance_names: Names of appliances to select; will select all if empty
    """
    if not update_buttons.is_displayed():
        navigate_to(current_appliance.server.zone.region, 'RedHatUpdates')
    if appliance_names:
        cells = {'appliance': [name for name in appliance_names]}
        appliances_table().deselect_all()
        appliances_table().select_rows(cells)
    else:
        appliances_table().select_all()


def get_appliance_rows(*appliance_names):
    """ Get appliances as table rows

    Args:
        appliance_names: Names of appliances to get; will get all if empty
    """
    if not update_buttons.is_displayed():
        navigate_to(current_appliance.server.zone.region, 'RedHatUpdates')
    if appliance_names:
        rows = list()
        for row in appliances_table().rows():
            if row.appliance.text in appliance_names:
                rows.append(row)
    else:
        rows = appliances_table().rows()
    return rows
