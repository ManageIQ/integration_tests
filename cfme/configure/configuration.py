#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import ui_navigate as nav
import cfme
import cfme.web_ui.menu  # so that menu is already loaded before grafting onto it
from cfme.web_ui import Region, Form, InfoBlock, Tree
import cfme.web_ui.flash as flash
import cfme.fixtures.pytest_selenium as browser
import utils.conf as conf
from utils.update import Updateable
import cfme.web_ui.toolbar as tb
from cfme.web_ui import fill
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.accordion as accordion
from utils.wait import wait_for
from time import sleep


def make_tree_locator(acc_name, root_name):
    return '//span[.="%s"]/../..//table//tr[contains(@title, "%s")]/../..' % (acc_name, root_name)

settings_tree = Tree(make_tree_locator("Settings", "Region"))
access_tree = Tree(make_tree_locator("Access Control", "Region"))
diagnostics_tree = Tree(make_tree_locator("Diagnostics", "Region"))
database_tree = Tree(make_tree_locator("Database", "VMDB"))

info_block = InfoBlock("form")

server_roles = Form(
    fields=[
        ('ems_metrics_coordinator', "//input[@id='server_roles_ems_metrics_coordinator']"),
        ('ems_operations', "//input[@id='server_roles_ems_operations']"),
        ('ems_metrics_collector', "//input[@id='server_roles_ems_metrics_collector']"),
        ('reporting', "//input[@id='server_roles_reporting']"),
        ('ems_metrics_processor', "//input[@id='server_roles_ems_metrics_processor']"),
        ('scheduler', "//input[@id='server_roles_scheduler']"),
        ('smartproxy', "//input[@id='server_roles_smartproxy']"),
        ('database_operations', "//input[@id='server_roles_database_operations']"),
        ('smartstate', "//input[@id='server_roles_smartstate']"),
        ('event', "//input[@id='server_roles_event']"),
        ('user_interface', "//input[@id='server_roles_user_interface']"),
        ('web_services', "//input[@id='server_roles_web_services']"),
        ('ems_inventory', "//input[@id='server_roles_ems_inventory']"),
        ('notifier', "//input[@id='server_roles_notifier']"),
        ('automate', "//input[@id='server_roles_automate']"),
        ('rhn_mirror', "//input[@id='server_roles_rhn_mirror']"),
        ('database_synchronization', "//input[@id='server_roles_database_synchronization']")
    ]
)

server_collect_logs = Form(
    fields=[
        ("type", "//select[@id='log_protocol']"),
        ("uri", "//input[@id='uri']"),
        ("user", "//input[@id='log_userid']"),
        ("password", "//input[@id='log_password']"),
        ("password_verify", "//input[@id='log_verify']"),
    ],
    # locators={
    #     "validate_button": "//div[@id='log_validate_buttons_on']/ul/li/a[@id='val']/img"
    # }
)

ntp_servers = Form(
    fields=[
        ('ntp_server_1', "//input[@id='ntp_server_1']"),
        ('ntp_server_2', "//input[@id='ntp_server_2']"),
        ('ntp_server_3', "//input[@id='ntp_server_3']"),
    ]
)

smtp_settings = Form(
    fields=[
        ('host', "//input[@id='smtp_host']"),
        ('port', "//input[@id='smtp_port']"),
        ('domain', "//input[@id='smtp_domain']"),
        ('start_tls', "//input[@id='smtp_enable_starttls_auto']"),
        ('ssl_verify', "//select[@id='smtp_openssl_verify_mode']"),
        ('auth', "//select[@id='smtp_authentication']"),
        ('username', "//input[@id='smtp_user_name']"),
        ('password', "//input[@id='smtp_password']"),
        ('from_email', "//input[@id='smtp_from']"),
        ('to_email', "//input[@id='smtp_test_to']"),
    ]
)

basic_information = Form(
    fields=[
        ('company_name', "//input[@id='server_company']"),
        ('appliance_name', "//input[@id='server_name']"),
        ('time_zone', "//input[@id='server_timezone']"),
    ]
)


def make_button(button_title):
    return "//div[@id='buttons_on']/ul[@id='form_buttons']/li/img[@title='%s']" % button_title

crud_buttons = Region(
    locators={
        'save_button': make_button("Save Changes"),
        'reset_button': make_button("Reset Changes"),
        'cancel_button': make_button("Cancel"),
    },
    identifying_loc="//div[@id='buttons_on']/ul[@id='form_buttons']",
)


nav.add_branch("configuration",
    dict(
        configuration_settings=[
            lambda: accordion.click("Settings"),
            {
                "cfg_settings_region":
                lambda: settings_tree.click_path("Region: Region"),

                "cfg_settings_defaultzone":
                lambda: settings_tree.click_path("Region: Region", "Zones", "Default Zone"),

                "cfg_settings_schedules":
                lambda: settings_tree.click_path("Region: Region", "Schedules"),

                "cfg_settings_currentserver":
                [
                    lambda: settings_tree.click_path("Region: Region",
                                                     "Zones",
                                                     "Default Zone",
                                                     "(current)"),
                    {
                        "cfg_settings_currentserver_server":
                        lambda: tabs.select_tab("Server"),

                        "cfg_settings_currentserver_auth":
                        lambda: tabs.select_tab("Authentication"),

                        "cfg_settings_currentserver_workers":
                        lambda: tabs.select_tab("Workers"),

                        "cfg_settings_currentserver_database":
                        lambda: tabs.select_tab("Database"),

                        "cfg_settings_currentserver_logos":
                        lambda: tabs.select_tab("Custom Logos"),

                        "cfg_settings_currentserver_maintenance":
                        lambda: tabs.select_tab("Maintenance"),

                        "cfg_settings_currentserver_smartproxy":
                        lambda: tabs.select_tab("SmartProxy"),

                        "cfg_settings_currentserver_advanced":
                        lambda: tabs.select_tab("Advanced")
                    }
                ]
            }
        ],
        configuration_diagnostics=[
            lambda: accordion.click("Diagnostics"),
            {
                "cfg_diagnostics_currentserver":
                [
                    lambda: diagnostics_tree.click_path("CFME Region", "Default Zone", "Server:"),
                    {
                        "cfg_diagnostics_server_summary":
                        lambda: tabs.select_tab("Summary"),

                        "cfg_diagnostics_server_workers":
                        lambda: tabs.select_tab("Workers"),

                        "cfg_diagnostics_server_collect":
                        lambda: tabs.select_tab("Collect Logs"),

                        "cfg_diagnostics_server_cfmelog":
                        lambda: tabs.select_tab("CFME Log"),

                        "cfg_diagnostics_server_auditlog":
                        lambda: tabs.select_tab("Audit Log"),

                        "cfg_diagnostics_server_productionlog":
                        lambda: tabs.select_tab("Production Log"),

                        "cfg_diagnostics_server_utilization":
                        lambda: tabs.select_tab("Utilization"),

                        "cfg_diagnostics_server_timelines":
                        lambda: tabs.select_tab("Timelines"),
                    }
                ],
                "cfg_diagnostics_defaultzone":
                [
                    lambda: diagnostics_tree.click_path("CFME Region", "Default Zone"),
                    {
                        "cfg_diagnostics_zone_roles_by_servers":
                        lambda: tabs.select_tab("Roles by Servers"),

                        "cfg_diagnostics_zone_servers_by_roles":
                        lambda: tabs.select_tab("Servers by Roles"),

                        "cfg_diagnostics_zone_servers":
                        lambda: tabs.select_tab("Servers"),

                        "cfg_diagnostics_zone_collect":
                        lambda: tabs.select_tab("Collect Logs"),

                        "cfg_diagnostics_zone_gap_collect":
                        lambda: tabs.select_tab("C & U Gap Collection"),
                    }
                ],
                "cfg_diagnostics_region":
                [
                    lambda: diagnostics_tree.click_path("CFME Region"),
                    {
                        "cfg_diagnostics_region_zones":
                        lambda: tabs.select_tab("Zones"),

                        "cfg_diagnostics_region_roles_by_servers":
                        lambda: tabs.select_tab("Roles by Servers"),

                        "cfg_diagnostics_region_servers_by_roles":
                        lambda: tabs.select_tab("Servers by Roles"),

                        "cfg_diagnostics_region_servers":
                        lambda: tabs.select_tab("Servers"),

                        "cfg_diagnostics_region_replication":
                        lambda: tabs.select_tab("Replication"),

                        "cfg_diagnostics_region_database":
                        lambda: tabs.select_tab("Database"),

                        "cfg_diagnostics_region_orphaned":
                        lambda: tabs.select_tab("Orphaned Data"),
                    }
                ]
            }
        ],
        configuration_access_control=lambda: accordion.click("Access Control"),
        configuration_database=lambda: accordion.click("Database"),
    )
)


class ServerLogDepot(object):
    """ This class represents the 'Collect logs' for the server.

    """

    class Credentials(Updateable):
        """ This class represents the credentials for log depots.

        """
        p_types = dict(
            ftp="File Transfer Protocol",
            nfs="Network File System",
            smb="Samba"
        )

        def __init__(self, p_type, uri, username=None, password=None):
            assert p_type in self.p_types.keys()
            self.p_type = p_type
            self.uri = uri
            self.username = username
            self.password = password

        def update(self, cancel=False):
            """ Navigate to a correct page, change details and save.

            """
            nav.go_to("cfg_diagnostics_server_collect")
            tb.select("Edit")
            details = {
                "type": self.p_types[self.p_type],
                "uri": self.uri
            }
            if self.p_type != "nfs":
                details["user"] = self.username
                details["password"] = self.password
                details["password_verify"] = self.password
            fill(server_collect_logs, details)
            if not cancel:
                browser.click(crud_buttons.save_button)
            else:
                browser.click(crud_buttons.cancel_button)

        @staticmethod
        def clear(cancel=False):
            """ Navigate to correct page and set <No Depot>.

            """
            nav.go_to("cfg_diagnostics_server_collect")
            tb.select("Edit")
            fill(server_collect_logs, {"type": "<No Depot>"})
            if not cancel:
                browser.click(crud_buttons.save_button)
            else:
                browser.click(crud_buttons.cancel_button)

    @staticmethod
    def _collect(selection):
        """ Initiate and wait for collection to finish. DRY method.

        Args:
            selection: The item in Collect menu ('Collect all logs' or 'Collect current logs')
        """
        nav.go_to("cfg_diagnostics_server_collect")
        tb.select("Collect", selection)
        flash.assert_no_errors()
        sleep(45)   # To prevent premature ending caused by Last Message from last time

        def _check_collection_finished():
            tabs.select_tab("Workers")
            tabs.select_tab("Collect Logs")  # Serve as the refresh
            return "were successfully collected" in info_block.text("Basic Info", "Last Message")
        return wait_for(_check_collection_finished, num_sec=4 * 60)

    @classmethod
    def collect_all(self):
        """ Initiate and wait for collection of all logs to finish.

        """
        return self._collect("Collect all logs")

    @classmethod
    def collect_current(self):
        """ Initiate and wait for collection of the current log to finish.

        """
        return self._collect("Collect current logs")


class BasicInformation(Updateable):
    def __init__(self, company_name=None, appliance_name=None, time_zone=None):
        assert company_name or appliance_name or time_zone, "You must provide at least one param!"
        self.details = {}
        if company_name is not None:
            self.details["company_name"] = company_name
        if appliance_name is not None:
            self.details["appliance_name"] = appliance_name
        if time_zone is not None:
            self.details["time_zone"] = time_zone

    def update(self):
        nav.go_to("cfg_settings_currentserver_server")
        fill(basic_information, self.details)
        browser.click(crud_buttons.save_button)


class SMTPSettings(Updateable):
    def __init__(self,
                 host="localhost",
                 port=25,
                 domain="mydomain.com",
                 start_tls=True,
                 ssl_verify="None",
                 auth="login",
                 username="evmadmin",
                 password="",
                 from_email="cfadmin@cfserver.com",
                 test_email=""):
        self.details = locals()
        del self.details["self"]

    def update(self):
        nav.go_to("cfg_settings_currentserver_server")
        fill(smtp_settings, self.details)
        browser.click(crud_buttons.save_button)


class DatabaseAuthSetting(object):
    """ Another approach

    """

    form = Form(fields=[
        ("timeout_h", "//select[@id='session_timeout_hours']"),
        ("timeout_m", "//select[@id='session_timeout_mins']"),
        ("auth_mode", "//select[@id='authentication_mode']")
    ])

    def _navigate(self):
        nav.go_to("cfg_settings_currentserver_auth")

    def update(self, session_timeout=(1, 0)):
        self._navigate()
        fill(self.form, dict(
            timeout_h=session_timeout[0],
            timeout_m=session_timeout[1],
            auth_mode="Database"
        ))
        browser.click(crud_buttons.save_button)


class AmazonAuthSetting(object):
    """ Another approach

    """

    form = Form(fields=[
        ("timeout_h", "//select[@id='session_timeout_hours']"),
        ("timeout_m", "//select[@id='session_timeout_mins']"),
        ("auth_mode", "//select[@id='authentication_mode']"),
        ("access_key", "//input[@id='authentication_amazon_key']"),
        ("secret_key", "//input[@id='authentication_amazon_secret']"),
        ("get_groups", "//input[@id='amazon_role']"),
    ])

    def __init__(self, access_key, secret_key, get_groups=False):
        self.details = dict(
            access_key=access_key,
            secret_key=secret_key,
            get_groups=get_groups
        )

    def _navigate(self):
        nav.go_to("cfg_settings_currentserver_auth")

    def update(self, session_timeout=(1, 0)):
        self._navigate()
        self.details.update(dict(
            timeout_h=session_timeout[0],
            timeout_m=session_timeout[1],
            auth_mode="Amazon"
        ))
        fill(self.form, self.details)
        browser.click(crud_buttons.save_button)


class LDAPAuthSetting(object):
    """ Another approach

    """

    form = Form(fields=[
        ("timeout_h", "//select[@id='session_timeout_hours']"),
        ("timeout_m", "//select[@id='session_timeout_mins']"),
        ("auth_mode", "//select[@id='authentication_mode']"),
        ("ldaphost_1", "//input[@id='authentication_ldaphost_1']"),
        ("ldaphost_2", "//input[@id='authentication_ldaphost_2']"),
        ("ldaphost_3", "//input[@id='authentication_ldaphost_3']"),
        ("ldapport", "//input[@id='authentication_ldapport']"),
        ("user_type", "//select[@id='authentication_user_type']"),
        ("user_suffix", "//input[@id='authentication_user_suffix']"),
        ("get_groups", "//input[@id='ldap_role']"),
        ("get_direct_groups", "//input[@id='get_direct_groups']"),
        ("follow_referrals", "//input[@id='follow_referrals']"),
        ("base_dn", "//input[@id='authentication_basedn']"),
        ("bind_dn", "//input[@id='authentication_bind_dn']"),
        ("bind_password", "//input[@id='authentication_bind_pwd']"),
    ])

    AUTH_MODE = "LDAP"
    PORT = 389

    def __init__(self,
                 hosts,
                 user_type,
                 user_suffix,
                 base_dn,
                 bind_dn,
                 bind_password,
                 get_groups=False,
                 get_direct_groups=False,
                 follow_referrals=False,
                 ldapport=None):
        ldapport = ldapport or self.PORT
        self.details = locals()
        del self.details["self"]
        del self.details["hosts"]
        assert len(hosts) <= 3, "You can specify only 3 LDAP hosts"
        for i in range(len(hosts)):
            self.details["ldaphost_%d" % (i + 1)] = hosts[i]

    def _navigate(self):
        nav.go_to("cfg_settings_currentserver_auth")

    def update(self, session_timeout=(1, 0)):
        self._navigate()
        self.details.update(dict(
            timeout_h=session_timeout[0],
            timeout_m=session_timeout[1],
            auth_mode=self.AUTH_MODE
        ))
        fill(self.form, self.details)
        browser.click(crud_buttons.save_button)


class LDAPSAuthSetting(LDAPAuthSetting):
    PORT = 636
    AUTH_MODE = "LDAPS"


def set_server_roles(**roles):
    """ Set server roles on Configure / Configuration pages.

    Args:
        **roles: Roles specified as in server_roles Form in this module. Set to True or False
    """
    nav.go_to("cfg_settings_currentserver_server")
    fill(server_roles, roles)
    browser.click(crud_buttons.save_button)


def set_ntp_servers(*servers):
    """ Set NTP servers on Configure / Configuration pages.

    Args:
        *servers: Maximum of 3 hostnames.
    """
    nav.go_to("cfg_settings_currentserver_server")
    assert len(servers) <= 3, "There is place only for 3 servers!"
    fields = {}
    for i in range(len(servers)):
        fields["ntp_server_%d" % (i + 1)] = servers[i]
    fill(ntp_servers, fields)
    browser.click(crud_buttons.save_button)
