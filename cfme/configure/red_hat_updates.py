# -*- coding: utf-8 -*-
import re

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import CheckboxTable, Form, Region, Select, fill, flash, form_buttons
from cfme.configure.configuration import nav  # noqa


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
    return "//div[@id='settings_rhn']//button[.='{}']".format(text)


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
        ("url", "//input[@id='server_url']"),
        ("username", "//input[@id='customer_userid']"),
        ("password", "//input[@id='customer_password']"),
        ("repo_name", "//input[@id='repo_name']"),
        ("organization", "//input[@id='customer_org']"),
        ("use_proxy", "//input[@id='use_proxy']"),
        ("proxy_url", "//input[@id='proxy_address']"),
        ("proxy_username", "//input[@id='proxy_userid']"),
        ("proxy_password", "//input[@id='proxy_password']"),
    ]
)


registration_buttons = Region(
    locators={
        'url_default': "//button[@id='rhn_default_button']",
        'repo_default': "//button[@id='repo_default_name']",
        'validate': "//img[@title='Validate the credentials']"
    },
    identifying_loc="url_default"
)


service_types = {
    'rhsm': 'sm_hosted',
    'sat5': 'rhn_satellite',
    'sat6': 'rhn_satellite6'
}


appliances_table = CheckboxTable("//div[@id='form_div']/table[@class='style3']")


def update_registration(service,
                        url,
                        username,
                        password,
                        repo_name=None,
                        organization=None,
                        use_proxy=False,
                        proxy_url=None,
                        proxy_username=None,
                        proxy_password=None,
                        validate=False,
                        cancel=False,
                        set_default_rhsm_address=False,
                        set_default_repository=False):
    """ Fill in the registration form, validate and save/cancel

    Args:
        service: Service type (registration method).
        url: Service server URL address.
        username: Username to use for registration.
        password: Password to use for registration.
        repo_or_channel: Repository/channel to enable.
        organization: Organization (sat5/sat6 only).
        use_proxy: `True` if proxy should be used, `False` otherwise
                   (default `False`).
        proxy_url: Address of the proxy server.
        proxy_username: Username for the proxy server.
        proxy_password: Password for the proxy server.
        validate: Click the Validate button and check the
                  flash message for errors if `True` (default `False`)
        cancel: Click the Cancel button if `True` or the Save button
                if `False` (default `False`)
        set_default_rhsm_address: Click the Default button connected to
                                  the RHSM (only) address if `True`
        set_default_repository: Click the Default button connected to
                                the repo/channel if `True`
    """
    assert service in service_types, "Unknown service type '{}'".format(service)
    service_value = service_types[service]

    sel.force_navigate("cfg_settings_region_red_hat_updates")
    sel.click(update_buttons.edit_registration)
    details = dict(
        service=sel.ByValue(service_value),
        url=url,
        username=username,
        password=password,
        repo_name=repo_name,
        organization=organization,
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password
    )

    fill(registration_form, details)

    if set_default_rhsm_address:
        sel.click(registration_buttons.url_default)

    if set_default_repository:
        sel.click(registration_buttons.repo_default)

    if validate:
        sel.click(registration_buttons.validate)
        flash.assert_no_errors()
        flash.dismiss()

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


def update_appliances(*appliance_names):
    """ Update appliances by names

    Args:
        appliance_names: Names of appliances to update; will update all if empty
    """
    select_appliances(*appliance_names)
    sel.click(update_buttons.apply_updates)


def check_updates(*appliance_names):
    """ Run update check on appliances by names

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    select_appliances(*appliance_names)
    sel.click(update_buttons.check_updates)


def are_registered(*appliance_names):
    """ Check if appliances are registered

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    for row in get_appliance_rows(*appliance_names):
        if row.update_status.text == 'Not Registered':
            return False
    return True


def are_subscribed(*appliance_names):
    """ Check if appliances are subscribed

    Args:
        appliance_names: Names of appliances to check; will check all if empty
    """
    for row in get_appliance_rows(*appliance_names):
        if row.update_status.text in {'Not Registered', 'Unsubscribed'}:
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
        if row.platform_updates_available.text != 'Yes':
            return False
    return True


def get_available_version():
    """ Get available version printed on the page

    Returns:
        `None` if not available; string with version otherwise
         e.g. ``1.2.2.3``
    """
    if not update_buttons.is_displayed():
        sel.force_navigate("cfg_settings_region_red_hat_updates")
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
        sel.force_navigate("cfg_settings_region_red_hat_updates")
    if appliance_names:
        cells = {'appliance': [name for name in appliance_names]}
        appliances_table.deselect_all()
        appliances_table.select_rows(cells)
    else:
        appliances_table.select_all()


def get_appliance_rows(*appliance_names):
    """ Get appliances as table rows

    Args:
        appliance_names: Names of appliances to get; will get all if empty
    """
    if not update_buttons.is_displayed():
        sel.force_navigate("cfg_settings_region_red_hat_updates")
    if appliance_names:
        rows = list()
        for row in appliances_table.rows():
            if row.appliance.text in appliance_names:
                rows.append(row)
    else:
        rows = appliances_table.rows()
    return rows
