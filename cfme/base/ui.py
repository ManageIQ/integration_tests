import re
import time

from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from selenium.webdriver.common.keys import Keys
from widgetastic.widget import ConditionalSwitchableView
from widgetastic.widget import FileInput
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import Accordion
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BootstrapSwitch
from widgetastic_patternfly import Button
from widgetastic_patternfly import CheckableBootstrapTreeview
from widgetastic_patternfly import DatePicker
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import FlashMessages
from widgetastic_patternfly import Input

from cfme.base import Region
from cfme.base import Server
from cfme.base import Zone
from cfme.base import ZoneCollection
from cfme.base.credential import Credential
from cfme.common import BaseLoggedInPage
from cfme.configure.about import AboutView
from cfme.configure.configuration.server_settings import ServerAuthenticationView
from cfme.configure.configuration.server_settings import ServerInformationView
from cfme.configure.configuration.server_settings import ServerWorkersView
from cfme.configure.documentation import DocView
from cfme.configure.tasks import TasksView
from cfme.dashboard import DashboardView
from cfme.exceptions import ItemNotFound
from cfme.intelligence.chargeback import ChargebackView
from cfme.intelligence.rss import RSSView
from cfme.intelligence.timelines import CloudIntelTimelinesView
from cfme.optimize.utilization import RegionUtilizationTrendsView
from cfme.utils import conf
from cfme.utils.appliance import MiqImplementationContext
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.appliance.implementations.ui import ViaUI
from cfme.utils.log import logger
from widgetastic_manageiq import AttributeValueForm
from widgetastic_manageiq import Checkbox
from widgetastic_manageiq import DiagnosticsTreeView
from widgetastic_manageiq import InputButton
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import ServerTimelinesView
from widgetastic_manageiq import SummaryForm
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import WaitTab


@MiqImplementationContext.external_for(Server.address, ViaUI)
def address(self):
    logger.info("USING UI ADDRESS")
    return self.appliance.url


class LoginPage(View):
    flash = View.nested(FlashMessages)

    class details(View):  # noqa
        region = Text('.//p[normalize-space(text())="Region:"]/span')
        zone = Text('.//p[normalize-space(text())="Zone:"]/span')
        appliance = Text('.//p[normalize-space(text())="Appliance:"]/span')

    change_password = Text('.//a[normalize-space(.)="Update password"]')
    back = Text('.//a[normalize-space(.)="Back"]')
    username = Input(name='user_name')
    password = Input(name='user_password')
    new_password = Input(name='user_new_password')
    verify_password = Input(name='user_verify_password')
    login = Button(id='login')

    def show_update_password(self):
        if not self.new_password.is_displayed:
            self.change_password.click()

    def hide_update_password(self):
        if self.new_password.is_displayed:
            self.back.click()

    def login_admin(self, **kwargs):
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = self.extra.appliance.collections.users.instantiate(
            credential=cred, name='Administrator'
        )
        return self.log_in(user, **kwargs)

    def submit_login(self, method='click_on_login'):
        if method == 'click_on_login':
            self.login.click()
        elif method == 'press_enter_after_password':
            self.browser.send_keys(Keys.ENTER, self.password)
        elif method == '_js_auth_fn':
            self.browser.execute_script('miqAjaxAuth();')
        else:
            raise ValueError(f'Unknown method {method}')
        if self.flash.is_displayed:
            self.flash.assert_no_error()

    def log_in(self, user, method='click_on_login'):
        self.fill({
            'username': user.credential.principal,
            'password': user.credential.secret,
        })
        self.submit_login(method)
        logged_in_view = self.browser.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in:
            if user.name is None:
                name = logged_in_view.current_fullname
                self.logger.info(
                    'setting the appliance.user.name to %r because it was not specified', name)
                user.name = name
            self.extra.appliance.user = user

    def update_password(
            self, user, new_password, verify_password=None, method='click_on_login'):
        self.show_update_password()
        self.fill({
            'username': user.credential.principal,
            'password': user.credential.secret,
            'new_password': new_password,
            'verify_password': verify_password if verify_password is not None else new_password
        })
        self.submit_login(method)
        logged_in_view = self.browser.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in:
            if user.name is None:
                name = logged_in_view.current_fullname
                self.logger.info(
                    'setting the appliance.user.name to %r because it was not specified', name)
                user.name = name
            self.extra.appliance.user = user

    def logged_in_as_user(self, user):
        return False

    @property
    def logged_in_as_current_user(self):
        return False

    # TODO remove this property, it is erroneous. View properties should be returning data from UI
    @property
    def current_username(self):
        return None

    @property
    def current_fullname(self):
        return None

    @property
    def current_groupname(self):
        return None

    @property
    def logged_in(self):
        return not self.logged_out

    @property
    def logged_out(self):
        return self.username.is_displayed and self.password.is_displayed and self.login.is_displayed

    @property
    def is_displayed(self):
        return self.logged_out


@MiqImplementationContext.external_for(Server.logged_in, ViaUI)
def logged_in(self):
    return self.appliance.browser.create_view(BaseLoggedInPage).logged_in


LOGIN_METHODS = ['click_on_login', 'press_enter_after_password', '_js_auth_fn']


@MiqImplementationContext.external_for(Server.update_password, ViaUI)
def update_password(self, new_password, verify_password=None, user=None, method=LOGIN_METHODS[1]):
    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = self.appliance.collections.users.instantiate(credential=cred, name='Administrator')

    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)

    if not logged_in_view.logged_in_as_user(user):
        if logged_in_view.logged_in:
            logged_in_view.logout()

        from cfme.utils.appliance.implementations.ui import navigate_to
        login_view = navigate_to(self.appliance.server, 'LoginScreen')

        logger.debug('Changing password for user %s', user.credential.principal)

        login_view.update_password(user=user,
                                   new_password=new_password,
                                   verify_password=verify_password,
                                   method=method)

        try:
            assert logged_in_view.is_displayed
        except AssertionError:
            login_view.flash.assert_no_error()

    return logged_in_view


@MiqImplementationContext.external_for(Server.login, ViaUI)
# for selenim3 v_js_auth_fn doesn't sent info to the server
def login(self, user=None, method=LOGIN_METHODS[1]):
    """
    Login to CFME with the given username and password.
    Optionally, submit_method can be press_enter_after_password
    to use the enter key to login, rather than clicking the button.
    Args:
        user: The username to fill in the username field.
        password: The password to fill in the password field.
        submit_method: A function to call after the username and password have been input.
    Raises:
        RuntimeError: If the login fails, ie. if a flash message appears
    """
    # Circular import
    if not user:
        username = conf.credentials['default']['username']
        password = conf.credentials['default']['password']
        cred = Credential(principal=username, secret=password)
        user = self.appliance.collections.users.instantiate(credential=cred, name='Administrator')

    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)

    if not logged_in_view.logged_in_as_user(user):
        if logged_in_view.logged_in:
            logged_in_view.logout()

        from cfme.utils.appliance.implementations.ui import navigate_to
        login_view = navigate_to(self.appliance.server, 'LoginScreen')

        time.sleep(1)

        logger.debug('Logging in as user %s', user.credential.principal)
        login_view.flush_widget_cache()

        login_view.log_in(user, method=method)
        logged_in_view.flush_widget_cache()
        try:
            assert logged_in_view.is_displayed
            assert logged_in_view.logged_in_as_user
            user.name = logged_in_view.current_fullname
            self.appliance.user = user
        except AssertionError:
            login_view.flash.assert_no_error()
    return logged_in_view


@MiqImplementationContext.external_for(Server.login_admin, ViaUI)
def login_admin(self, **kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.
    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    cred = Credential(principal=username, secret=password)
    user = self.appliance.collections.users.instantiate(credential=cred, name='Administrator')
    logged_in_page = self.login(user, **kwargs)
    return logged_in_page


@MiqImplementationContext.external_for(Server.logout, ViaUI)
def logout(self):
    """
    Logs out of CFME.
    """
    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        logged_in_view.logout()
        self.appliance.user = None


@MiqImplementationContext.external_for(Server.current_full_name, ViaUI)
def current_full_name(self):
    """ Returns the current username.
    Returns: the current username.
    """
    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        return logged_in_view.current_fullname
    else:
        return None


@MiqImplementationContext.external_for(Server.current_group_name, ViaUI)
def current_group_name(self):
    """Returns current groupname from settings dropdown nav if logged in, or None"""
    view = self.appliance.browser.create_view(BaseLoggedInPage)
    return view.current_groupname if view.logged_in else None


@MiqImplementationContext.external_for(Server.group_names, ViaUI)
def group_names(self):
    """Returns group names selectable for current user from settings dropdown if logged in"""
    view = self.appliance.browser.create_view(BaseLoggedInPage)
    return view.group_names if view.logged_in else None


# ######################## SERVER NAVS ################################

@navigator.register(Server)
class LoginScreen(CFMENavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        from cfme.utils.browser import ensure_browser_open
        ensure_browser_open(self.obj.appliance.server.address())

    def step(self, *args, **kwargs):
        # Can be either blank or logged in
        logged_in_view = self.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in:
            logged_in_view.logout()

        # TODO this is not the place to handle this behavior
        if not self.view.wait_displayed(timeout=60):
            # Something is wrong
            from cfme.utils import browser
            del self.view  # In order to unbind the browser
            browser.quit()
            raise


@navigator.register(Server)
class LoggedIn(CFMENavigateStep):
    VIEW = BaseLoggedInPage
    prerequisite = NavigateToSibling('LoginScreen')

    def step(self, *args, **kwargs):
        user = self.obj.appliance.user
        self.prerequisite_view.log_in(user)


class ConfigurationView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    @View.nested
    class accordions(View):  # noqa

        @View.nested
        class settings(Accordion):  # noqa
            ACCORDION_NAME = "Settings"
            INDIRECT = True
            tree = ManageIQTree()

        @View.nested
        class accesscontrol(Accordion):  # noqa
            ACCORDION_NAME = "Access Control"
            tree = ManageIQTree()

        @View.nested
        class diagnostics(Accordion):  # noqa
            ACCORDION_NAME = "Diagnostics"
            tree = ManageIQTree()

        @View.nested
        class database(Accordion):  # noqa
            ACCORDION_NAME = "Database"
            tree = ManageIQTree()

    @property
    def in_configuration(self):
        return (
            self.navigation.currently_selected == [] and
            self.accordions.settings.is_displayed or
            self.accordions.accesscontrol.is_displayed or
            self.accordions.diagnostics.is_displayed or
            self.accordions.database.is_displayed)

    @property
    def is_displayed(self):
        # TODO: We will need a better ID of this location when we have user permissions in effect
        return self.in_configuration


@navigator.register(Server)
class Configuration(CFMENavigateStep):
    VIEW = ConfigurationView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        if self.obj.appliance.version < "5.11":
            self.prerequisite_view.settings.select_item('Configuration')
        else:
            self.prerequisite_view.configuration_settings.click()

        self.prerequisite_view.browser.handle_alert(wait=2, cancel=False, squash=True)


@navigator.register(Server)
class About(CFMENavigateStep):
    VIEW = AboutView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.help.select_item('About')
        # wait for it to open within this step, it can be slow.
        self.view.modal.wait_displayed(5)


@navigator.register(Server)
class RSS(CFMENavigateStep):
    VIEW = RSSView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.view.navigation.select('Overview', 'RSS')


@navigator.register(Server)
class CloudIntelTimelines(CFMENavigateStep):
    VIEW = CloudIntelTimelinesView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.view.navigation.select('Overview', 'Timelines')


@navigator.register(Server)
class Documentation(CFMENavigateStep):
    VIEW = DocView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.help.select_item('Documentation')


@navigator.register(Server)
class Tasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.settings.select_item('Tasks')


@navigator.register(Server)
class Dashboard(CFMENavigateStep):
    VIEW = DashboardView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Overview', 'Dashboard')


@navigator.register(Server)
class Chargeback(CFMENavigateStep):
    VIEW = ChargebackView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Overview', 'Chargeback')


class ServerView(ConfigurationView):
    @View.nested
    class server(WaitTab):  # noqa
        TAB_NAME = "Server"
        including_view = View.include(ServerInformationView, use_parent=True)

    @View.nested
    class authentication(WaitTab):  # noqa
        TAB_NAME = "Authentication"
        including_view = View.include(ServerAuthenticationView, use_parent=True)

    @View.nested
    class workers(WaitTab):  # noqa
        TAB_NAME = "Workers"
        including_view = View.include(ServerWorkersView, use_parent=True)

    @View.nested
    class customlogos(WaitTab):  # noqa
        TAB_NAME = "Custom Logos"
        save_button = Button("Save")
        reset_button = Button("Reset")

        @View.nested
        class logo(View):   # noqa
            image = FileInput(id="upload_logo")
            upload_button = InputButton(
                locator='//div[contains(.,"Dimensions - 350x70.")]/input'
            )
            enable = BootstrapSwitch(id="server_uselogo")

        @View.nested
        class login_logo(View):    # noqa
            image = FileInput(id="login_logo")
            upload_button = InputButton(
                locator='//div[contains(.,"Dimensions - 1280x1000.")]/input'
            )
            enable = BootstrapSwitch(id="server_useloginlogo")

        @View.nested
        class brand(View):    # noqa
            image = FileInput(id="brand_logo")
            upload_button = InputButton(
                locator='//div[normalize-space()="* Requirements: File-type - PNG;"]/input'
            )
            enable = BootstrapSwitch(id="server_usebrand")

        @View.nested
        class favicon(View):    # noqa
            image = FileInput(id="favicon_logo")
            upload_button = InputButton(locator='//div[contains(.,"ICO")]/input')
            enable = BootstrapSwitch(id="server_usefavicon")

        @View.nested
        class logintext(View):    # noqa
            login_text = TextInput(id="login_text")
            enable = BootstrapSwitch(id="server_uselogintext")

    @View.nested
    class advanced(WaitTab):  # noqa
        TAB_NAME = "Advanced"

    @property
    def is_displayed(self):
        if not (self.in_configuration and self.accordions.settings.is_displayed):
            return False

        # check that tree contains all expected entities
        return self.accordions.settings.tree.currently_selected == self.context['object'].tree_path


@navigator.register(Server, 'Details')
class Details(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Configuration')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordions.settings.tree.click_path(*self.obj.tree_path)


@navigator.register(Server, 'Server')
class ServerDetails(CFMENavigateStep):
    VIEW = ServerInformationView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.server.select()


@navigator.register(Server)
class Authentication(CFMENavigateStep):
    VIEW = ServerAuthenticationView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.authentication.select()


@navigator.register(Server)
class Workers(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.workers.is_displayed and
            self.view.workers.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.workers.select()


@navigator.register(Server)
class CustomLogos(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.customlogos.is_displayed and
            self.view.customlogos.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.customlogos.select()


@navigator.register(Server)
class Advanced(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.advanced.is_displayed and
            self.view.advanced.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.advanced.select()


class ServerDatabaseView(ConfigurationView):
    @View.nested
    class summary(WaitTab):  # noqa
        TAB_NAME = "Summary"

    @View.nested
    class tables(WaitTab):  # noqa
        TAB_NAME = "Tables"

    @View.nested
    class indexes(WaitTab):  # noqa
        TAB_NAME = "Indexes"

    @View.nested
    class settings(WaitTab):  # noqa
        TAB_NAME = "Settings"

    @View.nested
    class client_connections(WaitTab):  # noqa
        TAB_NAME = "Client Connections"

    @View.nested
    class utilization(WaitTab):  # noqa
        TAB_NAME = "Utilization"

    @property
    def is_displayed(self):
        return (
            self.in_configuration and
            self.summary.is_displayed and
            self.accordions.database.is_opened
        )


class DatabaseSummaryView(ServerDatabaseView):
    properties = SummaryTable(title='Properties')

    @property
    def is_displayed(self):
        return (
            self.summary.is_displayed and
            self.summary.is_active() and
            self.title.text == 'VMDB Summary'
        )


class DatabaseTablesView(ServerDatabaseView):

    @property
    def is_displayed(self):
        return self.tables.is_active() and self.title.text == 'All VMDB Tables'


class DatabaseIndexesView(ServerDatabaseView):
    @property
    def is_displayed(self):
        return self.indexes.is_active() and self.title.text == 'All VMDB Indexes'


class DatabaseSettingsView(ServerDatabaseView):
    @property
    def is_displayed(self):
        return self.settings.is_active() and self.title.text == 'VMDB Settings'


class DatabaseClientConnectionsView(ServerDatabaseView):
    @property
    def is_displayed(self):
        return self.client_connections.is_active() and self.title.text == 'VMDB Client Connections'


class DatabaseUtilizationView(ServerDatabaseView):
    @property
    def is_displayed(self):
        return self.utilization.is_active() and self.title.text == 'VMDB Utilization'


@navigator.register(Server)
class Database(CFMENavigateStep):
    VIEW = ServerDatabaseView
    prerequisite = NavigateToSibling('Configuration')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordions.database.tree.click_path('VMDB')


@navigator.register(Server)
class DatabaseSummary(CFMENavigateStep):
    VIEW = DatabaseSummaryView
    prerequisite = NavigateToSibling('Database')

    def step(self, *args, **kwargs):
        self.prerequisite_view.summary.select()


@navigator.register(Server)
class DatabaseTables(CFMENavigateStep):
    VIEW = DatabaseTablesView
    prerequisite = NavigateToSibling('Database')

    def step(self, *args, **kwargs):
        self.prerequisite_view.tables.select()


@navigator.register(Server)
class DatabaseIndexes(CFMENavigateStep):
    VIEW = DatabaseIndexesView
    prerequisite = NavigateToSibling('Database')

    def step(self, *args, **kwargs):
        self.prerequisite_view.indexes.select()


@navigator.register(Server)
class DatabaseSettings(CFMENavigateStep):
    VIEW = DatabaseSettingsView
    prerequisite = NavigateToSibling('Database')

    def step(self, *args, **kwargs):
        self.prerequisite_view.settings.select()


@navigator.register(Server)
class DatabaseClientConnections(CFMENavigateStep):
    VIEW = DatabaseClientConnectionsView
    prerequisite = NavigateToSibling('Database')

    def step(self, *args, **kwargs):
        self.prerequisite_view.client_connections.select()


@navigator.register(Server)
class DatabaseUtilization(CFMENavigateStep):
    VIEW = DatabaseUtilizationView
    prerequisite = NavigateToSibling('Database')

    def step(self, *args, **kwargs):
        self.prerequisite_view.utilization.select()


class ServerDiagnosticsView(ConfigurationView):
    @View.nested
    class summary(WaitTab):  # noqa
        TAB_NAME = "Summary"
        started_on = SummaryFormItem('EVM', 'Started On')

    @View.nested
    class workers(WaitTab):  # noqa
        TAB_NAME = "Workers"

    @View.nested
    class collectlogs(WaitTab):  # noqa
        TAB_NAME = "Collect Logs"

    @View.nested
    class cfmelog(WaitTab):  # noqa
        TAB_NAME = "CFME Log"

    @View.nested
    class auditlog(WaitTab):  # noqa
        TAB_NAME = "Audit Log"

    @View.nested
    class productionlog(WaitTab):  # noqa
        TAB_NAME = "Production Log"

    @View.nested
    class utilization(WaitTab):  # noqa
        TAB_NAME = "Utilization"

    @View.nested
    class timelines(WaitTab, ServerTimelinesView):  # noqa
        TAB_NAME = "Timelines"

    configuration = Dropdown('Configuration')

    @property
    def is_displayed(self):
        return (
            self.accordions.diagnostics.tree.currently_selected ==
            self.context['object'].diagnostics_tree_path
        )


class ServerDiagnosticsCollectLogsView(ServerDiagnosticsView):
    @property
    def is_displayed(self):
        return self.collectlogs.is_active()


@navigator.register(Server)
class Diagnostics(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Configuration')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            *self.obj.diagnostics_tree_path)


@navigator.register(Server)
class DiagnosticsDetails(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.summary.is_displayed and
            self.view.summary.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.summary.select()


@navigator.register(Server)
class DiagnosticsWorkers(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.workers.is_displayed and
            self.view.workers.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.workers.select()


@navigator.register(Server)
class ServerDiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = ServerDiagnosticsCollectLogsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.collectlogs.is_displayed and
            self.view.collectlogs.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.collectlogs.select()


@navigator.register(Server)
class CFMELog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.cfmelog.is_displayed and
            self.view.cfmelog.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.cfmelog.select()


@navigator.register(Server)
class AuditLog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.auditlog.is_displayed and
            self.view.auditlog.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.auditlog.select()


@navigator.register(Server)
class ProductionLog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.productionlog.is_displayed and
            self.view.productionlog.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.productionlog.select()


@navigator.register(Server)
class Utilization(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.utilization.is_displayed and
            self.view.utilization.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.utilization.select()


@navigator.register(Server)
class Timelines(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.timelines.is_displayed and
            self.view.timelines.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.timelines.select()


# ######################## REGION NAVS ################################
class CompanyCategories(WaitTab):
    TAB_NAME = "My Company Categories"


class CompanyTags(WaitTab):
    TAB_NAME = "My Company Tags"


class ImportTags(WaitTab):
    TAB_NAME = "Import Tags"


class MapTags(WaitTab):
    TAB_NAME = "Map Tags"


class ImportVariable(WaitTab):
    TAB_NAME = "Import Variables"


class TagsView(WaitTab):
    TAB_NAME = "Tags"

    company_categories = View.nested(CompanyCategories)
    company_tags = View.nested(CompanyTags)
    import_tags = View.nested(ImportTags)
    map_tags = View.nested(MapTags)
    imports = View.nested(ImportVariable)


class RegionView(ConfigurationView):
    @View.nested
    class details(WaitTab):  # noqa
        TAB_NAME = "Details"
        table = Table(locator='.//table[./tbody/tr/td[@title="Edit this Region"]]')

    @View.nested
    class candu_collection(WaitTab):  # noqa
        TAB_NAME = "C & U Collection"

    @View.nested
    class redhat_updates(WaitTab):  # noqa
        TAB_NAME = "Red Hat Updates"

    @View.nested
    class imports(WaitTab):  # noqa
        TAB_NAME = "Import Variables"

    @View.nested
    class replication(WaitTab):  # noqa
        TAB_NAME = "Replication"

    @View.nested
    class help_menu(WaitTab):   # noqa
        TAB_NAME = "Help Menu"

    @View.nested
    class advanced(WaitTab):   # noqa
        TAB_NAME = "Advanced"

    company_categories = View.nested(CompanyCategories)
    company_tags = View.nested(CompanyTags)
    import_tags = View.nested(ImportTags)
    map_tags = View.nested(MapTags)
    tags = View.nested(TagsView)

    @property
    def is_displayed(self):
        return self.accordions.settings.tree.currently_selected == self.context['object'].tree_path


class RegionChangeNameView(RegionView):
    region_description = Input("region_description")
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return self.region_description.is_displayed and super().is_displayed


class HelpMenuView(RegionView):
    documentation_title = Input('documentation_title')
    documentation_url = Input('documentation_href')
    documentation_type = BootstrapSelect('documentation_type')

    product_title = Input('product_title')
    product_url = Input('product_href')
    product_type = BootstrapSelect('product_type')

    about_title = Input('about_title')
    about_url = Input('about_href')
    about_type = BootstrapSelect('about_type')

    submit = Button('Submit')

    @property
    def is_displayed(self):
        return self.help_menu.is_active() and self.documentation_title.is_displayed


@navigator.register(Region, 'Details')
class RegionDetails(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordions.settings.tree.click_path(*self.obj.tree_path)
        self.view.details.select()


@navigator.register(Region)
class ChangeRegionName(CFMENavigateStep):
    VIEW = RegionChangeNameView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.view.details.table.row().click()


@navigator.register(Region)
class ImportTags(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.tags.import_tags.select()


@navigator.register(Region)
class Import(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.tags.imports.select()


@navigator.register(Region)
class HelpMenu(CFMENavigateStep):
    VIEW = HelpMenuView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.help_menu.select()


@navigator.register(Region, 'Advanced')
class RegionAdvanced(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.advanced.is_displayed and
            self.view.advanced.is_active())

    def step(self, *args, **kwargs):
        self.prerequisite_view.advanced.select()


@navigator.register(Region, "UtilTrendSummary")
class RegionOptimizeUtilization(CFMENavigateStep):
    VIEW = RegionUtilizationTrendsView

    prerequisite = NavigateToAttribute("appliance.collections.utilization", "All")

    def step(self, *args, **kwargs):
        path = [self.obj.region_string]
        if self.appliance.version >= "5.11":
            path.insert(0, "Enterprise")
        self.prerequisite_view.tree.click_path(*path)


class ZoneListView(ConfigurationView):
    configuration = Dropdown('Configuration')
    table = Table('//div[@id="settings_list"]/table')

    @property
    def is_displayed(self):
        return (
            self.accordions.settings.is_opened and
            self.accordions.settings.tree.currently_selected ==
            self.context['object'].zones_tree_path and
            self.title.text == 'Settings Zones' and
            self.table.is_displayed)


@navigator.register(Region, 'Zones')
class RegionZones(CFMENavigateStep):
    VIEW = ZoneListView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self, *args, **kwargs):
        tree_path = self.obj.zones_tree_path
        self.prerequisite_view.accordions.settings.tree.click_path(*tree_path)
        if not self.view.is_displayed:
            # Zones is too smart and does not reload upon clicking, this helps
            self.prerequisite_view.accordions.accesscontrol.open()
            self.prerequisite_view.accordions.settings.tree.click_path(*tree_path)


class RegionDiagnosticsView(ConfigurationView):
    @View.nested
    class zones(WaitTab):  # noqa
        TAB_NAME = "Zones"

    @View.nested
    class rolesbyservers(WaitTab):  # noqa
        TAB_NAME = "Roles by Servers"
        title = Text(
            '//*[@id="zone_tree_div"]/'
            'h3[contains(normalize-space(.), "Status of Regional Roles for Servers in Region")]'
        )
        tree = DiagnosticsTreeView("roles_by_server_treebox")
        selected_item = SummaryForm("Selected Item")
        configuration = Dropdown("Configuration")

    @View.nested
    class serversbyroles(WaitTab):  # noqa
        TAB_NAME = "Servers by Roles"
        title = Text(
            '//*[@id="zone_tree_div"]/'
            'h3[contains(normalize-space(.), "Status of Regional Roles for Servers in Region")]'
        )
        tree = DiagnosticsTreeView("servers_by_role_treebox")
        selected_item = SummaryForm("Selected Item")
        configuration = Dropdown("Configuration")

    @View.nested
    class servers(WaitTab):  # noqa
        TAB_NAME = "Servers"
        table = Table('//*[@id="miq-gtl-view"]//table')

    @View.nested
    class database(WaitTab):  # noqa
        TAB_NAME = "Database"

    @View.nested
    class orphaneddata(WaitTab):  # noqa
        TAB_NAME = "Orphaned Data"

    @property
    def is_displayed(self):
        return (
            self.accordions.diagnostics.is_opened and
            self.accordions.diagnostics.tree.currently_selected ==
            self.context['object'].tree_path and
            self.title.text.startswith('Diagnostics Region ')
        )


class CommonProtocolEntities(View):
    depot_name = Input(id='depot_name')
    uri = Input(id='uri')


class SambaProtocolEntities(CommonProtocolEntities):
    """ Samba Protocol fields for Database Backup """
    samba_username = Input(id='log_userid')
    samba_password = Input(id='log_password')
    samba_confirm_password = Input(id='log_verify')


class AWSS3ProtocolEntities(CommonProtocolEntities):
    """ AWS S3 Protocol fields for Database Backup """
    aws_region = BootstrapSelect(id='log_aws_region')
    aws_username = Input(id='log_userid')
    aws_password = Input(id='log_password')
    aws_confirm_password = Input(id='log_verify')


class OpenstackSwiftProtocolEntities(CommonProtocolEntities):
    """ Openstack Swift Protocol fields for Database Backup """
    openstack_keystone_version = BootstrapSelect(id='keystone_api_version')
    openstack_region = Input('openstack_region')
    openstack_security_protocol = BootstrapSelect(id='security_protocol')
    openstack_api_port = Input('swift_api_port')
    openstack_username = Input(id='log_userid')
    openstack_password = Input(id='log_password')
    openstack_confirm_password = Input(id='log_verify')


class NFSProtocolEntities(CommonProtocolEntities):
    """ NFS Protocol fields for Database Backup """
    pass


class DatabaseBackupEntities(View):
    """ Database Backup fields """
    backup_type = BootstrapSelect('log_protocol')

    backup_settings = ConditionalSwitchableView(reference='backup_type')
    backup_settings.register('<No Depot>', default=True, widget=View())
    backup_settings.register('Samba', widget=SambaProtocolEntities)
    backup_settings.register('AWS S3', widget=AWSS3ProtocolEntities)
    backup_settings.register('OpenStack Swift', widget=OpenstackSwiftProtocolEntities)
    backup_settings.register('Network File System', widget=NFSProtocolEntities)


class RegionDiagnosticsDatabaseView(RegionDiagnosticsView):

    db_backup_settings = View.nested(DatabaseBackupEntities)
    submit_db_garbage_collection_button = Button(alt="Run Database Garbage Collection Now")

    depot_name = Input(id='depot_name')
    uri = Input(id='uri')

    @property
    def is_displayed(self):
        return (
            self.accordions.diagnostics.is_opened and
            self.accordions.diagnostics.tree.currently_selected == self.context['object'].tree_path
            and self.database.is_active()
        )


@navigator.register(Region, 'Diagnostics')
class RegionDiagnostics(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordions.diagnostics.tree.click_path(*self.obj.tree_path)


@navigator.register(Region, 'DiagnosticsZones')
class RegionDiagnosticsZones(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.zones.select()


@navigator.register(Region, 'RolesByServers')
class RegionDiagnosticsRolesByServers(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.rolesbyservers.select()


@navigator.register(Region, 'ServersByRoles')
class RegionDiagnosticsServersByRoles(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.serversbyroles.select()


@navigator.register(Region, 'Servers')
class RegionDiagnosticsServers(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.servers.select()


@navigator.register(Region, 'Database')
class RegionDiagnosticsDatabase(CFMENavigateStep):
    VIEW = RegionDiagnosticsDatabaseView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.database.select()


@navigator.register(Region, 'OrphanedData')
class RegionDiagnosticsOrphanedData(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self, *args, **kwargs):
        self.prerequisite_view.orphaneddata.select()


# ################################## ZONE NAVS ##############################


class ZoneForm(ConfigurationView):
    name = Input(name='name')
    description = Input(name='description')
    smartproxy_ip = Input(name='proxy_server_ip')
    ntp_server_1 = Input(name='ntp_server_1')
    ntp_server_2 = Input(name='ntp_server_2')
    ntp_server_3 = Input(name='ntp_server_3')
    max_scans = BootstrapSelect("max_scans")
    username = Input(name='userid')
    password = Input(name='password')
    verify = Input(name='verify')

    cancel_button = Button('Cancel')


class ZoneSettingsView(ConfigurationView):
    @View.nested
    class zone(WaitTab):  # noqa
        TAB_NAME = "Zone"
        configuration = Dropdown('Configuration')
        basic_information = SummaryForm("Basic Information")

    @View.nested
    class smart_proxy_affinity(WaitTab):  # noqa
        TAB_NAME = "SmartProxy Affinity"
        smartproxy_affinity = CheckableBootstrapTreeview(tree_id='smartproxy_affinitybox')
        save = Button(title='Save Changes')

    @View.nested
    class advanced(WaitTab):  # noqa
        TAB_NAME = "Advanced"

    @property
    def is_displayed(self):
        title_string = self.context['object'].title_string('"')
        return (
            self.accordions.settings.is_opened and
            self.accordions.settings.tree.currently_selected == self.context['object'].tree_path and
            self.title.text == f"Settings Zone {title_string}"
        )


# Zone Settings #
@navigator.register(Zone, 'Settings')
class ZoneSettings(CFMENavigateStep):
    VIEW = ZoneSettingsView

    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Zones')

    def step(self, *args, **kwargs):
        regex = re.compile(r'Zone\s?\:\s?{}'.format(re.escape(self.obj.description)))
        rows = self.prerequisite_view.table.rows((1, regex))
        for row in rows:
            row.click()
            break
        else:
            raise ItemNotFound(f"No unique Zone with the description {self.obj.description!r}.")


@navigator.register(Zone, 'Zone')
class ZoneZone(CFMENavigateStep):
    VIEW = ZoneSettingsView

    prerequisite = NavigateToSibling('Settings')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.zone.is_displayed and
            self.view.zone.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.zone.select()


@navigator.register(Zone, 'SmartProxyAffinity')
class ZoneSmartProxyAffinity(CFMENavigateStep):
    VIEW = ZoneSettingsView

    prerequisite = NavigateToSibling('Settings')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.smart_proxy_affinity.is_displayed and
            self.view.smart_proxy_affinity.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.smart_proxy_affinity.select()


@navigator.register(Zone, 'Advanced')
class ZoneAdvanced(CFMENavigateStep):
    VIEW = ZoneSettingsView

    prerequisite = NavigateToSibling('Settings')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.advanced.is_displayed and
            self.view.advanced.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.advanced.select()


# Zone Add #
class ZoneAddView(ZoneForm):
    add_button = Button('Add')

    @property
    def is_displayed(self):
        return self.title.text == 'Adding a new Zone'


@navigator.register(ZoneCollection, 'Add')
class ZoneAdd(CFMENavigateStep):
    VIEW = ZoneAddView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Zones')

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Add a new Zone")


# Zone Edit #
class ZoneEditView(ZoneForm):
    save_button = Button('Save')

    @property
    def is_displayed(self):
        return self.title.text == 'Editing Zone "{}"'.format(self.context['object'].description)


@navigator.register(Zone, 'Edit')
class ZoneEdit(CFMENavigateStep):
    VIEW = ZoneEditView
    prerequisite = NavigateToSibling('Zone')

    def step(self, *args, **kwargs):
        self.prerequisite_view.zone.configuration.item_select("Edit this Zone")


# Zone Diagnostics #
class ZoneDiagnosticsView(ConfigurationView):
    @View.nested
    class rolesbyservers(WaitTab):  # noqa
        TAB_NAME = "Roles by Servers"
        title = Text(
            '//*[@id="zone_tree_div"]/'
            'h3[contains(normalize-space(.), "Status of Roles for Servers in Zone")]'
        )
        tree = DiagnosticsTreeView("roles_by_server_treebox")
        selected_item = SummaryForm("Selected Item")
        configuration = Dropdown("Configuration")

    @View.nested
    class serversbyroles(WaitTab):  # noqa
        TAB_NAME = "Servers by Roles"

    @View.nested
    class servers(WaitTab):  # noqa
        TAB_NAME = "Servers"
        table = Table('//*[@id="miq-gtl-view"]//table')

    @View.nested
    class collectlogs(WaitTab):  # noqa
        TAB_NAME = "Collect Logs"

    @View.nested
    class candugapcollection(WaitTab):  # noqa
        TAB_NAME = "C & U Gap Collection"
        end_date = DatePicker(id='miq_date_2')
        start_date = DatePicker(id='miq_date_1')
        submit = Button(title='Submit')

    @property
    def is_displayed(self):
        title_string = self.context['object'].title_string('"')
        return (
            self.accordions.diagnostics.is_opened and
            self.accordions.diagnostics.tree.currently_selected ==
            self.context['object'].diagnostics_tree_path and
            self.title.text == f"Diagnostics Zone {title_string}"
        )


@navigator.register(Zone, 'Diagnostics')
class ZoneDiagnostics(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self, *args, **kwargs):
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            *self.obj.diagnostics_tree_path)


@navigator.register(Zone, 'RolesByServers')
class ZoneDiagnosticsRolesByServers(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.rolesbyservers.is_displayed and
            self.view.rolesbyservers.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.rolesbyservers.select()


@navigator.register(Zone, 'ServersByRoles')
class ZoneDiagnosticsServersByRoles(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.serversbyroles.is_displayed and
            self.view.serversbyroles.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.serversbyroles.select()


@navigator.register(Zone, 'Servers')
class ZoneDiagnosticsServers(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.servers.is_displayed and
            self.view.servers.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.servers.select()


@navigator.register(Zone, 'CollectLogs')
class ZoneCollectLogs(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.collectlogs.is_displayed and
            self.view.collectlogs.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.collectlogs.select()


@navigator.register(Zone, 'CANDUGapCollection')
class ZoneCANDUGapCollection(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.candugapcollection.is_displayed and
            self.view.candugapcollection.is_active()
        )

    def step(self, *args, **kwargs):
        self.prerequisite_view.candugapcollection.select()


@Zone.exists.external_getter_implemented_for(ViaUI)
def exists(self):
    try:
        navigate_to(self, 'Zone')
        return True
    except ItemNotFound:
        return False


@MiqImplementationContext.external_for(Zone.update, ViaUI)
def update(self, updates):
    view = navigate_to(self, 'Edit')
    changed = view.fill(updates)
    if changed:
        view.save_button.click()
    else:
        view.cancel_button.click()
    view = self.create_view(ZoneSettingsView)
    # assert view.is_displayed
    view.flash.assert_no_error()
    if changed:
        view.flash.assert_message(
            'Zone "{}" was saved'.format(updates.get('name', self.name)))
    else:
        view.flash.assert_message(
            f'Edit of Zone "{self.name}" was cancelled by the user')


@MiqImplementationContext.external_for(Zone.delete, ViaUI)
def delete(self, cancel=False):
    """ Delete the Zone represented by this object.

    Args:
        cancel: Whether to click on the cancel button in the pop-up.
    """
    view = navigate_to(self, 'Zone')
    view.zone.configuration.item_select('Delete this Zone', handle_alert=not cancel)
    if not cancel:
        view.flash.assert_message(f'Zone "{self.name}": Delete successful')


@MiqImplementationContext.external_for(ZoneCollection.create, ViaUI)
def create(self, name=None, description=None, smartproxy_ip=None, ntp_servers=None,
           max_scans=None, user=None, cancel=False):
    add_page = navigate_to(self, 'Add')
    if not ntp_servers:
        ntp_servers = []
    fill_dict = {
        k: v
        for k, v in {
            'name': name,
            'description': description,
            'smartproxy_ip': smartproxy_ip,
            'ntp_server_1': ntp_servers[0] if len(ntp_servers) > 0 else None,
            'ntp_server_2': ntp_servers[1] if len(ntp_servers) > 1 else None,
            'ntp_server_3': ntp_servers[2] if len(ntp_servers) > 2 else None,
            'max_scans': max_scans,
            'user': user.principal if user else None,
            'password': user.secret if user else None,
            'verify': user.secret if user else None
        }.items()
        if v is not None
    }

    add_page.fill(fill_dict)
    if cancel:
        add_page.cancel_button.click()
        add_page.flash.assert_no_error()
        add_page.flash.assert_message('Add of new Zone was cancelled by the user')
        return None
    else:
        add_page.add_button.click()
        add_page.flash.assert_no_error()
        add_page.flash.assert_message(f'Zone "{name}" was added')
    return self.instantiate(
        name=name, description=description, smartproxy_ip=smartproxy_ip,
        ntp_servers=ntp_servers, max_scans=max_scans, user=user
    )


# AUTOMATE
class AutomateSimulationView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Automate", "Simulation"]
        )
    copy = Button("Copy")
    instance = BootstrapSelect('instance_name')
    message = Input(name='object_message')
    request = Input(name='object_request')
    target_type = BootstrapSelect('target_class')
    target_object = BootstrapSelect('target_id')
    execute_methods = Checkbox(name='readonly')
    avp = AttributeValueForm('attribute_', 'value_')

    submit_button = Button(title='Submit Automation Simulation with the specified options')
    reset_button = Button(title="Reset all options")
    cancel_button = Button(title="Cancel Simulation to go back to Button details")
    retry_button = Button(title="Retry state machine simulation, with preserved attributes")

    result_tree = ManageIQTree(tree_id='ae_simulation_treebox')


@navigator.register(Server)
class AutomateSimulation(CFMENavigateStep):
    VIEW = AutomateSimulationView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select(*["Automation", "Automate", "Simulation"])
