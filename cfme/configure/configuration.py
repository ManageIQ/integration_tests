# -*- coding: utf-8 -*-
from functools import partial
from urlparse import urlparse

import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.exceptions import ScheduleNotFound, AuthModeUnknown
from cfme.web_ui import Calendar, Form, Region, Select, Table, Tree, accordion, fill, flash
from cfme.web_ui.menu import nav
from utils.db_queries import get_server_id, get_server_name, get_server_region
from utils.timeutil import parsetime
from utils.update import Updateable
from utils.wait import wait_for, TimedOutError


def make_tree_locator(acc_name, root_name):
    """ Make a specific locator for the tree in accordions.

    Args:
        acc_name: Accordion title
        root_name: Title of the root node of the tree in the accordion.
    """
    return '//span[.="%s"]/../..//table//tr[contains(@title, "%s")]/../..' % (acc_name, root_name)

settings_tree = Tree(make_tree_locator("Settings", "Region"))
access_tree = Tree(make_tree_locator("Access Control", "Region"))
diagnostics_tree = Tree(make_tree_locator("Diagnostics", "Region"))
database_tree = Tree(make_tree_locator("Database", "VMDB"))

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

ntp_servers = Form(
    fields=[
        ('ntp_server_1', "//input[@id='ntp_server_1']"),
        ('ntp_server_2', "//input[@id='ntp_server_2']"),
        ('ntp_server_3', "//input[@id='ntp_server_3']"),
    ]
)

db_configuration = Form(
    fields=[
        ('type', Select("//select[@id='production_dbtype']")),
        ('hostname', "//input[@id='production_host']"),
        ('database', "//input[@id='production_database']"),
        ('username', "//input[@id='production_username']"),
        ('password', "//input[@id='production_password']"),
        ('password_verify', "//input[@id='production_verify']"),
    ]
)


def make_button(button_title):
    """ Precise button factory. Targets only buttons that are visible.

    """
    return "//div[@id='buttons_on']/ul[@id='form_buttons']/li/img[@title='%s']" % button_title

crud_buttons = Region(
    locators={
        'save_button': make_button("Save Changes"),
        'reset_button': make_button("Reset Changes"),
        'cancel_button': make_button("Cancel"),
        'add_button': make_button("Add"),
    },
    identifying_loc="save_button",
)

records_table = Table("//div[@id='records_div']/table[@class='style3']")


def get_server_ctx(server_db=None):
    try:
        cached = get_server_ctx.cached
    except AttributeError:
        cached = dict(ip_addr=None, ctx_data=dict())

    ip_addr = urlparse(sel.base_url()).netloc
    if ip_addr == cached['ip_addr']:
        return cached['ctx_data']

    cached['ip_addr'] = ip_addr
    cached['ctx_data'] = dict(
        region=get_server_region(db=server_db, ip_address=ip_addr),
        server_name=get_server_name(db=server_db, ip_address=ip_addr),
        server_id=get_server_id(db=server_db, ip_address=ip_addr)
    )
    get_server_ctx.cached = cached
    return cached['ctx_data']


nav.add_branch("configuration",
    {
        "configuration_settings":
        [
            lambda _: accordion.click("Settings"),
            {
                "cfg_settings_region":
                [
                    lambda ctx_db: settings_tree.click_path(
                        "Region: Region %d [%d]" % (
                            get_server_ctx(ctx_db)['region'],
                            get_server_ctx(ctx_db)['region']
                        )
                    ),
                    {
                        "cfg_settings_region_details":
                        lambda _: tabs.select_tab("Details"),

                        "cfg_settings_region_cu_collection":
                        lambda _: tabs.select_tab("C & U Collection"),

                        "cfg_settings_region_my_company_categories":
                        lambda _: tabs.select_tab("My Company Categories"),

                        "cfg_settings_region_my_company_tags":
                        lambda _: tabs.select_tab("My Company Tags"),

                        "cfg_settings_region_import_tags":
                        lambda _: tabs.select_tab("Import Tags"),

                        "cfg_settings_region_import":
                        lambda _: tabs.select_tab("Import"),

                        "cfg_settings_region_red_hat_updates":
                        lambda _: tabs.select_tab("Red Hat Updates")
                    }
                ],

                "cfg_settings_defaultzone":
                lambda ctx_db: settings_tree.click_path(
                    "Region: Region %d [%d]" % (
                        get_server_ctx(ctx_db)['region'],
                        get_server_ctx(ctx_db)['region']
                    ),
                    "Zones",
                    "Zone: Default Zone"
                ),

                "cfg_settings_schedules":
                [
                    lambda ctx_db: settings_tree.click_path(
                        "Region: Region %d [%d]" % (
                            get_server_ctx(ctx_db)['region'],
                            get_server_ctx(ctx_db)['region']
                        ),
                        "Schedules"),
                    {
                        "cfg_settings_schedule":
                        [
                            lambda ctx: records_table.click_cell("name", ctx["schedule_name"]),
                            {
                                "cfg_settings_schedule_edit":
                                lambda _: tb.select("Configuration", "Edit this Schedule")
                            }
                        ]
                    }
                ],

                "cfg_settings_currentserver":
                [
                    lambda ctx_db: settings_tree.click_path(
                        "Region: Region %d [%d]" % (
                            get_server_ctx(ctx_db)['region'],
                            get_server_ctx(ctx_db)['region']
                        ),
                        "Zones",
                        "Zone: Default Zone",
                        "Server: %s [%d] (current)" % (
                            get_server_ctx(ctx_db)['server_name'],
                            get_server_ctx(ctx_db)['server_id']
                        )
                    ),
                    {
                        "cfg_settings_currentserver_server":
                        lambda _: tabs.select_tab("Server"),

                        "cfg_settings_currentserver_auth":
                        lambda _: tabs.select_tab("Authentication"),

                        "cfg_settings_currentserver_workers":
                        lambda _: tabs.select_tab("Workers"),

                        "cfg_settings_currentserver_database":
                        lambda _: tabs.select_tab("Database"),

                        "cfg_settings_currentserver_logos":
                        lambda _: tabs.select_tab("Custom Logos"),

                        "cfg_settings_currentserver_maintenance":
                        lambda _: tabs.select_tab("Maintenance"),

                        "cfg_settings_currentserver_smartproxy":
                        lambda _: tabs.select_tab("SmartProxy"),

                        "cfg_settings_currentserver_advanced":
                        lambda _: tabs.select_tab("Advanced")
                    }
                ],
            }
        ],
        "configuration_diagnostics":
        [
            lambda _: accordion.click("Diagnostics"),
            {
                "cfg_diagnostics_currentserver":
                [
                    lambda ctx_db: diagnostics_tree.click_path(
                        "CFME Region: Region %d [%d]" % (
                            get_server_ctx(ctx_db)['region'],
                            get_server_ctx(ctx_db)['region']
                        ),
                        "Zone: Default Zone",
                        "Server: %s [%d] (current)" % (
                            get_server_ctx(ctx_db)['server_name'],
                            get_server_ctx(ctx_db)['server_id']
                        )
                    ),
                    {
                        "cfg_diagnostics_server_summary":
                        lambda _: tabs.select_tab("Summary"),

                        "cfg_diagnostics_server_workers":
                        lambda _: tabs.select_tab("Workers"),

                        "cfg_diagnostics_server_collect":
                        [
                            lambda _: tabs.select_tab("Collect Logs"),
                            {
                                "cfg_diagnostics_server_collect_settings":
                                lambda _: tb.select("Edit")
                            }
                        ],

                        "cfg_diagnostics_server_cfmelog":
                        lambda _: tabs.select_tab("CFME Log"),

                        "cfg_diagnostics_server_auditlog":
                        lambda _: tabs.select_tab("Audit Log"),

                        "cfg_diagnostics_server_productionlog":
                        lambda _: tabs.select_tab("Production Log"),

                        "cfg_diagnostics_server_utilization":
                        lambda _: tabs.select_tab("Utilization"),

                        "cfg_diagnostics_server_timelines":
                        lambda _: tabs.select_tab("Timelines"),
                    }
                ],
                "cfg_diagnostics_defaultzone":
                [
                    lambda ctx_db: diagnostics_tree.click_path(
                        "CFME Region: Region %d [%d]" % (
                            get_server_ctx(ctx_db)['region'],
                            get_server_ctx(ctx_db)['region']
                        ),
                        "Zone: Default Zone"
                    ),
                    {
                        "cfg_diagnostics_zone_roles_by_servers":
                        lambda _: tabs.select_tab("Roles by Servers"),

                        "cfg_diagnostics_zone_servers_by_roles":
                        lambda _: tabs.select_tab("Servers by Roles"),

                        "cfg_diagnostics_zone_servers":
                        lambda _: tabs.select_tab("Servers"),

                        "cfg_diagnostics_zone_collect":
                        lambda _: tabs.select_tab("Collect Logs"),

                        "cfg_diagnostics_zone_gap_collect":
                        lambda _: tabs.select_tab("C & U Gap Collection"),
                    }
                ],
                "cfg_diagnostics_region":
                [
                    lambda ctx_db: diagnostics_tree.click_path(
                        "CFME Region: Region %d [%d]" % (
                            get_server_ctx(ctx_db)['region'],
                            get_server_ctx(ctx_db)['region']
                        )
                    ),
                    {
                        "cfg_diagnostics_region_zones":
                        lambda _: tabs.select_tab("Zones"),

                        "cfg_diagnostics_region_roles_by_servers":
                        lambda _: tabs.select_tab("Roles by Servers"),

                        "cfg_diagnostics_region_servers_by_roles":
                        lambda _: tabs.select_tab("Servers by Roles"),

                        "cfg_diagnostics_region_servers":
                        lambda _: tabs.select_tab("Servers"),

                        "cfg_diagnostics_region_replication":
                        lambda _: tabs.select_tab("Replication"),

                        "cfg_diagnostics_region_database":
                        lambda _: tabs.select_tab("Database"),

                        "cfg_diagnostics_region_orphaned":
                        lambda _: tabs.select_tab("Orphaned Data"),
                    }
                ],
            },
        ],

        "configuration_access_control": lambda _: accordion.click("Access Control"),
        "configuration_database": lambda _: accordion.click("Database"),
    }
)


class ServerLogDepot(object):
    """ This class represents the 'Collect logs' for the server.

    Usage:

        log_credentials = ServerLogDepot.Credentials("nfs", "backup.acme.com")
        log_credentials.update()
        ServerLogDepot.collect_all()
        ServerLogDepot.Credentials.clear()

    """
    elements = Region(
        locators={},
        infoblock_type="form"
    )

    class Credentials(Updateable):
        """ This class represents the credentials for log depots.

        Args:
            p_type: One of ftp, nfs, or smb.
            uri: Hostname/IP address of the machine.
            username: User name used for logging in (ftp, smb only).
            password: Password used for logging in (ftp, smb only).

        Usage:

            log_credentials = ServerLogDepot.Credentials("nfs", "backup.acme.com")
            log_credentials.update()
            log_credentials = ServerLogDepot.Credentials(
                "smb",
                "backup.acme.com",
                username="jdoe",
                password="xyz"
            )
            log_credentials.update()

        """
        p_types = dict(
            ftp="File Transfer Protocol",
            nfs="Network File System",
            smb="Samba"
        )

        server_collect_logs = Form(
            fields=[
                ("type", Select("//select[@id='log_protocol']")),
                ("uri", "//input[@id='uri']"),
                ("user", "//input[@id='log_userid']"),
                ("password", "//input[@id='log_password']"),
                ("password_verify", "//input[@id='log_verify']"),
            ]
        )

        collect_logs_misc = Region(
            locators=dict(
                validate_button="//div[@id='log_validate_buttons_on']/ul/li/a[@id='val']/img"
            ),
            infoblock_type="form"
        )

        def __init__(self, p_type, uri, username=None, password=None):
            assert p_type in self.p_types.keys(), "%s is not allowed as the protocol type!" % p_type
            self.p_type = p_type
            self.uri = uri
            self.username = username
            self.password = password

        def update(self, cancel=False):
            """ Navigate to a correct page, change details and save.

            Args:
                cancel: If set to True, the Cancel button is clicked instead of saving.
            """
            sel.force_navigate("cfg_diagnostics_server_collect_settings")
            details = {
                "type": self.p_types[self.p_type],
                "uri": self.uri
            }
            if self.p_type != "nfs":
                details["user"] = self.username
                details["password"] = self.password
                details["password_verify"] = self.password

            if cancel:
                action = crud_buttons.cancel_button
            else:
                action = crud_buttons.save_button
            fill(
                self.server_collect_logs,
                details,
                action=action
            )

        @classmethod
        def clear(cls, cancel=False):
            """ Navigate to correct page and set <No Depot>.

            Args:
                cancel: If set to True, the Cancel button is clicked instead of saving.
            """
            sel.force_navigate("cfg_diagnostics_server_collect_settings")

            if cancel:
                action = crud_buttons.cancel_button
            else:
                action = crud_buttons.save_button
            fill(
                cls.server_collect_logs,
                {"type": "<No Depot>"},
                action=action
            )

    @classmethod
    def get_last_message(cls):
        """ Returns the Last Message that is displayed in the InfoBlock.

        """
        return cls.elements.infoblock.text("Basic Info", "Last Message")

    @classmethod
    def get_last_collection(cls):
        """ Returns the Last Log Collection that is displayed in the InfoBlock.

        Returns: If it is Never, returns `None`, otherwise :py:class:`utils.timeutil.parsetime`.
        """
        d = cls.elements.infoblock.text("Basic Info", "Last Log Collection")
        return None if d.strip().lower() == "never" else parsetime.from_american_with_utc(d.strip())

    @classmethod
    def _collect(cls, selection, wait_minutes=4):
        """ Initiate and wait for collection to finish. DRY method.

        Args:
            selection: The item in Collect menu ('Collect all logs' or 'Collect current logs')
            wait_minutes: How many minutes should we wait for the collection process to finish?
        """
        sel.force_navigate("cfg_diagnostics_server_collect")
        last_collection = cls.get_last_collection()
        # Initiate the collection
        tb.select("Collect", selection)
        flash.assert_no_errors()

        def _refresh():
            """ The page has no refresh button, so we'll switch between tabs.

            Why this? Selenium's refresh() is way too slow. This is much faster.

            """
            tabs.select_tab("Workers")
            tabs.select_tab("Collect Logs")  # Serve as the refresh
        # Wait for start
        if last_collection is not None:
            # How does this work?
            # The time is updated just after the collection has started
            # If the Text is Never, we will not wait as there is nothing in the last message.
            wait_for(
                lambda: cls.get_last_collection() > last_collection,
                num_sec=90,
                fail_func=_refresh,
                message="wait_for_log_collection_start"
            )
        # Wait for finish
        wait_for(
            lambda: "were successfully collected" in cls.get_last_message(),
            num_sec=wait_minutes * 60,
            fail_func=_refresh,
            message="wait_for_log_collection_finish"
        )

    @classmethod
    def collect_all(cls):
        """ Initiate and wait for collection of all logs to finish.

        """
        cls._collect("Collect all logs")

    @classmethod
    def collect_current(cls):
        """ Initiate and wait for collection of the current log to finish.

        """
        cls._collect("Collect current logs")


class BasicInformation(Updateable):
    """ This class represents the "Basic Info" section of the Configuration page.

    Args:
        company_name: Company name.
        appliance_name: Appliance name.
        time_zone: Time Zone.

    Usage:

        basic_info = BasicInformation(company_name="ACME Inc.")
        basic_info.update()

    """
    basic_information = Form(
        fields=[
            ('company_name', "//input[@id='server_company']"),
            ('appliance_name', "//input[@id='server_name']"),
            ('time_zone', Select("//select[@id='server_timezone']")),
        ]
    )

    def __init__(self, company_name=None, appliance_name=None, time_zone=None):
        assert company_name or appliance_name or time_zone, "You must provide at least one param!"
        self.details = dict(
            company_name=company_name,
            appliance_name=appliance_name,
            time_zone=time_zone
        )

    def update(self):
        """ Navigate to a correct page, change details and save.

        """
        sel.force_navigate("cfg_settings_currentserver_server")
        fill(self.basic_information, self.details, action=crud_buttons.save_button)


class SMTPSettings(Updateable):
    """ SMTP settings on the main page.

    Args:
        host: SMTP Server host name
        port: SMTP Server port
        domain: E-mail domain
        start_tls: Whether use StartTLS
        ssl_verify: SSL Verification
        auth: Authentication type
        username: User name
        password: User password
        from_email: E-mail address to be used as the "From:"
        test_email: Destination of the test-email.

    Usage:

        smtp = SMTPSettings(
            host="smtp.acme.com",
            start_tls=True,
            auth="login",
            username="mailer",
            password="secret"
        )
        smtp.update()

    Todo:
        * send a test-email, if that will be needed.

    """
    smtp_settings = Form(
        fields=[
            ('host', "//input[@id='smtp_host']"),
            ('port', "//input[@id='smtp_port']"),
            ('domain', "//input[@id='smtp_domain']"),
            ('start_tls', "//input[@id='smtp_enable_starttls_auto']"),
            ('ssl_verify', Select("//select[@id='smtp_openssl_verify_mode']")),
            ('auth', Select("//select[@id='smtp_authentication']")),
            ('username', "//input[@id='smtp_user_name']"),
            ('password', "//input[@id='smtp_password']"),
            ('from_email', "//input[@id='smtp_from']"),
            ('to_email', "//input[@id='smtp_test_to']"),
        ]
    )

    def __init__(self,
                 host=None,
                 port=None,
                 domain=None,
                 start_tls=None,
                 ssl_verify=None,
                 auth=None,
                 username=None,
                 password=None,
                 from_email=None,
                 test_email=None):
        self.details = dict(
            host=host,
            port=port,
            domain=domain,
            start_tls=start_tls,
            ssl_verify=ssl_verify,
            auth=auth,
            username=username,
            password=password,
            from_email=from_email,
            test_email=test_email
        )

    def update(self):
        sel.force_navigate("cfg_settings_currentserver_server")
        fill(self.smtp_settings, self.details, action=crud_buttons.save_button)


class DatabaseAuthSetting(object):
    """ Authentication settings for DB internal database.

    Args:
        timeout_h: Timeout in hours
        timeout_m: Timeout in minutes

    Usage:

        dbauth = DatabaseAuthSetting()
        dbauth.update()

    """

    form = Form(fields=[
        ("timeout_h", Select("//select[@id='session_timeout_hours']")),
        ("timeout_m", Select("//select[@id='session_timeout_mins']")),
        ("auth_mode", Select("//select[@id='authentication_mode']"))
    ])

    def __init__(self, timeout_h=None, timeout_m=None):
        self.details = dict(
            timeout_h=timeout_h,
            timeout_m=timeout_m,
            auth_mode="Database"
        )

    def update(self):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, self.details, action=crud_buttons.save_button)


class AmazonAuthSetting(object):
    """ Authentication settings via Amazon.

    Args:
        access_key: Amazon access key
        secret_key: Amazon secret key
        get_groups: Whether to get groups from the auth provider (default `False`)
        timeout_h: Timeout in hours
        timeout_m: Timeout in minutes

    Usage:

        amiauth = AmazonAuthSetting("AJSHDGVJAG", "IUBDIUWQBQW")
        amiauth.update()

    """

    form = Form(fields=[
        ("timeout_h", Select("//select[@id='session_timeout_hours']")),
        ("timeout_m", Select("//select[@id='session_timeout_mins']")),
        ("auth_mode", Select("//select[@id='authentication_mode']")),
        ("access_key", "//input[@id='authentication_amazon_key']"),
        ("secret_key", "//input[@id='authentication_amazon_secret']"),
        ("get_groups", "//input[@id='amazon_role']"),
    ])

    def __init__(self, access_key, secret_key, get_groups=False, timeout_h=None, timeout_m=None):
        self.details = dict(
            access_key=access_key,
            secret_key=secret_key,
            get_groups=get_groups,
            timeout_h=timeout_h,
            timeout_m=timeout_m,
            auth_mode="Amazon"
        )

    def update(self):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, self.details, action=crud_buttons.save_button)


class LDAPAuthSetting(object):
    """ Authentication via LDAP

    Args:
        hosts: List of LDAP servers (max 3).
        user_type: "userprincipalname", "mail", ...
        user_suffix: User suffix.
        base_dn: Base DN.
        bind_dn: Bind DN.
        bind_password: Bind Password.
        get_groups: Get user groups from LDAP.
        get_roles: Get roles from home forest.
        follow_referrals: Follow Referrals.
        port: LDAP connection port.
        timeout_h: Timeout in hours
        timeout_m: Timeout in minutes

    Usage:

        ldapauth = LDAPAuthSetting(
            ["host1", "host2"],
            "mail",
            "user.acme.com"
        )
        ldapauth.update()

    """
    form = Form(fields=[
        ("timeout_h", Select("//select[@id='session_timeout_hours']")),
        ("timeout_m", Select("//select[@id='session_timeout_mins']")),
        ("auth_mode", Select("//select[@id='authentication_mode']")),
        ("ldaphost_1", "//input[@id='authentication_ldaphost_1']"),
        ("ldaphost_2", "//input[@id='authentication_ldaphost_2']"),
        ("ldaphost_3", "//input[@id='authentication_ldaphost_3']"),
        ("port", "//input[@id='authentication_ldapport']"),
        ("user_type", Select("//select[@id='authentication_user_type']")),
        ("user_suffix", "//input[@id='authentication_user_suffix']"),
        ("get_groups", "//input[@id='ldap_role']"),
        ("get_direct_groups", "//input[@id='get_direct_groups']"),
        ("follow_referrals", "//input[@id='follow_referrals']"),
        ("base_dn", "//input[@id='authentication_basedn']"),
        ("bind_dn", "//input[@id='authentication_bind_dn']"),
        ("bind_password", "//input[@id='authentication_bind_pwd']"),
    ])

    AUTH_MODE = "LDAP"

    def __init__(self,
                 hosts,
                 user_type,
                 user_suffix,
                 base_dn=None,
                 bind_dn=None,
                 bind_password=None,
                 get_groups=False,
                 get_roles=False,
                 follow_referrals=False,
                 port=None,
                 timeout_h=None,
                 timeout_m=None,
                 ):
        self.details = dict(
            user_type=sel.ByValue(user_type),
            user_suffix=user_suffix,
            base_dn=base_dn,
            bind_dn=bind_dn,
            bind_password=bind_password,
            get_groups=get_groups,
            get_roles=get_roles,
            follow_referrals=follow_referrals,
            port=port,
            timeout_m=timeout_m,
            timeout_h=timeout_h,
            auth_mode=self.AUTH_MODE
        )
        assert len(hosts) <= 3, "You can specify only 3 LDAP hosts"
        for enum, host in enumerate(hosts):
            self.details["ldaphost_%d" % (enum + 1)] = host

    def update(self):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, self.details, action=crud_buttons.save_button)


class LDAPSAuthSetting(LDAPAuthSetting):
    """ Authentication via LDAPS

    Args:
        hosts: List of LDAPS servers (max 3).
        user_type: "userprincipalname", "mail", ...
        user_suffix: User suffix.
        base_dn: Base DN.
        bind_dn: Bind DN.
        bind_password: Bind Password.
        get_groups: Get user groups from LDAP.
        get_roles: Get roles from home forest.
        follow_referrals: Follow Referrals.
        port: LDAPS connection port.
        timeout_h: Timeout in hours
        timeout_m: Timeout in minutes

    Usage:

        ldapauth = LDAPSAuthSetting(
            ["host1", "host2"],
            "mail",
            "user.acme.com"
        )
        ldapauth.update()

    """
    AUTH_MODE = "LDAPS"


class Schedule(object):
    """ Configure/Configuration/Region/Schedules functionality

    CReate, Update, Delete functionality.
    Todo: Maybe the row handling might go into Table class?

    Args:
        name: Schedule's name.
        description: Schedule description.
        active: Whether the schedule should be active (default `True`)
        action: Action type
        filter_type: Filtering type
        filter_value: If a more specific `filter_type` is selected, here is the place to choose
            hostnames, machines and so ...
        run_type: Once, Hourly, Daily, ...
        run_every: If `run_type` is not Once, then you can specify how often it should be run.
        time_zone: Time zone selection.
        start_date: Specify start date (mm/dd/yyyy or datetime.datetime()).
        start_hour: Starting hour
        start_min: Starting minute.

    Usage:

        schedule = Schedule(
            "My very schedule",
            "Some description here.",
            action="Datastore Analysis",
            filter_type="All Datastores for Host",
            filter_value="datastore.intra.acme.com",
            run_type="Hourly",
            run_every="2 Hours"
        )
        schedule.create()
        schedule.disable()
        schedule.enable()
        schedule.delete()
        # Or
        Schedule.enable_by_names("One schedule", "Other schedule")
        # And so.
    """
    tab = {"Hourly": "timer_hours",
           "Daily": "timer_days",
           "Weekly": "timer_weeks",
           "Monthly": "timer_months"}

    form = Form(fields=[
        ("name", "//input[@id='name']"),
        ("description", "//input[@id='description']"),
        ("active", "//input[@id='enabled']"),
        ("name", "//input[@id='name']"),
        ("action", Select("//select[@id='action_typ']")),
        ("filter_type", Select("//select[@id='filter_typ']")),
        ("filter_value", Select("//select[@id='filter_value']")),
        ("timer_type", Select("//select[@id='timer_typ']")),
        ("timer_hours", Select("//select[@id='timer_hours']")),
        ("timer_days", Select("//select[@id='timer_days']")),
        ("timer_weeks", Select("//select[@id='timer_weekss']")),    # Not a typo!
        ("timer_months", Select("//select[@id='timer_months']")),
        ("time_zone", Select("//select[@id='time_zone']")),
        ("start_date", Calendar("miq_date_1")),
        ("start_hour", Select("//select[@id='start_hour']")),
        ("start_min", Select("//select[@id='start_min']")),
    ])

    def __init__(self,
                 name,
                 description,
                 active=True,
                 action=None,
                 filter_type=None,
                 filter_value=None,
                 run_type="Once",
                 run_every=None,
                 time_zone=None,
                 start_date=None,
                 start_hour=None,
                 start_min=None):
        self.details = dict(
            name=name,
            description=description,
            active=active,
            action=action,
            filter_type=filter_type,
            filter_value=filter_value,
            time_zone=sel.ByValue(time_zone),
            start_date=start_date,
            start_hour=start_hour,
            start_min=start_min,
        )

        if run_type == "Once":
            self.details["timer_type"] = "Once"
        else:
            self.details["timer_type"] = run_type
            self.details[self.tab[run_type]] = run_every

    def create(self, cancel=False):
        """ Create a new schedule from the informations stored in the object.

        Args:
            cancel: Whether to click on the cancel button to interrupt the creation.
        """
        sel.force_navigate("cfg_settings_schedules")
        tb.select("Configuration", "Add a new Schedule")

        if cancel:
            action = crud_buttons.cancel_button
        else:
            action = crud_buttons.add_button
        fill(
            self.form,
            self.details,
            action=action
        )

    def update(self, updates, cancel=False):
        """ Modify an existing schedule with informations from this instance.

        Args:
            updates: Dict with fields to be updated
            cancel: Whether to click on the cancel button to interrupt the editation.

        """
        sel.force_navigate("cfg_settings_schedule_edit",
                           context={"schedule_name": self.details["name"]})
        if cancel:
            action = crud_buttons.cancel_button
        else:
            action = crud_buttons.save_button
        self.details.update(updates)
        fill(
            self.form,
            self.details,
            action=action
        )

    def delete(self, cancel=False):
        """ Delete the schedule represented by this object.

        Calls the class method with the name of the schedule taken out from the object.

        Args:
            cancel: Whether to click on the cancel button in the pop-up.
        """
        self.delete_by_name(self.details["name"], cancel)

    def enable(self):
        """ Enable the schedule via table checkbox and Configuration menu.

        """
        self.enable_by_names(self.details["name"])

    def disable(self):
        """ Enable the schedule via table checkbox and Configuration menu.

        """
        self.disable_by_names(self.details["name"])

    ##
    # CLASS METHODS
    #
    @classmethod
    def delete_by_name(cls, name, cancel=False):
        """ Finds a particular schedule by its name and then deletes it.

        Args:
            name: Name of the schedule.
            cancel: Whether to click on the cancel button in the pop-up.
        """
        sel.force_navigate("cfg_settings_schedule", context={"schedule_name": name})
        tb.select("Configuration", "Delete this Schedule from the Database", invokes_alert=True)
        sel.handle_alert(cancel)

    @classmethod
    def select_by_names(cls, *names):
        """ Select all checkboxes at the schedules with specified names.

        Can select multiple of them.

        Candidate for DRY in Table class.

        Args:
            *names: Arguments with all schedules' names.
        """
        def select_by_name(name):
            for row in records_table.rows():
                if row.name.strip() == name:
                    checkbox = row[0].find_element_by_xpath("//input[@type='checkbox']")
                    if not checkbox.is_selected():
                        sel.click(checkbox)
                    break
            else:
                raise ScheduleNotFound(
                    "Schedule '%s' could not be found for selection!" % name
                )

        sel.force_navigate("cfg_settings_schedules")
        for name in names:
            select_by_name(name)

    @classmethod
    def enable_by_names(cls, *names):
        """ Checks all schedules that are passed with `names` and then enables them via menu.

        Args:
            *names: Names of schedules to enable.
        """
        cls.select_by_names(*names)
        tb.select("Configuration", "Enable the selected Schedules")

    @classmethod
    def disable_by_names(cls, *names):
        """ Checks all schedules that are passed with `names` and then disables them via menu.

        Args:
            *names: Names of schedules to disable.
        """
        cls.select_by_names(*names)
        tb.select("Configuration", "Disable the selected Schedules")


class DatabaseBackupSchedule(Schedule):
    """ Configure/Configuration/Region/Schedules - Database Backup type

    Args:
        name: Schedule name
        description: Schedule description
        active: Whether the schedule should be active (default `True`)
        protocol: One of ``{'Samba', 'Network File System'}``
        run_type: Once, Hourly, Daily, ...
        run_every: If `run_type` is not Once, then you can specify how often it should be run
        time_zone: Time zone selection
        start_date: Specify start date (mm/dd/yyyy or datetime.datetime())
        start_hour: Starting hour
        start_min: Starting minute

    Usage:
        smb_schedule = DatabaseBackupSchedule(
            name="Bi-hourly Samba Database Backup",
            description="Everybody's favorite backup schedule",
            protocol="Samba",
            uri="samba.example.com/share_name",
            username="samba_user",
            password="secret",
            password_verify="secret",
            time_zone="UTC",
            start_date=datetime.datetime.utcnow(),
            run_type="Hourly",
            run_every="2 Hours"
        )
        smb_schedule.create()
        smb_schedule.delete()

        ... or ...

        nfs_schedule = DatabaseBackupSchedule(
            name="One-time NFS Database Backup",
            description="The other backup schedule",
            protocol="Network File System",
            uri="nfs.example.com/path/to/share",
            time_zone="Chihuahua",
            start_date="21/6/2014",
            start_hour="7",
            start_min="45"
        )
        nfs_schedule.create()
        nfs_schedule.delete()

    """
    form = Form(fields=[
        ("name", "//input[@id='name']"),
        ("description", "//input[@id='description']"),
        ("active", "//input[@id='enabled']"),
        ("action", Select("//select[@id='action_typ']")),
        ("log_protocol", Select("//select[@id='log_protocol']")),
        ("uri", "//input[@id='uri']"),
        ("log_userid", "//input[@id='log_userid']"),
        ("log_password", "//input[@id='log_password']"),
        ("log_verify", "//input[@id='log_verify']"),
        ("validate", "//a[@title='Validate the credentials by logging into the Server']"),
        ("timer_type", Select("//select[@id='timer_typ']")),
        ("timer_hours", Select("//select[@id='timer_hours']")),
        ("timer_days", Select("//select[@id='timer_days']")),
        ("timer_weeks", Select("//select[@id='timer_weekss']")),    # Not a typo!
        ("timer_months", Select("//select[@id='timer_months']")),
        ("time_zone", Select("//select[@id='time_zone']")),
        ("start_date", Calendar("miq_date_1")),
        ("start_hour", Select("//select[@id='start_hour']")),
        ("start_min", Select("//select[@id='start_min']"))
    ])

    def __init__(self,
                 name,
                 description,
                 active=True,
                 protocol=None,
                 uri=None,
                 username=None,
                 password=None,
                 password_verify=None,
                 run_type="Once",
                 run_every=None,
                 time_zone=None,
                 start_date=None,
                 start_hour=None,
                 start_min=None):

        assert protocol in {'Samba', 'Network File System'},\
            "Unknown protocol type '{}'".format(protocol)

        if protocol == 'Samba':
            self.details = dict(
                name=name,
                description=description,
                active=active,
                action='Database Backup',
                log_protocol=sel.ByValue(protocol),
                uri=uri,
                log_userid=username,
                log_password=password,
                log_verify=password_verify,
                time_zone=sel.ByValue(time_zone),
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min,
            )
        else:
            self.details = dict(
                name=name,
                description=description,
                active=active,
                action='Database Backup',
                log_protocol=sel.ByValue(protocol),
                uri=uri,
                time_zone=sel.ByValue(time_zone),
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min,
            )

        if run_type == "Once":
            self.details["timer_type"] = "Once"
        else:
            self.details["timer_type"] = run_type
            self.details[self.tab[run_type]] = run_every

    def create(self, cancel=False, samba_validate=False):
        """ Create a new schedule from the informations stored in the object.

        Args:
            cancel: Whether to click on the cancel button to interrupt the creation.
            samba_validate: Samba-only option to click the `Validate` button to check
                            if entered samba credentials are valid or not
        """
        sel.force_navigate("cfg_settings_schedules")
        tb.select("Configuration", "Add a new Schedule")

        fill(self.form, self.details)
        if samba_validate:
            sel.click(self.form.validate)
        if cancel:
            sel.click(crud_buttons.cancel_button)
        else:
            sel.click(crud_buttons.add_button)

    def update(self, updates, cancel=False, samba_validate=False):
        """ Modify an existing schedule with informations from this instance.

        Args:
            updates: Dict with fields to be updated
            cancel: Whether to click on the cancel button to interrupt the editation.
            samba_validate: Samba-only option to click the `Validate` button to check
                            if entered samba credentials are valid or not
        """
        sel.force_navigate("cfg_settings_schedule_edit",
                           context={"schedule_name": self.details["name"]})

        self.details.update(updates)
        fill(self.form, self.details)
        if samba_validate:
            sel.click(self.form.validate)
        if cancel:
            sel.click(crud_buttons.cancel_button)
        else:
            sel.click(crud_buttons.save_button)


def set_server_roles(**roles):
    """ Set server roles on Configure / Configuration pages.

    Args:
        **roles: Roles specified as in server_roles Form in this module. Set to True or False
    """
    sel.force_navigate("cfg_settings_currentserver_server")
    fill(server_roles, roles, action=crud_buttons.save_button)


def get_server_roles():
    """ Get server roles from Configure / Configuration

    Returns: :py:class:`dict` with the roles in the same format as :py:func:`set_server_roles`
        accepts as kwargs.
    """
    sel.force_navigate("cfg_settings_currentserver_server")
    return {name: sel.element(locator).is_selected() for (name, locator) in server_roles.fields}


def set_server_role(role_name, state=True):
    """ Change state of given role only

    Args:
        role_name: Name of the role to set/unset
        state: Enable if `True`, disable otherwise (default `True`)
    """
    roles_to_set = get_server_roles()
    roles_to_set[role_name] = state
    set_server_roles(**roles_to_set)


def set_ntp_servers(*servers):
    """ Set NTP servers on Configure / Configuration pages.

    Args:
        *servers: Maximum of 3 hostnames.
    """
    sel.force_navigate("cfg_settings_currentserver_server")
    assert len(servers) <= 3, "There is place only for 3 servers!"
    fields = {}
    for enum, server in enumerate(servers):
        fields["ntp_server_%d" % (enum + 1)] = server
    fill(ntp_servers, fields, action=crud_buttons.save_button)


def unset_ntp_servers():
    """ Clears the NTP server settings.

    """
    return set_ntp_servers("", "", "")


def set_database_internal():
    """ Set the database as the internal one.

    """
    sel.force_navigate("cfg_settings_currentserver_database")
    fill(
        db_configuration,
        dict(type="Internal Database on this CFME Appliance"),
        action=crud_buttons.save_button
    )


def set_database_external_appliance(hostname):
    """ Set the database as an external from another appliance

    Args:
        hostname: Host name of the another appliance
    """
    sel.force_navigate("cfg_settings_currentserver_database")
    fill(
        db_configuration,
        dict(
            type="External Database on another CFME Appliance",
            hostname=hostname
        ),
        action=crud_buttons.save_button
    )


def set_database_external_postgres(hostname, database, username, password):
    """ Set the database as an external Postgres DB

    Args:
        hostname: Host name of the Postgres server
        database: Database name
        username: User name
        password: User password
    """
    sel.force_navigate("cfg_settings_currentserver_database")
    fill(
        db_configuration,
        dict(
            type="External Postgres Database",
            hostname=hostname,
            database=database,
            username=username,
            password=password,
            password_verify=password
        ),
        action=crud_buttons.save_button
    )


def restart_workers(name, wait_time_min=1):
    """ Restarts workers by their name.

    Args:
        name: Name of the worker. Multiple workers can have the same name. Name is matched with `in`
    Returns: bool whether the restart succeeded.
    """

    table = Table("//div[@id='records_div']/table[@class='style3']")
    sel.force_navigate("cfg_diagnostics_server_workers")

    def get_all_pids(worker_name):
        return {row.pid.text for row in table.rows() if worker_name in row.name.text}

    reload_func = partial(tb.select, "Reload current workers display")

    pids = get_all_pids(name)
    # Initiate the restart
    for pid in pids:
        table.click_cell("pid", pid)
        tb.select("Configuration", "Restart selected worker", invokes_alert=True)
        sel.handle_alert(cancel=False)
        reload_func()

    # Check they have finished
    def _check_all_workers_finished():
        for pid in pids:
            if table.click_cell("pid", pid):    # If could not click, it is no longer present
                return False                    # If clicked, it is still there so unsuccess
        return True

    # Wait for all original workers to be gone
    try:
        wait_for(
            _check_all_workers_finished,
            fail_func=reload_func,
            num_sec=wait_time_min * 60
        )
    except TimedOutError:
        return False

    # And now check whether the same number of workers is back online
    try:
        wait_for(
            lambda: len(pids) == len(get_all_pids(name)),
            fail_func=reload_func,
            num_sec=wait_time_min * 60,
            message="wait_workers_back_online"
        )
        return True
    except TimedOutError:
        return False


def set_auth_mode(mode, **kwargs):
    """ Set up authentication mode

    Args:
        mode: Authentication mode to set up.
        kwargs: A dict of keyword arguments used to initialize one of
                the \*AuthSetting classes - class type is mode-dependent.
    Raises:
        AuthModeUnknown: when the given mode is not valid
    """
    if mode == 'ldap':
        auth_pg = LDAPAuthSetting(**kwargs)
    elif mode == 'ldaps':
        auth_pg = LDAPSAuthSetting(**kwargs)
    elif mode == 'amazon':
        auth_pg = AmazonAuthSetting(**kwargs)
    elif mode == 'database':
        auth_pg = DatabaseAuthSetting(**kwargs)
    else:
        raise AuthModeUnknown("{} is not a valid authentication mode".format(mode))
    auth_pg.update()
