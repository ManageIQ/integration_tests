# -*- coding: utf-8 -*-
from copy import copy
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic_patternfly import Input, Button, BootstrapSelect, BootstrapSwitch
from widgetastic.widget import Text, View

from cfme.base.ui import ServerView
from cfme.exceptions import ConsoleNotSupported, ConsoleTypeNotSupported
from cfme.utils import version
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable


class ServerInformationView(ServerView):
    """ Class represents full Server tab view"""
    title = Text("//div[@id='settings_server']/h3[1]")
    save_button = Button('Save')
    reset_button = Button('Reset')

    @View.nested
    class basic_information(View):    # noqa
        """ Class represents Server Basic Information Form """

        company_name = Input(name='server_company')
        appliance_name = Input(name='server_name')
        appliance_zone = BootstrapSelect(id='server_zone')
        time_zone = BootstrapSelect(id='server_timezone')
        locale = BootstrapSelect(id='locale')

    @View.nested
    class server_roles(View):   # noqa
        """ Class represents Server Roles Form """

        embedded_ansible = BootstrapSwitch(name='server_roles_embedded_ansible')
        ems_metrics_coordinator = BootstrapSwitch(name="server_roles_ems_metrics_coordinator")
        ems_operations = BootstrapSwitch(name="server_roles_ems_operations")
        ems_metrics_collector = BootstrapSwitch(name="server_roles_ems_metrics_collector")
        reporting = BootstrapSwitch(name="server_roles_reporting")
        ems_metrics_processor = BootstrapSwitch(name="server_roles_ems_metrics_processor")
        scheduler = BootstrapSwitch(name="server_roles_scheduler")
        smartproxy = BootstrapSwitch(name="server_roles_smartproxy")
        database_operations = BootstrapSwitch(name="server_roles_database_operations")
        smartstate = BootstrapSwitch(name="server_roles_smartstate")
        event = BootstrapSwitch(name="server_roles_event")
        user_interface = BootstrapSwitch(name="server_roles_user_interface")
        web_services = BootstrapSwitch(name="server_roles_web_services")
        ems_inventory = BootstrapSwitch(name="server_roles_ems_inventory")
        notifier = BootstrapSwitch(name="server_roles_notifier")
        automate = BootstrapSwitch(name="server_roles_automate")
        rhn_mirror = BootstrapSwitch(name="server_roles_rhn_mirror")
        database_synchronization_role = BootstrapSwitch(
            name="server_roles_database_synchronization")
        git_owner = BootstrapSwitch(name="server_roles_git_owner")
        websocket = BootstrapSwitch(name="server_roles_websocket")
        cockpit_ws = BootstrapSwitch(name="server_roles_cockpit_ws")
        # STORAGE OPTIONS
        storage_metrics_processor = BootstrapSwitch(name="server_roles_storage_metrics_processor")
        storage_metrics_collector = BootstrapSwitch(name="server_roles_storage_metrics_collector")
        storage_metrics_coordinator = BootstrapSwitch(
            name="server_roles_storage_metrics_coordinator")
        storage_inventory = BootstrapSwitch(name="server_roles_storage_inventory")
        vmdb_storage_bridge = BootstrapSwitch(name="server_roles_vmdb_storage_bridge")

        default_smart_proxy = Text(
            "//label[contains(text(), 'Default Repository SmartProxy')]/following-sibling::div")

    @View.nested
    class vmware_console(View):    # noqa
        """ Class represents Server VWware Console Support Form """

        console_type = BootstrapSelect("console_type")

    @View.nested
    class ntp_servers(View):    # noqa
        """ Class represents Server VWware Console Support Form """

        ntp_server_1 = Input(name="ntp_server_1")
        ntp_server_2 = Input(name="ntp_server_2")
        ntp_server_3 = Input(name="ntp_server_3")

    @View.nested
    class smtp_server(View):    # noqa
        """ Class represents SMTP Server Form """

        host = Input("smtp_host")
        port = Input("smtp_port")
        domain = Input("smtp_domain")
        start_tls = Input("smtp_enable_starttls_auto")
        ssl_verify = BootstrapSelect("smtp_openssl_verify_mode")
        auth = BootstrapSelect("smtp_authentication")
        username = Input("smtp_user_name")
        password = Input("smtp_password")
        from_email = Input("smtp_from")
        to_email = Input("smtp_test_to")
        verify = Button('Verify')

    @View.nested
    class web_services(View):   # noqa
        """ Class represents Server WebServices Form """

        mode = BootstrapSelect(id='webservices_mode')
        security = BootstrapSelect(id='webservices_security')

    @View.nested
    class logging_form(View):   # noqa
        """ Class represents Server Logging Form """

        log_level = BootstrapSelect(id='log_level')

    @View.nested
    class custom_support_url(View):   # noqa
        """ Class represents Server Custom Support URL Form """

        url = Input(name='custom_support_url')
        description = Input(name='custom_support_url_description')

    @property
    def is_displayed(self):
        return {
            self.server.is_active and
            self.title.text == 'Basic Information'
        }


class ServerInformation(Updateable, Pretty, NavigatableMixin):
    """ This class represents the Server tab in Server Settings

    Kwargs:
        All lower parameters by default set to None
        BasicInformationForm:
            company_name: Company name, default value in "My Company"
            appliance_name: Appliance name.
            appliance_zone: Appliance Zone.
            time_zone: Time Zone.
            locale: Locale used for users UI
        ServerControlForm (Server Roles):
            websocket, ems_metrics_coordinator, cockpit_ws, smartproxy,
            storage_metrics_collector, database_operations, smartstate, event,
            storage_inventory, storage_metrics_processor, web_services, automate,
            rhn_mirror, database_synchronization, ems_operations, ems_metrics_collector,
            reporting, ems_metrics_processor, scheduler, git_owner, user_interface,
            embedded_ansible, storage_metrics_coordinator, ems_inventory,
            vmdb_storage_bridge, notifier: set True/False to change the state
        VWwareConsoleSupportForm:
            console_type - Server console type
        NTPServersForm:
            ntp_server_1, ntp_server_2, ntp_server_3 - Set ntp server
        SMTPServerForm:
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
        WebServicesForm:
            mode: web services mode
            security: security type
        LoggingForm:
            log_level: log level type
        CustomSupportURL:
            url: custom url
            decryption: url description
    """
    CONSOLE_TYPES = ('VNC', 'VMware VMRC Plugin', 'VMware WebMKS')
    SERVER_ROLES = ('embedded_ansible', 'ems_metrics_coordinator', 'ems_operations',
                    'ems_metrics_collector', 'reporting', 'ems_metrics_processor', 'scheduler',
                    'smartproxy', 'database_operations', 'smartstate', 'event', 'user_interface',
                    'web_services', 'ems_inventory', 'notifier', 'automate',
                    'rhn_mirror', 'database_synchronization_role', 'git_owner', 'websocket',
                    'storage_metrics_processor', 'storage_metrics_collector',
                    'storage_metrics_coordinator', 'storage_inventory', 'vmdb_storage_bridge',
                    'cockpit_ws')

    _basic_information = ['company_name', 'appliance_name', 'appliance_zone', 'time_zone', 'locale']
    _vmware_console = ['console_type']
    _ntp_servers = ['ntp_server_1', 'ntp_server_2', 'ntp_server_3']
    _smtp_server = ['host', 'port', 'domain', 'start_tls', 'ssl_verify', 'auth', 'username',
                   'password', 'from_email', 'to_email']
    _web_services = ['mode', 'security']
    _logging = ['log_level']
    _custom_support_url = ['url', 'description']

    pretty_attrs = ['appliance']

    def __init__(self, appliance):
        self.appliance = appliance
        full_form = (self._basic_information + list(self.SERVER_ROLES) + self._vmware_console +
                     self._ntp_servers + self._smtp_server + self._web_services + self._logging +
                     self._custom_support_url)
        for att in full_form:
            # embedded_ansible available from 5.8 version
            if att != 'embedded_ansible' and self.appliance.version > '5.7':
                setattr(self, att, None)


# ============================= Basic Information Form =================================

    def update_basic_information(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates basic information form
        Args:
             updates: dict, widgets will be updated regarding updates.
                ex. update_basic_information({'company_name': 'New name'})
             regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset
        """
        view = navigate_to(self, 'Details')

        view.basic_information.fill(updates)
        self._save_action(view, updates, reset)

    @property
    def basic_information_values(self):
        """ Returns(dict): basic_information fields values"""
        view = navigate_to(self, 'Details')
        return view.basic_information.read()

# ============================= VMware Console Form =================================

    def update_vmware_console(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates Vmware console

        Args:
             updates: dict, widgets will be updated regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset

        """
        view = navigate_to(self, 'Details')
        for name, value in updates.items():
            if name == 'console_type':
                if value not in self.CONSOLE_TYPES:
                    raise ConsoleTypeNotSupported(value)
                if self.appliance.version < '5.8':
                    raise ConsoleNotSupported(
                        product_name=self.appliance.product_name,
                        version=self.appliance.version
                    )
        view.vmware_console.fill(updates)
        self._save_action(view, updates, reset)

    @property
    def vmware_console_values(self):
        """ Returns(dict): vmware_console fields values"""
        view = navigate_to(self, 'Details')
        return view.vmware_console.read()

# ============================= NTP Servers Form =================================

    def update_ntp_servers(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates ntp servers

        Args:
             updates: dict, widgets will be updated regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset

        """
        view = navigate_to(self, 'Details')
        view.ntp_servers.fill(updates)
        self._save_action(view, updates, reset)

    @property
    def ntp_servers_values(self):
        """ Returns(dict): ntp_servers fields values"""
        view = navigate_to(self, 'Details')
        return view.ntp_servers.read()

    @property
    def ntp_servers_fields_keys(self):
        """ Returns(list): ntp servers fields names"""
        return self._ntp_servers


# ============================= SMTP Server Form =================================

    def update_smtp_server(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates smtp server
        Args:
             updates: dict, widgets will be updated regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset
        """
        view = navigate_to(self, 'Details')
        view.smtp_server.fill(updates)
        if view.smtp_server.verify.active:
            view.smtp_server.verify.click()
        self._save_action(view, updates, reset)

    def send_test_email(self, email=None):
        """ Send a testing e-mail on specified address. Needs configured SMTP. """
        view = navigate_to(self, 'Details')
        if not email:
            email = self.to_email
        view.smtp_server.fill({'to_email': email})
        view.smtp_server.verify.click()

    @property
    def smtp_server_values(self):
        """ Returns(dict): smtp_server fields values"""
        view = navigate_to(self, 'Details')
        return view.smtp_server.read()

# ============================= Web Services Form =================================

    def update_web_services(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates web services
        Args:
             updates: dict, widgets will be updated regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset
        """
        view = navigate_to(self, 'Details')
        view.web_services.fill(updates)
        self._save_action(view, updates, reset)

    @property
    def web_services_values(self):
        """ Returns(dict): web_services fields values"""
        view = navigate_to(self, 'Details')
        return view.web_services.read()

# ============================= Logging Form =================================

    def update_logging_form(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates logging form
        Args:
             updates: dict, widgets will be updated regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset
        """
        view = navigate_to(self, 'Details')
        view.web_services.fill(updates)
        self._save_action(view, updates, reset)

    @property
    def logging_values(self):
        """ Returns(dict): logging fields values"""
        view = navigate_to(self, 'Details')
        return view.logging_form.read()

# ============================= Custom Support Url Form =================================

    def update_custom_support_url(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates custom support url
        Args:
             updates: dict, widgets will be updated regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset
        """
        view = navigate_to(self, 'Details')
        view.custom_support_url.fill(updates)
        self._save_action(view, updates, reset)

    @property
    def custom_support_url_values(self):
        """ Returns(dict): custom_support_url fields values"""
        view = navigate_to(self, 'Details')
        return view.custom_support_url.read()

# =============================== Server Roles Form ===================================

    def update_server_roles_ui(self, updates, reset=False):
        """ Navigate to a Server Tab. Updates server roles via UI
        Args:
             updates: dict, widgets will be updated regarding updates.
             reset: By default(False) changes will not be reset, if True changes will be reset
        """
        view = navigate_to(self, 'Details')
        # embedded_ansible server role available from 5.8 version
        if self.appliance.version < '5.8' and 'embedded_ansible' in updates:
            updates.pop('embedded_ansible')
        # cockpit_ws element is not present for downstream version
        if self.appliance.version != version.UPSTREAM and 'cockpit_ws' in updates:
            updates.pop('cockpit_ws')
        view.server_roles.fill(updates)
        self._save_action(view, updates, reset)

    def update_server_roles_db(self, roles):
        """ Set server roles on Configure / Configuration pages.
        Args:
            roles: Roles specified as in server_roles dict in this module. Set to True or False
        """
        if self.server_roles_db == roles:
            logger.debug(' Roles already match, returning...')
            return
        else:
            self.appliance.server_roles = roles

    @property
    def server_roles_db(self):
        """ Get server roles from Configure / Configuration from DB
        Returns: :py:class:`dict` with the roles in the same format as :py:func:`set_server_roles`
            accepts as kwargs.
        """
        return self.appliance.server_roles

    @property
    def server_roles_ui(self):
        view = navigate_to(self, 'Details')
        roles = view.server_roles.read()
        # default_smart_proxy is not a role, but text info
        roles.pop('default_smart_proxy')
        return roles

    def server_roles_enabled(self, *roles):
        """ Enables Server roles """
        self._change_server_roles_state(True, *roles)

    def server_roles_disabled(self, *roles):
        """ Disable Server roles """
        self._change_server_roles_state(False, *roles)

    def _change_server_roles_state(self, enable, *roles):
        """ Takes care of setting required roles and then restoring original roles.
        Args:
            enable: Whether to enable the roles.
        """
        try:
            original_roles = self.server_roles_db
            set_roles = copy(original_roles)
            for role in roles:
                set_roles[role] = enable
            self.update_server_roles_db(set_roles)
        except Exception:
            self.update_server_roles_db(original_roles)

    def _save_action(self, view, updates, reset):
        """ Take care of actions to do after updates """
        if reset:
            try:
                view.reset_button.click()
                flash_message = 'All changes have been reset'
            except Exception:
                logger.warning('No values was changed')
        else:
            view.save_button.click()
            self.appliance.server_details_changed()
            flash_message = (
                'Configuration settings saved for {} Server "{} [{}]" in Zone "{}"'.format(
                    self.appliance.product_name,
                    self.appliance.server_name(),
                    self.appliance.server_id(),
                    self.appliance.server.zone.name))
        view.flash.assert_message(flash_message)

    def _save_action(self, view, updates, reset):
        """ Take care of actions to do after updates """
        if reset:
            try:
                view.reset_button.click()
                flash_message = 'All changes have been reset'
            except Exception:
                logger.warning('No values was changed')
        else:
            view.save_button.click()
            self.appliance.server_details_changed()
            flash_message = (
                'Configuration settings saved for {} Server "{} [{}]" in Zone "{}"'.format(
                    self.appliance.product_name,
                    self.appliance.server_name(),
                    self.appliance.server_id(),
                    self.appliance.server.zone.name))
        view.flash.assert_message(flash_message)


@navigator.register(ServerInformation)
class Details(CFMENavigateStep):
    VIEW = ServerInformationView
    prerequisite = NavigateToAttribute('appliance.server', 'Details')

    def am_i_here(self):
        return (
            self.prerequisite_view.is_displayed and
            self.prerequisite_view.server.is_displayed
        )

    def step(self):
        self.prerequisite_view.server.select()


@navigator.register(ServerInformation)
class Authentication(CFMENavigateStep):
    # VIEW = Todo
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.authentication.select()


@navigator.register(ServerInformation)
class Workers(CFMENavigateStep):
    # VIEW = Todo
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.workers.select()


@navigator.register(ServerInformation)
class CustomLogos(CFMENavigateStep):
    # VIEW = Todo
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.custom_logos.select()


@navigator.register(ServerInformation)
class Advanced(CFMENavigateStep):
    # VIEW = Todo
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.advanced.select()
