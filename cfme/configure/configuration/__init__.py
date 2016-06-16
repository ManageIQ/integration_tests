# -*- coding: utf-8 -*-
from contextlib import contextmanager
from functools import partial
from cached_property import cached_property
import cfme.fixtures.pytest_selenium as sel
from fixtures.pytest_store import store

import cfme.web_ui.tabstrip as tabs
import cfme.web_ui.toolbar as tb
from cfme.exceptions import ScheduleNotFound, AuthModeUnknown, ZoneNotFound, CandidateNotFound
from cfme.web_ui import (
    AngularSelect, Calendar, CheckboxSelect, CFMECheckbox, DynamicTable, Form, InfoBlock, Input,
    MultiFill, Region, Select, Table, accordion, fill, flash, form_buttons)
from cfme.web_ui.menu import nav
from cfme.web_ui.form_buttons import change_stored_password
from utils.db import cfmedb
from utils.log import logger
from utils.timeutil import parsetime
from utils.update import Updateable
from utils.wait import wait_for, TimedOutError
from utils import version, conf
from utils.pretty import Pretty
from utils.signals import fire, on_signal
from utils import clear_property_cache


@on_signal("server_details_changed")
def invalidate_server_details():
    clear_property_cache(store.current_appliance,
                        'configuration_details', 'zone_description')


access_tree = partial(accordion.tree, "Access Control")
database_tree = partial(accordion.tree, "Database")
settings_tree = partial(accordion.tree, "Settings")
diagnostics_tree = partial(accordion.tree, "Diagnostics")

replication_worker = Form(
    fields=[
        ('database', Input("replication_worker_dbname")),
        ('port', Input("replication_worker_port")),
        ('username', Input("replication_worker_username")),
        ('password', Input("replication_worker_password")),
        ('password_verify', Input("replication_worker_verify")),
        ('host', Input("replication_worker_host")),
    ]
)

replication_process = Region(locators={
    "status": InfoBlock("Replication Process", "Status"),
    "current_backlog": InfoBlock("Replication Process", "Current Backlog"),
})

server_roles = Form(
    fields=[
        ('ems_metrics_coordinator', CFMECheckbox("server_roles_ems_metrics_coordinator")),
        ('ems_operations', CFMECheckbox("server_roles_ems_operations")),
        ('ems_metrics_collector', CFMECheckbox("server_roles_ems_metrics_collector")),
        ('reporting', CFMECheckbox("server_roles_reporting")),
        ('ems_metrics_processor', CFMECheckbox("server_roles_ems_metrics_processor")),
        ('scheduler', CFMECheckbox("server_roles_scheduler")),
        ('smartproxy', CFMECheckbox("server_roles_smartproxy")),
        ('database_operations', CFMECheckbox("server_roles_database_operations")),
        ('smartstate', CFMECheckbox("server_roles_smartstate")),
        ('event', CFMECheckbox("server_roles_event")),
        ('user_interface', CFMECheckbox("server_roles_user_interface")),
        ('web_services', CFMECheckbox("server_roles_web_services")),
        ('ems_inventory', CFMECheckbox("server_roles_ems_inventory")),
        ('notifier', CFMECheckbox("server_roles_notifier")),
        ('automate', CFMECheckbox("server_roles_automate")),
        ('rhn_mirror', CFMECheckbox("server_roles_rhn_mirror")),
        ('database_synchronization', CFMECheckbox("server_roles_database_synchronization")),
        ('git_owner', CFMECheckbox("server_roles_git_owner")),
        ('websocket', CFMECheckbox("server_roles_websocket")),
        # STORAGE OPTIONS
        ("storage_metrics_processor", CFMECheckbox("server_roles_storage_metrics_processor")),
        ("storage_metrics_collector", CFMECheckbox("server_roles_storage_metrics_collector")),
        ("storage_metrics_coordinator", CFMECheckbox("server_roles_storage_metrics_coordinator")),
        ("storage_inventory", CFMECheckbox("server_roles_storage_inventory")),
        ("vmdb_storage_bridge", CFMECheckbox("server_roles_vmdb_storage_bridge")),

    ]
)

ntp_servers = Form(
    fields=[
        ('ntp_server_1', Input("ntp_server_1")),
        ('ntp_server_2', Input("ntp_server_2")),
        ('ntp_server_3', Input("ntp_server_3")),
    ]
)

db_configuration = Form(
    fields=[
        ('type', Select("select#production_dbtype")),
        ('hostname', Input("production_host")),
        ('database', Input("production_database")),
        ('username', Input("production_username")),
        ('password', Input("production_password")),
        ('password_verify', Input("production_verify")),
    ]
)

category_form = Form(
    fields=[
        ('new_tr', "//tr[@id='new_tr']"),
        ('name', Input("name")),
        ('display_name', Input("description")),
        ('description', Input("example_text")),
        ('show_in_console', CFMECheckbox("show")),
        ('single_value', CFMECheckbox("single_value")),
        ('capture_candu', CFMECheckbox("perf_by_tag"))
    ])

tag_form = Form(
    fields=[
        ('category', Select("select#classification_name")),
        ('name', Input("entry[name]")),
        ('display_name', Input("entry[description]")),
        ('add', {
            version.LOWEST: Input("accept"),
            '5.6': '//button[normalize-space(.)="Add"]'
        }),
        ('new', {
            version.LOWEST: "//span[@class='glyphicon glyphicon-plus']",
            '5.6': '//button[normalize-space(.)="Add"]'
        }),
        ('save', '//button[normalize-space(.)="Save"]'),
    ])

zone_form = Form(
    fields=[
        ("name", Input("name")),
        ("description", Input("description")),
        ("smartproxy_ip", Input("proxy_server_ip")),
        ("ntp_server_1", Input("ntp_server_1")),
        ("ntp_server_2", Input("ntp_server_2")),
        ("ntp_server_3", Input("ntp_server_3")),
        ("max_scans", Select("select#max_scans")),
        ("user", Input("userid")),
        ("password", Input("password")),
        ("verify", Input("verify")),
    ])


records_table = Table("//div[@id='records_div']/table")
category_table = Table("//div[@id='settings_co_categories']/table")
classification_table = Table("//div[@id='classification_entries_div']/table")
zones_table = Table("//div[@id='settings_list']/table")


def server_region():
    return store.current_appliance.server_region()


def server_region_pair():
    r = server_region()
    return r, r


def server_name():
    return store.current_appliance.server_name()


def server_id():
    return store.current_appliance.server_id()


def add_tag(cat_name):
    fill(tag_form, {'category': cat_name})
    sel.click(tag_form.new)


def edit_tag(cat_name, tag_name):
    fill(tag_form, {'category': cat_name})
    classification_table.click_cell('name', tag_name)


def server_zone_description():
    return store.current_appliance.zone_description


def server_region_string():
    return "CFME Region: Region {} [{}]".format(*server_region_pair())

nav.add_branch("configuration",
    {
        "cfg_settings_region":
        [
            lambda _: settings_tree(server_region_string()),
            {
                "cfg_settings_region_details":
                lambda _: tabs.select_tab("Details"),

                "cfg_settings_region_cu_collection":
                lambda _: tabs.select_tab("C & U Collection"),

                "cfg_settings_region_my_company_categories":
                [
                    lambda _: tabs.select_tab("My Company Categories"),
                    {
                        "cfg_settings_region_my_company_category_new":
                        lambda _: sel.click(category_form.new_tr),

                        "cfg_settings_region_my_company_category_edit":
                        lambda ctx: category_table.click_cell("name", ctx.category.name)
                    },
                ],

                "cfg_settings_region_my_company_tags":
                [
                    lambda _: tabs.select_tab("My Company Tags"),
                    {
                        "cfg_settings_region_my_company_tag_new":
                        lambda ctx: add_tag(ctx.tag.category.display_name),

                        "cfg_settings_region_my_company_tag_edit":
                        lambda ctx: edit_tag(ctx.tag.category.display_name, ctx.tag.name)
                    },
                ],

                "cfg_settings_region_import_tags":
                lambda _: tabs.select_tab("Import Tags"),

                "cfg_settings_region_import":
                lambda _: tabs.select_tab("Import"),

                "cfg_settings_region_red_hat_updates":
                lambda _: tabs.select_tab("Red Hat Updates")
            }
        ],

        "cfg_analysis_profiles": [
            lambda _: settings_tree(server_region_string(), "Analysis Profiles"),
            {
                "host_analysis_profile_add": lambda _: tb.select(
                    "Configuration", "Add Host Analysis Profile"),
                "vm_analysis_profile_add": lambda _: tb.select(
                    "Configuration", "Add VM Analysis Profile"),
            }
        ],

        "cfg_analysis_profile": [
            lambda ctx:
            settings_tree(server_region_string(), "Analysis Profiles", str(ctx.analysis_profile)),
            {
                "analysis_profile_edit":
                lambda _: tb.select("Configuration", "Edit this Analysis Profile"),
            }
        ],

        "cfg_settings_defaultzone":
        lambda _: settings_tree(
            server_region_string(),
            "Zones",
            "Zone: Default Zone (current)",
        ),

        "cfg_settings_zones":
        [
            lambda _: settings_tree(
                server_region_string(),
                "Zones"),
            {
                "cfg_settings_zone":
                [
                    lambda ctx: zones_table.click_cell("name", ctx["zone_name"]),
                    {
                        "cfg_settings_zone_edit":
                        lambda _: tb.select("Configuration", "Edit this Zone")
                    }
                ]
            }
        ],

        "cfg_settings_schedules":
        [
            lambda _: settings_tree(
                server_region_string(),
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
            lambda _: settings_tree(
                server_region_string(),
                "Zones",
                "Zone: {} (current)".format(server_zone_description()),
                "Server: {} [{}] (current)".format(server_name(), server_id())
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
        "cfg_diagnostics_currentserver":
        [
            lambda _: diagnostics_tree(
                server_region_string(),
                "Zone: Default Zone (current)",
                "Server: {} [{}] (current)".format(server_name(), server_id())
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
            lambda _: diagnostics_tree(
                server_region_string(),
                "Zone: Default Zone (current)",
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
            lambda _: diagnostics_tree(server_region_string()),
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

        "configuration_access_control": lambda _: accordion.click("Access Control"),
        "configuration_database": lambda _: accordion.click("Database"),
    }
)


class AnalysisProfile(Pretty, Updateable):
    """Analysis profiles. Do not use this class but the derived one.

    Example:

        .. code-block:: python

            p = VMAnalysisProfile(name, description)
            p.files = [
                "/somefile",
                {"Name": "/some/anotherfile", "Collect Contents?": True}
            ]
            p.categories = ["check_system"]
            p.create()
            p.delete()

    """
    CREATE_LOC = None
    pretty_attrs = "name", "description", "files", "events"

    form = tabs.TabStripForm(
        fields=[
            ("name", "input#name"),
            ("description", "input#description")],
        tab_fields={
            "Category": [
                ("categories", CheckboxSelect({
                    version.LOWEST: "table#formtest",
                    "5.5":
                    "//h3[normalize-space(.)='Category Selection']/.."
                    "//div[contains(@class, 'col-md-8')]"})),
            ],
            "File": [
                ("files", DynamicTable(
                    "//div[@id='file']/fieldset/table", default_row_item="Name")),
            ],
            "Registry": [
                ("registry", DynamicTable("//div[@id='registry']/fieldset/table")),
            ],
            "Event Log": [
                ("events", DynamicTable("//div[@id='event_log']/fieldset/table")),
            ],
        })

    def __init__(self, name, description, files=None, events=None, categories=None, registry=None):
        self.name = name
        self.description = description
        self.files = files
        self.events = events
        self.categories = categories
        self.registry = registry

    def create(self):
        sel.force_navigate(self.CREATE_LOC)
        fill(self.form, self, action=form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates=None):
        sel.force_navigate("analysis_profile_edit", context={"analysis_profile": self})
        if updates is None:
            fill(self.form, self, action=form_buttons.save)
        else:
            fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self):
        sel.force_navigate("cfg_analysis_profile", context={"analysis_profile": self})
        tb.select("Configuration", "Delete this Analysis Profile from the VMDB", invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()

    def copy(self, name=None):
        if not name:
            name = self.name + "copy"
        sel.force_navigate("cfg_analysis_profile", context={"analysis_profile": self})
        tb.select('Configuration', 'Copy this selected Analysis Profile')
        new_profile = AnalysisProfile(name=name, description=self.description, files=self.files)
        fill(self.form, {'name': new_profile.name},
             action=form_buttons.add)
        flash.assert_success_message('Analysis Profile "{}" was saved'.format(new_profile.name))
        return new_profile

    @property
    def exists(self):
        try:
            sel.force_navigate("cfg_analysis_profile", context={"analysis_profile": self})
        except CandidateNotFound:
            return False
        else:
            return True

    def __str__(self):
        return self.name

    def __enter__(self):
        self.create()

    def __exit__(self, type, value, traceback):
        self.delete()


class HostAnalysisProfile(AnalysisProfile):
    CREATE_LOC = "host_analysis_profile_add"


class VMAnalysisProfile(AnalysisProfile):
    CREATE_LOC = "vm_analysis_profile_add"


class ServerLogDepot(Pretty):
    """ This class represents the 'Collect logs' for the server.

    Usage:

        log_credentials = ServerLogDepot.Credentials("nfs", "backup.acme.com")
        log_credentials.update()
        ServerLogDepot.collect_all()
        ServerLogDepot.Credentials.clear()

    """
    elements = Region(
        locators={
            "last_message": InfoBlock("Basic Info", "Last Message"),
            "last_log_collection": InfoBlock("Basic Info", "Last Log Collection"),
        },
    )

    class Credentials(Updateable, Pretty):
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
                "foobar",
                "backup.acme.com",
                username="jdoe",
                password="xyz",
            )
            log_credentials.update()

        """
        pretty_attrs = ['p_type', 'name', 'uri', 'username', 'password']

        server_collect_logs = Form(
            fields=[
                ("type", {
                    version.LOWEST: Select("select#log_protocol"),
                    '5.5': AngularSelect('log_protocol')}),
                ("name", {
                    version.LOWEST: None,
                    "5.4": Input("depot_name")}),
                ("uri", Input("uri")),
                ("user", Input("log_userid")),
                ("password", MultiFill(Input("log_password"), Input("log_verify"))),
            ]
        )

        validate = form_buttons.FormButton("Validate the credentials by logging into the Server")
        # add FormButton because of inconsistency in attributes for Save buttons in cfme
        save_button = {
            version.LOWEST: form_buttons.save,
            "5.4": form_buttons.angular_save,
            "5.6": form_buttons.FormButton("Save Changes", ng_click="btnClick()")
        }

        def __init__(self, p_type, name, uri, username=None, password=None):
            assert p_type in self.p_types.keys(), "{} is not allowed as the protocol type!".format(
                p_type)
            self.p_type = p_type
            self.uri = uri
            self.username = username
            self.password = password
            self.name = name

        @cached_property
        def p_types(self):
            return version.pick({
                version.LOWEST: dict(
                    anon_ftp="Anonymous FTP",
                    ftp="FTP",
                    nfs="NFS",
                    smb="Samba",
                    dropbox="Red Hat Dropbox",
                ),
                "5.5": dict(
                    anon_ftp=sel.ByValue("Anonymous FTP"),
                    ftp=sel.ByValue("FTP"),
                    nfs=sel.ByValue("NFS"),
                    smb=sel.ByValue("Samba"),
                    dropbox=sel.ByValue("Red Hat Dropbox")
                )
            })

        def update(self, validate=True, cancel=False):
            """ Navigate to a correct page, change details and save.

            Args:
                validate: Whether validate the credentials (not for NFS)
                cancel: If set to True, the Cancel button is clicked instead of saving.
            """
            sel.force_navigate("cfg_diagnostics_server_collect_settings")
            details = {
                "type": sel.ByValue(self.p_types[self.p_type]),
                "name": self.name,
                "uri": self.uri,
            }
            if self.p_type not in {"nfs", "anon_ftp"}:
                change_stored_password()
                details["user"] = self.username
                details["password"] = self.password

            fill(
                self.server_collect_logs,
                details
            )
            if validate and self.p_type not in {"nfs", "anon_ftp", "dropbox"}:
                sel.click(self.validate)
                flash.assert_no_errors()

            if cancel:
                sel.click(form_buttons.cancel)
                flash.assert_message_match("Edit Log Depot settings was cancelled by the user")
                flash.assert_no_errors()
            else:
                sel.click(self.save_button)
                flash.assert_message_match("Log Depot Settings were saved")
                flash.assert_no_errors()

        @classmethod
        def clear(cls, cancel=False):
            """ Navigate to correct page and set <No Depot>.

            Args:
                cancel: If set to True, the Cancel button is clicked instead of saving.
            """
            sel.force_navigate("cfg_diagnostics_server_collect_settings")
            sel.wait_for_element(cls.server_collect_logs.type)
            sel.wait_for_ajax()
            if cls.server_collect_logs.type.first_selected_option_text == "<No Depot>":
                # Nothing to do here
                sel.click(form_buttons.cancel)
            else:
                fill(
                    cls.server_collect_logs,
                    {"type": "<No Depot>"},
                    action=form_buttons.cancel if cancel else cls.save_button
                )

    @classmethod
    def get_last_message(cls):
        """ Returns the Last Message that is displayed in the InfoBlock.

        """
        return cls.elements.last_message.text

    @classmethod
    def get_last_collection(cls):
        """ Returns the Last Log Collection that is displayed in the InfoBlock.

        Returns: If it is Never, returns `None`, otherwise :py:class:`utils.timeutil.parsetime`.
        """
        d = cls.elements.last_log_collection.text
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


class BasicInformation(Updateable, Pretty):
    """ This class represents the "Basic Info" section of the Configuration page.

    Args:
        company_name: Company name.
        appliance_name: Appliance name.
        appliance_zone: Appliance Zone.
        time_zone: Time Zone.

    Usage:

        basic_info = BasicInformation(company_name="ACME Inc.")
        basic_info.update()

    """
    basic_information = Form(
        fields=[
            ('company_name', Input("server_company")),
            ('appliance_name', Input("server_name")),
            ('appliance_zone', Select("select#server_zone")),
            ('time_zone', Select("select#server_timezone")),
        ]
    )
    pretty_attrs = ['company_name', 'appliance_name', 'appliance_zone', 'time_zone']

    def __init__(self, company_name=None, appliance_name=None, appliance_zone=None, time_zone=None):
        assert (company_name or appliance_name or appliance_zone or time_zone), \
            "You must provide at least one param!"
        self.details = dict(
            company_name=company_name,
            appliance_name=appliance_name,
            appliance_zone=appliance_zone,
            time_zone=time_zone
        )

    def update(self):
        """ Navigate to a correct page, change details and save.

        """
        sel.force_navigate("cfg_settings_currentserver_server")
        fill(self.basic_information, self.details)
        sel.click(form_buttons.save)
        # TODO: Maybe make a cascaded delete on lazycache?
        fire('server_details_changed')


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

    Note: TODO: send a test-email, if that will be needed.

    """
    smtp_settings = Form(
        fields=[
            ('host', Input("smtp_host")),
            ('port', Input("smtp_port")),
            ('domain', Input("smtp_domain")),
            ('start_tls', Input("smtp_enable_starttls_auto")),
            ('ssl_verify', Select("select#smtp_openssl_verify_mode")),
            ('auth', Select("select#smtp_authentication")),
            ('username', Input("smtp_user_name")),
            ('password', Input("smtp_password")),
            ('from_email', Input("smtp_from")),
            ('to_email', Input("smtp_test_to")),
        ]
    )

    buttons = Region(
        locators=dict(
            test="|".join([
                "//img[@alt='Send test email']",
                "//button[@alt='Send test email']",
                "//a[@title='Send test email']",
            ])
        )
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
        fill(self.smtp_settings, self.details, action=form_buttons.save)

    @classmethod
    def send_test_email(self, to_address):
        """ Send a testing e-mail on specified address. Needs configured SMTP.

        Args:
            to_address: Destination address.
        """
        sel.force_navigate("cfg_settings_currentserver_server")
        fill(self.smtp_settings, dict(to_email=to_address), action=self.buttons.test)


class AuthSetting(Updateable, Pretty):
    form = Form(fields=[
        ("timeout_h", Select("select#session_timeout_hours")),
        ("timeout_m", Select("select#session_timeout_mins")),
    ])

    @classmethod
    def set_session_timeout(cls, hours=None, minutes=None):
        """Sets the session timeout of the appliance."""
        sel.force_navigate("cfg_settings_currentserver_auth")
        logger.info(
            "Setting authentication timeout to %s hours and %s minutes.", hours, minutes)
        fill(cls.form, {"timeout_h": hours, "timeout_m": minutes}, action=form_buttons.save)
        flash.assert_no_errors()
        flash.assert_message_contain("Authentication settings saved")


class DatabaseAuthSetting(AuthSetting):
    """ Authentication settings for DB internal database.

    Args:
        timeout_h: Timeout in hours
        timeout_m: Timeout in minutes

    Usage:

        dbauth = DatabaseAuthSetting()
        dbauth.update()

    """

    form = Form(fields=[
        ("timeout_h", Select("select#session_timeout_hours")),
        ("timeout_m", Select("select#session_timeout_mins")),
        ("auth_mode", Select("select#authentication_mode"))
    ])
    pretty_attrs = ['timeout_h', 'timeout_m']

    def __init__(self, timeout_h=None, timeout_m=None):
        self.timeout_h = timeout_h
        self.timeout_m = timeout_m
        self.auth_mode = "Database"

    def update(self, updates=None):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, updates if updates is not None else self, action=form_buttons.save)


class ExternalAuthSetting(AuthSetting):
    """ Authentication settings for authentication via httpd.

    Args:
        timeout_h: Timeout in hours
        timeout_m: Timeout in minutes
        get_groups: Get user groups from external auth source.

    Usage:

        dbauth = ExternalAuthSetting(get_groups=True)
        dbauth.update()

    """

    form = Form(fields=[
        ("timeout_h", Select("select#session_timeout_hours")),
        ("timeout_m", Select("select#session_timeout_mins")),
        ("auth_mode", Select("select#authentication_mode")),
        ("get_groups", Input("httpd_role")),
    ])
    pretty_attrs = ['timeout_h', 'timeout_m', 'get_groups']

    def __init__(self, get_groups=False, timeout_h="1", timeout_m="0"):
        self.timeout_h = timeout_h,
        self.timeout_m = timeout_m,
        self.auth_mode = "External (httpd)"
        self.get_groups = get_groups

    def setup(self):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, self, action=form_buttons.save)

    def update(self, updates=None):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, updates if updates is not None else self, action=form_buttons.save)


class AmazonAuthSetting(AuthSetting):
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
        ("timeout_h", Select("select#session_timeout_hours")),
        ("timeout_m", Select("select#session_timeout_mins")),
        ("auth_mode", Select("select#authentication_mode")),
        ("access_key", Input("authentication_amazon_key")),
        ("secret_key", Input("authentication_amazon_secret")),
        ("get_groups", Input("amazon_role")),
    ])
    pretty_attrs = ['access_key', 'secret_key', 'get_groups', 'timeout_h', 'timeout_m']

    def __init__(self, access_key, secret_key, get_groups=False, timeout_h=None, timeout_m=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.get_groups = get_groups
        self.timeout_h = timeout_h
        self.timeout_m = timeout_m
        self.auth_mode = "Amazon"

    def update(self, updates=None):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, updates if updates is not None else self, action=form_buttons.save)


class LDAPAuthSetting(AuthSetting):
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
        ("timeout_h", Select("select#session_timeout_hours")),
        ("timeout_m", Select("select#session_timeout_mins")),
        ("auth_mode", Select("select#authentication_mode")),
        ("ldaphost_1", Input("authentication_ldaphost_1")),
        ("ldaphost_2", Input("authentication_ldaphost_2")),
        ("ldaphost_3", Input("authentication_ldaphost_3")),
        ("port", Input("authentication_ldapport")),
        ("user_type", {
            version.LOWEST: Select("select#authentication_user_type"),
            "5.5": AngularSelect("authentication_user_type")}),
        ("user_suffix", Input("authentication_user_suffix")),
        ("get_groups", Input("ldap_role")),
        ("get_roles", Input("get_direct_groups")),
        ("follow_referrals", Input("follow_referrals")),
        ("base_dn", Input("authentication_basedn")),
        ("bind_dn", Input("authentication_bind_dn")),
        ("bind_password", Input("authentication_bind_pwd")),
    ])

    AUTH_MODE = "LDAP"
    pretty_attrs = ['hosts', 'user_type', 'user_suffix', 'base_dn', 'bind_dn', 'bind_password']

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
        self.user_type = sel.ByValue(user_type)
        self.user_suffix = user_suffix
        self.base_dn = base_dn
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.get_groups = get_groups
        self.get_roles = get_roles
        self.follow_referrals = follow_referrals
        self.port = port
        self.timeout_h = timeout_h
        self.timeout_m = timeout_m
        self.auth_mode = self.AUTH_MODE
        self.ldaphost_1 = None
        self.ldaphost_2 = None
        self.ldaphost_3 = None
        assert len(hosts) <= 3, "You can specify only 3 LDAP hosts"
        for enum, host in enumerate(hosts):
            setattr(self, "ldaphost_{}".format(enum + 1), host)

    def update(self, updates=None):
        sel.force_navigate("cfg_settings_currentserver_auth")
        fill(self.form, updates if updates is not None else self, action=form_buttons.save)


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


class Schedule(Pretty):
    """ Configure/Configuration/Region/Schedules functionality

    CReate, Update, Delete functionality.

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

    Note: TODO: Maybe the row handling might go into Table class?

    """
    tab = {"Hourly": "timer_hours",
           "Daily": "timer_days",
           "Weekly": "timer_weeks",
           "Monthly": "timer_months"}

    form = Form(fields=[
        ("name", Input("name")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("name", Input("name")),
        ("action", {
            version.LOWEST: Select("select#action_typ"),
            '5.5': AngularSelect('action_typ')}),
        ("filter_type", {
            version.LOWEST: Select("select#filter_typ"),
            '5.5': AngularSelect('filter_typ')}),
        ("filter_value", {
            version.LOWEST: Select("select#filter_value"),
            '5.5': AngularSelect('filter_value')}),
        ("timer_type", {
            version.LOWEST: Select("select#timer_typ"),
            '5.5': AngularSelect('timer_typ')}),
        ("timer_hours", Select("select#timer_hours")),
        ("timer_days", Select("select#timer_days")),
        ("timer_weeks", Select("select#timer_weekss")),    # Not a typo!
        ("timer_months", Select("select#timer_months")),
        ("timer_value", AngularSelect('timer_value'), {"appeared_in": "5.5"}),
        ("time_zone", {
            version.LOWEST: Select("select#time_zone"),
            '5.5': AngularSelect('time_zone')}),
        ("start_date", Calendar("miq_angular_date_1")),
        ("start_hour", {
            version.LOWEST: Select("select#start_hour"),
            '5.5': AngularSelect('start_hour')}),
        ("start_min", {
            version.LOWEST: Select("select#start_min"),
            '5.5': AngularSelect('start_min')}),
    ])

    pretty_attrs = ['name', 'description', 'run_type', 'run_every',
                    'start_date', 'start_hour', 'start_min']

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
            field = version.pick({
                version.LOWEST: self.tab[run_type],
                '5.5': 'timer_value'})
            self.details["timer_type"] = run_type
            self.details[field] = run_every

    def create(self, cancel=False):
        """ Create a new schedule from the informations stored in the object.

        Args:
            cancel: Whether to click on the cancel button to interrupt the creation.
        """
        sel.force_navigate("cfg_settings_schedules")
        tb.select("Configuration", "Add a new Schedule")

        if cancel:
            action = form_buttons.cancel
        else:
            action = form_buttons.add
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
            action = form_buttons.cancel
        else:
            action = form_buttons.save
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
                    "Schedule '{}' could not be found for selection!".format(name)
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
        ("name", Input("name")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("action", {
            version.LOWEST: Select("select#action_typ"),
            '5.5': AngularSelect('action_typ')}),
        ("log_protocol", {
            version.LOWEST: Select("select#log_protocol"),
            '5.5': AngularSelect('log_protocol')}),
        ("depot_name", Input("depot_name")),
        ("uri", Input("uri")),
        ("log_userid", Input("log_userid")),
        ("log_password", Input("log_password")),
        ("log_verify", Input("log_verify")),
        ("timer_type", {
            version.LOWEST: Select("select#timer_typ"),
            '5.5': AngularSelect('timer_typ')}),
        ("timer_hours", Select("select#timer_hours")),
        ("timer_days", Select("select#timer_days")),
        ("timer_weeks", Select("select#timer_weekss")),    # Not a typo!
        ("timer_months", Select("select#timer_months")),
        ("timer_value", AngularSelect('timer_value'), {"appeared_in": "5.5"}),
        ("time_zone", {
            version.LOWEST: Select("select#time_zone"),
            '5.5': AngularSelect('time_zone')}),
        ("start_date", {
            '5.4': Calendar("miq_angular_date_1"),
            '5.5': Calendar("start_date")}),
        ("start_hour", {
            version.LOWEST: Select("select#start_hour"),
            '5.5': AngularSelect('start_hour')}),
        ("start_min", {
            version.LOWEST: Select("select#start_min"),
            '5.5': AngularSelect('start_min')}),
    ])

    def __init__(self,
                 name,
                 description,
                 active=True,
                 protocol=None,
                 depot_name=None,
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
                depot_name=depot_name,
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
                depot_name=depot_name,
                uri=uri,
                time_zone=sel.ByValue(time_zone),
                start_date=start_date,
                start_hour=start_hour,
                start_min=start_min,
            )

        if run_type == "Once":
            self.details["timer_type"] = "Once"
        else:
            field = version.pick({
                version.LOWEST: self.tab[run_type],
                '5.5': 'timer_value'})
            self.details["timer_type"] = run_type
            self.details[field] = run_every

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
            sel.click(form_buttons.validate)
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.add()

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
            sel.click(form_buttons.validate)
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.save()

    @property
    def last_date(self):
        sel.force_navigate("cfg_settings_schedules")
        name = self.details["name"]
        row = records_table.find_row("Name", name)
        return row[6].text


class Zone(Pretty):
    """ Configure/Configuration/Region/Zones functionality

    Create/Read/Update/Delete functionality.
    """
    pretty_attrs = ['name', 'description', 'smartproxy_ip', 'ntp_server_1',
                    'ntp_server_2', 'ntp_server_3', 'max_scans', 'user', 'password', 'verify']

    def __init__(self,
                 name=None,
                 description=None,
                 smartproxy_ip=None,
                 ntp_server_1=None,
                 ntp_server_2=None,
                 ntp_server_3=None,
                 max_scans=None,
                 user=None,
                 password=None,
                 verify=None):
        self.name = name
        self.description = description
        self.smartproxy_ip = smartproxy_ip
        self.ntp_server_1 = ntp_server_1
        self.ntp_server_2 = ntp_server_2
        self.ntp_server_3 = ntp_server_3
        self.max_scans = sel.ByValue(max_scans)
        self.user = user
        self.password = password
        self.verify = verify

    def _form_mapping(self, create=None, **kwargs):
        return {
            'name': create and kwargs.get('name'),
            'description': kwargs.get('description'),
            'smartproxy_ip': kwargs.get('smartproxy_ip'),
            'ntp_server_1': kwargs.get('ntp_server_1'),
            'ntp_server_2': kwargs.get('ntp_server_2'),
            'ntp_server_3': kwargs.get('ntp_server_3'),
            'max_scans': kwargs.get('max_scans'),
            'user': kwargs.get('user'),
            'password': kwargs.get('password'),
            'verify': kwargs.get('verify')
        }

    def create(self, cancel=False):
        """ Create a new Zone from the information stored in the object.

        Args:
            cancel: Whether to click on the cancel button to interrupt the creation.
        """
        sel.force_navigate("cfg_settings_zones")
        tb.select("Configuration", "Add a new Zone")
        if self.name is not None:
            try:
                sel.execute_script(
                    "$j.ajax({type: 'POST', url: '/ops/zone_field_changed/new?name=%s',"
                    " data: {'name':'%s'}})" % (self.name, self.name))
            except sel.WebDriverException:
                logger.info("Ignoring workaround for zone description filling")
        if self.description is not None:
            try:
                sel.execute_script(
                    "$j.ajax({type: 'POST', url: '/ops/zone_field_changed/new?description=%s',"
                    " data: {'description':'%s'}})" % (self.description,
                    self.description))
            except sel.WebDriverException:
                logger.info("Ignoring workaround for zone description filling")
        fill(
            zone_form,
            self._form_mapping(True, **self.__dict__))
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.add()
            flash.assert_message_match('Zone "{}" was added'.format(self.name))

    def update(self, updates, cancel=False):
        """ Modify an existing zone with information from this instance.

        Args:
            updates: Dict with fields to be updated
            cancel: Whether to click on the cancel button to interrupt the edit.

        """
        # sel.force_navigate("cfg_settings_zone_edit",
        #    context={"zone_name": self.name})
        self.go_to_by_description(self.description)
        tb.select("Configuration", "Edit this Zone")
        fill(zone_form, self._form_mapping(**updates))
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.save()
            flash.assert_message_match('Zone "{}" was saved'.format(self.name))

    def delete(self, cancel=False):
        """ Delete the Zone represented by this object.

        Args:
            cancel: Whether to click on the cancel button in the pop-up.
        """
        self.go_to_by_description(self.description)
        tb.select("Configuration", "Delete this Zone", invokes_alert=True)
        sel.handle_alert(cancel)
        if not cancel:
            flash.assert_message_match('Zone "{}": Delete successful'.format(self.name))

    @classmethod
    def go_to_by_description(cls, description):
        """ Finds and navigates to a particular Zone by its description.

        This method looks for a Zone with the provided description. If it
        finds one (and only one) Zone with that description, it navigates to it.
        Otherwise, it raises an Exception.

        Args:
            description: description of the Zone.

        Raises:
            ZoneNotFound: If no single Zone is found with the specified description.
        """
        # TODO Stop using this method as a workaround once Zones can be located by name in the UI.
        sel.force_navigate("cfg_settings_zones")
        try:
            zones_table.click_row_by_cells({1: description}, partial_check=True)
        except:
            raise ZoneNotFound("No unique Zones with the description '{}'".format(description))

    @property
    def exists(self):
        sel.force_navigate("cfg_settings_zones")
        table = Table(zones_table)
        if table.find_cell(1, "Zone: {}".format(self.description)):
            return True
        elif table.find_cell(1, "Zone : {}".format(self.description)):  # Another possibility
            return True
        else:
            return False


class Category(Pretty):
    pretty_attrs = ['name', 'display_name', 'description', 'show_in_console',
                    'single_value', 'capture_candu']

    def __init__(self, name=None, display_name=None, description=None, show_in_console=True,
                 single_value=True, capture_candu=False):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.show_in_console = show_in_console
        self.single_value = single_value
        self.capture_candu = capture_candu

    def _form_mapping(self, create=None, **kwargs):
        return {
            'name': kwargs.get('name'),
            'display_name': kwargs.get('display_name'),
            'description': kwargs.get('description'),
            'show_in_console': kwargs.get('show_in_console'),
            'single_value': kwargs.get('single_value'),
            'capture_candu': kwargs.get('capture_candu'),
        }

    def create(self, cancel=False):
        sel.force_navigate("cfg_settings_region_my_company_category_new")
        fill(category_form, self._form_mapping(True, **self.__dict__))
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.add()
            flash.assert_success_message('Category "{}" was added'.format(self.display_name))

    def update(self, updates, cancel=False):
        sel.force_navigate("cfg_settings_region_my_company_category_edit",
                           context={"category": self})
        fill(category_form, self._form_mapping(**updates))
        if cancel:
            form_buttons.cancel()
        else:
            form_buttons.save()
            flash.assert_success_message('Category "{}" was saved'.format(self.name))

    def delete(self, cancel=True):
        """
        """
        if not cancel:
            sel.force_navigate("cfg_settings_region_my_company_categories")
            row = category_table.find_row_by_cells({'name': self.name})
            del_btn_fn = version.pick({
                version.LOWEST: lambda: row[0],
                '5.6': lambda: row.actions
            })
            sel.click(del_btn_fn(), wait_ajax=False)
            sel.handle_alert()
            flash.assert_success_message('Category "{}": Delete successful'.format(self.name))


class Tag(Pretty):
    pretty_attrs = ['name', 'display_name', 'category']

    def __init__(self, name=None, display_name=None, category=None):
        self.name = name
        self.display_name = display_name
        self.category = category

    def _form_mapping(self, create=None, **kwargs):
        return {
            'name': kwargs.get('name'),
            'display_name': kwargs.get('display_name'),
        }

    def create(self):
        sel.force_navigate("cfg_settings_region_my_company_tag_new", context={"tag": self})
        fill(tag_form, self._form_mapping(True, **self.__dict__), action=tag_form.add)

    def update(self, updates):
        sel.force_navigate("cfg_settings_region_my_company_tag_edit",
                           context={"tag": self})
        update_action = version.pick({
            version.LOWEST: tag_form.add,
            '5.6': tag_form.save
        })
        fill(tag_form, self._form_mapping(**updates), action=update_action)

    def delete(self, cancel=True):
        """
        """
        if not cancel:
            sel.force_navigate("cfg_settings_region_my_company_tags")
            fill(tag_form, {'category': self.category.display_name})
            row = classification_table.find_row_by_cells({'name': self.name})
            del_btn_fn = version.pick({
                version.LOWEST: lambda: row[0],
                '5.6': lambda: row.actions
            })
            sel.click(del_btn_fn(), wait_ajax=False)
            sel.handle_alert()


def set_server_roles(**roles):
    """ Set server roles on Configure / Configuration pages.

    Args:
        **roles: Roles specified as in server_roles Form in this module. Set to True or False
    """
    if get_server_roles() == roles:
        logger.debug(' Roles already match, returning...')
        return
    sel.force_navigate("cfg_settings_currentserver_server")
    fill(server_roles, roles, action=form_buttons.save)


def get_server_roles(navigate=True, db=True):
    """ Get server roles from Configure / Configuration

    Returns: :py:class:`dict` with the roles in the same format as :py:func:`set_server_roles`
        accepts as kwargs.
    """
    if db:
        asr = cfmedb()['assigned_server_roles']
        sr = cfmedb()['server_roles']
        cfg = store.current_appliance.get_yaml_config('vmdb')
        roles = list(cfmedb().session.query(sr.name))
        roles_set = list(cfmedb().session.query(sr.name)
                         .join(asr, asr.server_role_id == sr.id))
        role_set = [role_set[0] for role_set in roles_set]
        roles_with_bool = {role[0]: role[0] in role_set for role in roles}

        dead_keys = ['database_owner', 'vdi_inventory']
        for key in roles_with_bool:
            if 'storage' not in cfg.get('product', {}):
                if key.startswith('storage'):
                    dead_keys.append(key)
                if key == 'vmdb_storage_bridge':
                    dead_keys.append(key)

        for key in dead_keys:
            try:
                del roles_with_bool[key]
            except:
                pass
        return roles_with_bool
    else:
        if navigate:
            sel.force_navigate("cfg_settings_currentserver_server")

        role_list = {}
        for (name, locator) in server_roles.fields:
            try:
                role_list[name] = locator.is_selected()
            except:
                logger.warning("role not found, skipping, netapp storage role?  (%s)", name)
        return role_list


@contextmanager
def _server_roles_cm(enable, *roles):
    """ Context manager that takes care of setting required roles and then restoring original roles.

    Args:
        enable: Whether to enable the roles.
        *roles: Role ids to set
    """
    try:
        original_roles = get_server_roles()
        set_roles = dict(original_roles)
        for role in roles:
            if role not in set_roles:
                raise NameError("No such role {}".format(role))
            set_roles[role] = enable
        set_server_roles(**set_roles)
        yield
    finally:
        set_server_roles(**original_roles)


def server_roles_enabled(*roles):
    return _server_roles_cm(True, *roles)


def server_roles_disabled(*roles):
    return _server_roles_cm(False, *roles)


def set_ntp_servers(*servers):
    """ Set NTP servers on Configure / Configuration pages.

    Args:
        *servers: Maximum of 3 hostnames.
    """
    server_value = ["", "", ""]
    sel.force_navigate("cfg_settings_currentserver_server")
    assert len(servers) <= 3, "There is place only for 3 servers!"
    for enum, server in enumerate(servers):
        server_value[enum] = server
    fields = {}
    for enum, server in enumerate(server_value):
        fields["ntp_server_%d" % (enum + 1)] = server
    fill(ntp_servers, fields, action=form_buttons.save)
    if servers:
        flash.assert_message_match(
            "Configuration settings saved for CFME Server \"{} [{}]\" in Zone \"{}\"".format(
                server_name(),
                server_id(),
                server_zone_description().partition(' ')[0].lower()))


def get_ntp_servers():
    sel.force_navigate("cfg_settings_currentserver_server")
    servers = set([])
    for i in range(3):
        value = sel.value("#ntp_server_{}".format(i + 1)).encode("utf-8").strip()
        if value:
            servers.add(value)
    return servers


def set_database_internal():
    """ Set the database as the internal one.

    """
    sel.force_navigate("cfg_settings_currentserver_database")
    fill(
        db_configuration,
        dict(type="Internal Database on this CFME Appliance"),
        action=form_buttons.save
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
        action=form_buttons.save
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
        action=form_buttons.save
    )


def restart_workers(name, wait_time_min=1):
    """ Restarts workers by their name.

    Args:
        name: Name of the worker. Multiple workers can have the same name. Name is matched with `in`
    Returns: bool whether the restart succeeded.
    """

    sel.force_navigate("cfg_diagnostics_server_workers")

    def get_all_pids(worker_name):
        return {row.pid.text for row in records_table.rows() if worker_name in row.name.text}

    reload_func = partial(tb.select, "Reload current workers display")

    pids = get_all_pids(name)
    # Initiate the restart
    for pid in pids:
        records_table.click_cell("pid", pid)
        tb.select("Configuration", "Restart selected worker", invokes_alert=True)
        sel.handle_alert(cancel=False)
        reload_func()

    # Check they have finished
    def _check_all_workers_finished():
        for pid in pids:
            if records_table.click_cell("pid", pid):    # If could not click, no longer present
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


def get_workers_list(do_not_navigate=False, refresh=True):
    """Retrieves all workers.

    Returns a dictionary where keys are names of the workers and values are lists (because worker
    can have multiple instances) which contain dictionaries with some columns.
    """
    if do_not_navigate:
        if refresh:
            tb.select("Reload current workers display")
    else:
        sel.force_navigate("cfg_diagnostics_server_workers")
    workers = {}
    for row in records_table.rows():
        name = sel.text_sane(row.name)
        if name not in workers:
            workers[name] = []
        worker = {
            "status": sel.text_sane(row.status),
            "pid": int(sel.text_sane(row.pid)) if len(sel.text_sane(row.pid)) > 0 else None,
            "spid": int(sel.text_sane(row.spid)) if len(sel.text_sane(row.spid)) > 0 else None,
            "started": parsetime.from_american_with_utc(sel.text_sane(row.started)),

            "last_heartbeat": None,
        }
        try:
            workers["last_heartbeat"] = parsetime.from_american_with_utc(
                sel.text_sane(row.last_heartbeat))
        except ValueError:
            pass
        workers[name].append(worker)
    return workers


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


def set_replication_worker_host(host, port='5432'):
    """ Set replication worker host on Configure / Configuration pages.

    Args:
        host: Address of the hostname to replicate to.
    """
    sel.force_navigate("cfg_settings_currentserver_workers")
    change_stored_password()
    fill(
        replication_worker,
        dict(host=host,
             port=port,
             username=conf.credentials['database']['username'],
             password=conf.credentials['database']['password'],
             password_verify=conf.credentials['database']['password']),
        action=form_buttons.save
    )


def get_replication_status(navigate=True):
    """ Gets replication status from Configure / Configuration pages.

    Returns: bool of whether replication is Active or Inactive.
    """
    if navigate:
        sel.force_navigate("cfg_diagnostics_region_replication")
    return replication_process.status.text == "Active"


def get_replication_backlog(navigate=True):
    """ Gets replication backlog from Configure / Configuration pages.

    Returns: int representing the remaining items in the replication backlog.
    """
    if navigate:
        sel.force_navigate("cfg_diagnostics_region_replication")
    return int(replication_process.current_backlog.text)
