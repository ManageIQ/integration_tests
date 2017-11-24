from __future__ import absolute_import
import time
from selenium.webdriver.common.keys import Keys

import re
from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic_manageiq import (ManageIQTree, Checkbox, AttributeValueForm, TimelinesView)
from widgetastic_patternfly import (Accordion, Input, Button, Dropdown,
    FlashMessages, BootstrapSelect, Tab)
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View, Table, Text, Image, FileInput


from cfme.base.login import BaseLoggedInPage
from cfme.base.credential import Credential
from cfme.configure.about import AboutView
from cfme.configure.documentation import DocView
from cfme.configure.tasks import TasksView
from cfme.dashboard import DashboardView
from cfme.intelligence.rss import RSSView
from cfme.exceptions import ZoneNotFound, DestinationNotFound
from cfme.intelligence.chargeback import ChargebackView

from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, ViaUI, navigate_to
from . import Server, Region, Zone, ZoneCollection

from cfme.utils import conf
from cfme.utils.log import logger

from cfme.exceptions import BugException
from cfme.utils.blockers import BZ


@Server.address.external_implementation_for(ViaUI)
def address(self):
    logger.info("USING UI ADDRESS")
    return '{scheme}://{addr}/'.format(scheme=self.appliance.scheme, addr=self.appliance.address)


class LoginPage(View):
    flash = FlashMessages(
        VersionPick({
            Version.lowest(): 'div#flash_text_div',
            '5.8': '//div[@class="flash_text_div"]'
        })
    )

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
        from cfme.configure.access_control import User
        user = User(credential=cred, name='Administrator')
        return self.log_in(user, **kwargs)

    def submit_login(self, method='click_on_login'):
        if method == 'click_on_login':
            self.login.click()
        elif method == 'press_enter_after_password':
            self.browser.send_keys(Keys.ENTER, self.password)
        elif method == '_js_auth_fn':
            self.browser.execute_script('miqAjaxAuth();')
        else:
            raise ValueError('Unknown method {}'.format(method))
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
            self, username, password, new_password, verify_password=None,
            method='click_on_login'):
        self.show_update_password()
        self.fill({
            'username': username,
            'password': password,
            'new_password': new_password,
            'verify_password': verify_password if verify_password is not None else new_password
        })
        self.submit_login(method)

    def logged_in_as_user(self, user):
        return False

    @property
    def logged_in_as_current_user(self):
        return False

    @property
    def current_username(self):
        return None

    @property
    def current_fullname(self):
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


@Server.logged_in.external_implementation_for(ViaUI)
def logged_in(self):
    return self.appliance.browser.create_view(BaseLoggedInPage).logged_in


LOGIN_METHODS = ['click_on_login', 'press_enter_after_password', '_js_auth_fn']


@Server.login.external_implementation_for(ViaUI)
def login(self, user=None, method=LOGIN_METHODS[-1]):
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
        from cfme.configure.access_control import User
        user = User(credential=cred, name='Administrator')

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
        user.name = logged_in_view.current_fullname
        try:
            assert logged_in_view.is_displayed
            assert logged_in_view.logged_in_as_user
            self.appliance.user = user
        except AssertionError:
            login_view.flash.assert_no_error()
    return logged_in_view


@Server.login_admin.external_implementation_for(ViaUI)
def login_admin(self, **kwargs):
    """
    Convenience function to log into CFME using the admin credentials from the yamls.
    Args:
        kwargs: A dict of keyword arguments to supply to the :py:meth:`login` method.
    """
    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    cred = Credential(principal=username, secret=password)
    from cfme.configure.access_control import User
    user = User(credential=cred)
    user.name = 'Administrator'
    logged_in_page = self.login(user, **kwargs)
    return logged_in_page


@Server.logout.external_implementation_for(ViaUI)
def logout(self):
    """
    Logs out of CFME.
    """
    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        logged_in_view.logout()
        self.appliance.user = None


@Server.current_full_name.external_implementation_for(ViaUI)
def current_full_name(self):
    """ Returns the current username.
    Returns: the current username.
    """
    logged_in_view = self.appliance.browser.create_view(BaseLoggedInPage)
    if logged_in_view.logged_in:
        return logged_in_view.current_fullname
    else:
        return None


def automate_menu_name(appliance):
    if appliance.version < '5.8':
        return ['Automate']
    else:
        return ['Automation', 'Automate']


# ######################## SERVER NAVS ################################

@navigator.register(Server)
class LoginScreen(CFMENavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        from cfme.utils.browser import ensure_browser_open
        ensure_browser_open(self.obj.appliance.server.address())

    def step(self):
        # Can be either blank or logged in
        from cfme.utils import browser
        logged_in_view = self.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in:
            logged_in_view.logout()
        if not self.view.is_displayed:
            # Something is wrong
            del self.view  # In order to unbind the browser
            browser.quit()
            browser.ensure_browser_open(self.obj.appliance.server.address())
            if not self.view.is_displayed:
                raise Exception('Could not open the login screen')


@navigator.register(Server)
class LoggedIn(CFMENavigateStep):
    VIEW = BaseLoggedInPage
    prerequisite = NavigateToSibling('LoginScreen')

    def step(self):
        user = self.obj.appliance.user
        self.prerequisite_view.log_in(user)


class ConfigurationView(BaseLoggedInPage):
    flash = FlashMessages(
        './/div[starts-with(@id, "flash_text_div") or starts-with(@class, "flash_text_div")]')
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
            self.accordions.settings.is_displayed and
            self.accordions.accesscontrol.is_displayed and
            self.accordions.diagnostics.is_displayed and
            self.accordions.database.is_displayed)

    @property
    def is_displayed(self):
        # TODO: We will need a better ID of this location when we have user permissions in effect
        return self.in_configuration


@navigator.register(Server)
class Configuration(CFMENavigateStep):
    VIEW = ConfigurationView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            self.prerequisite_view.settings.select_item('Configuration')
            self.prerequisite_view.browser.handle_alert(wait=2, cancel=False, squash=True)
        else:
            self.prerequisite_view.navigation.select('Settings', 'Configuration')


class MySettingsView(BaseLoggedInPage):

    @View.nested
    class tabs(View):  # noqa

        @View.nested
        class visual_all(Tab):  # noqa
            TAB_NAME = "Visual"

        @View.nested
        class default_views(Tab):  # noqa
            TAB_NAME = "Default Views"

        @View.nested
        class default_filter(Tab):  # noqa
            TAB_NAME = "Default Filters"

        @View.nested
        class time_profile(Tab):  # noqa
            TAB_NAME = "Time Profiles"

    @property
    def is_displayed(self):
        return (
            self.tabs.visual_all.is_displayed and
            self.tabs.default_views.is_displayed and
            self.tabs.default_filter.is_displayed and
            self.time_profile.is_displayed)


@navigator.register(Server)
class MySettings(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            self.prerequisite_view.settings.select_item('My Settings')
        else:
            self.prerequisite_view.navigation.select('Settings', 'My Settings')


@navigator.register(Server)
class About(CFMENavigateStep):
    VIEW = AboutView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.prerequisite_view.help.select_item('About')


@navigator.register(Server)
class RSS(CFMENavigateStep):
    VIEW = RSSView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.view.navigation.select('Cloud Intel', 'RSS')


@navigator.register(Server)
class Documentation(CFMENavigateStep):
    VIEW = DocView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.prerequisite_view.help.select_item('Documentation')


@navigator.register(Server)
class Tasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            self.prerequisite_view.settings.select_item('Tasks')
        else:
            self.prerequisite_view.navigation.select('Settings', 'Tasks')


@navigator.register(Server)
class Dashboard(CFMENavigateStep):
    VIEW = DashboardView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Cloud Intel', 'Dashboard')


@navigator.register(Server)
class Chargeback(CFMENavigateStep):
    VIEW = ChargebackView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Cloud Intel', 'Chargeback')


class ServerView(ConfigurationView):
    @View.nested
    class server(Tab):  # noqa
        TAB_NAME = "Server"

    @View.nested
    class authentication(Tab):  # noqa
        TAB_NAME = "Authentication"

    @View.nested
    class workers(Tab):  # noqa
        TAB_NAME = "Workers"
        generic_worker_count = BootstrapSelect("generic_worker_count")
        generic_worker_threshold = BootstrapSelect("generic_worker_threshold")
        cu_data_collector_worker_count = BootstrapSelect("ems_metrics_collector_worker_count")
        cu_data_collector_worker_threshold = BootstrapSelect(
            "ems_metrics_collector_worker_threshold")
        event_monitor_worker_threshold = BootstrapSelect("event_catcher_threshold")
        connection_broker_worker_threshold = BootstrapSelect("vim_broker_worker_threshold")
        ui_worker_count = BootstrapSelect("ui_worker_count")
        reporting_worker_count = BootstrapSelect("reporting_worker_count")
        reporting_worker_threshold = BootstrapSelect("reporting_worker_threshold")
        web_service_worker_count = BootstrapSelect("web_service_worker_count")
        web_service_worker_threshold = BootstrapSelect("web_service_worker_threshold")
        priority_worker_count = BootstrapSelect("priority_worker_count")
        priority_worker_threshold = BootstrapSelect("priority_worker_threshold")
        cu_data_processor_worker_count = BootstrapSelect("ems_metrics_processor_worker_count")
        cu_data_processor_worker_threshold = BootstrapSelect(
            "ems_metrics_processor_worker_threshold")
        refresh_worker_threshold = BootstrapSelect("ems_refresh_worker_threshold")
        vm_analysis_collectors_worker_count = BootstrapSelect("proxy_worker_count")
        vm_analysis_collectors_worker_threshold = BootstrapSelect("proxy_worker_threshold")
        websocket_worker_count = BootstrapSelect("websocket_worker_count")

        save = Button('Save')
        reset = Button('Reset')

    @View.nested
    class customlogos(Tab):  # noqa
        TAB_NAME = "Custom Logos"

    @View.nested
    class advanced(Tab):  # noqa
        TAB_NAME = "Advanced"

    @property
    def is_displayed(self):
        if not self.in_configuration:
            return False
        if not self.view.accordions.settings.is_displayed:
            return False
        return self.view.accordions.settings.tree.currently_selected == [
            self.context['object'].zone.region.settings_string,
            "Zones",
            "Zone: {} (current)".format(self.context['object'].zone.description),
            "Server: {} [{}] (current)".format(self.context['object'].name,
                self.context['object'].sid)]


@navigator.register(Server)
class Details(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Configuration')

    def step(self):
        self.prerequisite_view.accordions.settings.tree.click_path(
            self.obj.zone.region.settings_string,
            "Zones",
            "Zone: {} (current)".format(self.obj.appliance.zone_description),
            "Server: {} [{}] (current)".format(self.obj.appliance.server_name(),
                self.obj.sid))


@navigator.register(Server, 'Server')
class ServerDetails(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.server.is_displayed and self.view.server.is_active)

    def step(self):
        self.prerequisite_view.server.select()


@navigator.register(Server)
class Authentication(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.authentication.is_displayed and
            self.view.authentication.is_active)

    def step(self):
        self.prerequisite_view.authentication.select()


@navigator.register(Server)
class Workers(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.workers.is_displayed and
            self.view.workers.is_active)

    def step(self):
        self.prerequisite_view.workers.select()


@navigator.register(Server)
class CustomLogos(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.custom_logos.is_displayed and
            self.view.custom_logos.is_active)

    def step(self):
        self.prerequisite_view.customlogos.select()


@navigator.register(Server)
class Advanced(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.advanced.is_displayed and
            self.view.advanced.is_active)

    def step(self):
        self.prerequisite_view.advanced.select()


class ServerDiagnosticsView(ConfigurationView):
    @View.nested
    class summary(Tab):  # noqa
        TAB_NAME = "Summary"

    @View.nested
    class workers(Tab):  # noqa
        TAB_NAME = "Workers"

    @View.nested
    class collectlogs(Tab):  # noqa
        TAB_NAME = "Collect Logs"

    @View.nested
    class cfmelog(Tab):  # noqa
        TAB_NAME = "CFME Log"

    @View.nested
    class auditlog(Tab):  # noqa
        TAB_NAME = "Audit Log"

    @View.nested
    class productionlog(Tab):  # noqa
        TAB_NAME = "Production Log"

    @View.nested
    class utilization(Tab):  # noqa
        TAB_NAME = "Utilization"

    @View.nested
    class timelines(Tab, TimelinesView):  # noqa
        TAB_NAME = "Timelines"

    configuration = Dropdown('Configuration')

    @property
    def is_displayed(self):
        return self.prerequisite_view.accordions.diagnostics.tree.currently_selected == [
            self.context['object'].zone.region.settings_string,
            "Zone: {} (current)".format(self.context['object'].zone.description),
            "Server: {} [{}] (current)".format(
                self.context['object'].name, self.context['object'].sid)]


@navigator.register(Server)
class Diagnostics(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Configuration')

    def step(self):
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            self.obj.zone.region.settings_string,
            "Zone: {} (current)".format(self.obj.zone.description),
            "Server: {} [{}] (current)".format(
                self.obj.name, self.obj.sid))


@navigator.register(Server)
class DiagnosticsDetails(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.summary.is_displayed and
            self.view.summary.is_active)

    def step(self):
        self.prerequisite_view.summary.select()


@navigator.register(Server)
class DiagnosticsWorkers(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.workers.is_displayed and
            self.view.workers.is_active)

    def step(self):
        self.prerequisite_view.workers.select()


@navigator.register(Server)
class CFMELog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.cfmelog.is_displayed and
            self.view.cfmelog.is_active)

    def step(self):
        self.prerequisite_view.cfmelog.select()


@navigator.register(Server)
class AuditLog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.auditlog.is_displayed and
            self.view.auditlog.is_active)

    def step(self):
        self.prerequisite_view.auditlog.select()


@navigator.register(Server)
class ProductionLog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.productionlog.is_displayed and
            self.view.productionlog.is_active)

    def step(self):
        self.prerequisite_view.productionlog.select()


@navigator.register(Server)
class Utilization(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.utilization.is_displayed and
            self.view.utilization.is_active)

    def step(self):
        self.prerequisite_view.utilization.select()


@navigator.register(Server)
class Timelines(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return (
            self.view.is_displayed and self.view.timelines.is_displayed and
            self.view.timelines.is_active)

    def step(self):
        self.prerequisite_view.timelines.select()


# ######################## REGION NAVS ################################
class CompanyCategories(Tab):
    TAB_NAME = "My Company Categories"


class CompanyTags(Tab):
    TAB_NAME = "My Company Tags"


class ImportTags(Tab):
    TAB_NAME = "Import Tags"


class MapTags(Tab):
    TAB_NAME = "Map Tags"


class ImportVariable(Tab):
    TAB_NAME = "Import Variables"


class TagsView(Tab):
    TAB_NAME = "Tags"

    company_categories = View.nested(CompanyCategories)
    company_tags = View.nested(CompanyTags)
    import_tags = View.nested(ImportTags)
    map_tags = View.nested(MapTags)
    imports = View.nested(ImportVariable)


class RegionView(ConfigurationView):
    @View.nested
    class details(Tab):  # noqa
        TAB_NAME = "Details"

    @View.nested
    class candu_collection(Tab):  # noqa
        TAB_NAME = "C & U Collection"

    @View.nested
    class redhat_updates(Tab):  # noqa
        TAB_NAME = "Red Hat Updates"

    @View.nested
    class imports(Tab):  # noqa
        TAB_NAME = "Import"

    @View.nested
    class replication(Tab):  # noqa
        TAB_NAME = "Replication"

    company_categories = View.nested(CompanyCategories)
    company_tags = View.nested(CompanyTags)
    import_tags = View.nested(ImportTags)
    map_tags = View.nested(MapTags)

    # available starting from 5.9 version, not available in 5.7, 5.8
    tags = View.nested(TagsView)

    @property
    def is_displayed(self):
        return self.accordions.settings.tree.currently_selected == [self.obj.settings_string]


@navigator.register(Region, 'Details')
class RegionDetails(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        # TODO: This string can now probably be built up with the relevant server, zone,
        # region objects
        self.prerequisite_view.accordions.settings.tree.click_path(self.obj.settings_string)
        self.view.details.select()


@navigator.register(Region)
class ImportTags(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.importtags.select()


@navigator.register(Region)
class Import(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.imports.select()


class ZoneListView(ConfigurationView):
    configuration = Dropdown('Configuration')
    table = Table('//div[@id="settings_list"]/table')

    @property
    def is_displayed(self):
        return (
            self.accordions.settings.is_opened and
            self.accordions.settings.tree.currently_selected == [
                self.context['object'].settings_string, 'Zones'] and
            self.title.text == 'Settings Zones' and
            self.table.is_displayed)


@navigator.register(Region, 'Zones')
class RegionZones(CFMENavigateStep):
    VIEW = ZoneListView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.settings.tree.click_path(
            self.obj.settings_string, 'Zones')
        if not self.view.is_displayed:
            # Zones is too smart and does not reload upon clicking, this helps
            self.prerequisite_view.accordions.accesscontrol.open()
            self.prerequisite_view.accordions.settings.tree.click_path(
                self.obj.settings_string, 'Zones')


class RegionDiagnosticsView(ConfigurationView):
    @View.nested
    class zones(Tab):  # noqa
        TAB_NAME = "Zones"

    @View.nested
    class rolesbyservers(Tab):  # noqa
        TAB_NAME = "Roles by Servers"

    @View.nested
    class replication(Tab):  # noqa
        TAB_NAME = "Replication"

    @View.nested
    class serversbyroles(Tab):  # noqa
        TAB_NAME = "Servers by Roles"

    @View.nested
    class servers(Tab):  # noqa
        TAB_NAME = "Servers"

    @View.nested
    class database(Tab):  # noqa
        TAB_NAME = "Database"

    @View.nested
    class orphaneddata(Tab):  # noqa
        TAB_NAME = "Orphaned Data"

    @property
    def is_displayed(self):
        return (
            self.accordions.diagnostics.is_opened and
            self.accordions.diagnostics.tree.currently_selected == [
                self.context['object'].settings_string] and
            self.title.text.startswith('Diagnostics Region '))


@navigator.register(Region, 'Diagnostics')
class RegionDiagnostics(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.diagnostics.tree.click_path(self.obj.settings_string)


@navigator.register(Region, 'DiagnosticsZones')
class RegionDiagnosticsZones(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.zones.select()


@navigator.register(Region, 'RolesByServers')
class RegionDiagnosticsRolesByServers(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.rolesbyservers.select()


@navigator.register(Region, 'Replication')
class RegionDiagnosticsReplication(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self):
        if self.obj.appliance.version < '5.7':
            self.prerequisite_view.replication.select()
        else:
            raise DestinationNotFound('Replication destination is absent in 5.7')


@navigator.register(Region, 'ServersByRoles')
class RegionDiagnosticsServersByRoles(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.serversbyroles.select()


@navigator.register(Region, 'Servers')
class RegionDiagnosticsServers(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.servers.select()


@navigator.register(Region, 'Database')
class RegionDiagnosticsDatabase(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.database.select()


@navigator.register(Region, 'OrphanedData')
class RegionDiagnosticsOrphanedData(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def am_i_here(self):
        return False

    def step(self):
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


# Zone Details #
class ZoneDetailsView(ConfigurationView):
    configuration = Dropdown('Configuration')

    @property
    def is_displayed(self):
        return self.title.text.startswith(
            'Settings Zone "{}"'.format(self.context['object'].description))


@navigator.register(Zone, 'Details')
class ZoneDetails(CFMENavigateStep):
    VIEW = ZoneDetailsView

    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Zones')

    def step(self):
        rows = self.prerequisite_view.table.rows((1, re.compile(r'Zone\s?\:\s?{}'.format(
            self.obj.description))))
        for row in rows:
            row.click()
            break
        else:
            raise ZoneNotFound(
                "No unique Zones with the description '{}'".format(self.obj.description))


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

    def step(self):
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
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Zone")


# Zone Diags #
class ZoneDiagnosticsView(ConfigurationView):
    @View.nested
    class rolesbyservers(Tab):  # noqa
        TAB_NAME = "Roles by Servers"

    @View.nested
    class serversbyroles(Tab):  # noqa
        TAB_NAME = "Servers by Roles"

    @View.nested
    class servers(Tab):  # noqa
        TAB_NAME = "Servers"

    @View.nested
    class collectlogs(Tab):  # noqa
        TAB_NAME = "Collect Logs"

    @View.nested
    class candugapcollection(Tab):  # noqa
        TAB_NAME = "C & U Gap Collection"

    @property
    def is_displayed(self):
        return (
            self.title.text == 'Diagnostics Zone "{}" (current)'.format(
                self.context['object'].description))


@navigator.register(Zone, 'Diagnostics')
class ZoneDiagnostics(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            self.obj.region.settings_string,
            "Zone: {} (current)".format(self.obj.description))


@navigator.register(Zone, 'RolesByServers')
class ZoneDiagnosticsRolesByServers(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.prerequisite_view.rolesbyservers.select()


@navigator.register(Zone, 'ServersByRoles')
class ZoneDiagnosticsServersByRoles(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.prerequisite_view.serversbyroles.select()


@navigator.register(Zone, 'Servers')
class ZoneDiagnosticsServers(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.prerequisite_view.servers.select()


@navigator.register(Zone, 'CANDUGapCollection')
class ZoneCANDUGapCollection(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.prerequisite_view.candugapcollection.select()


@Zone.exists.external_getter_implemented_for(ViaUI)
def exists(self):
    try:
        navigate_to(self, 'Details')
        return True
    except ZoneNotFound:
        return False


@Zone.update.external_implementation_for(ViaUI)
def update(self, updates):
    view = navigate_to(self, 'Edit')
    changed = view.fill(updates)
    if changed:
        view.save_button.click()
    else:
        view.cancel_button.click()
    view = self.create_view(ZoneDetailsView)
    # assert view.is_displayed
    view.flash.assert_no_error()
    if changed:
        view.flash.assert_message(
            'Zone "{}" was saved'.format(updates.get('name', self.name)))
    else:
        view.flash.assert_message(
            'Edit of Zone "{}" was cancelled by the user'.format(self.name))


@Zone.delete.external_implementation_for(ViaUI)
def delete(self, cancel=False):
    """ Delete the Zone represented by this object.

    Args:
        cancel: Whether to click on the cancel button in the pop-up.
    """
    view = navigate_to(self, 'Details')
    view.configuration.item_select('Delete this Zone', handle_alert=not cancel)
    if not cancel:
        view.flash.assert_message('Zone "{}": Delete successful'.format(self.name))


@ZoneCollection.create.external_implementation_for(ViaUI)
def create(self, name=None, description=None, smartproxy_ip=None, ntp_servers=None,
           max_scans=None, user=None, cancel=False):

    if BZ(1509452).blocks:
        raise BugException(1509452, 'creating zones')

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
        if v is not None}

    add_page.fill(fill_dict)
    if cancel:
        add_page.cancel_button.click()
        add_page.flash.assert_no_error()
        add_page.flash.assert_message('Add of new Zone was cancelled by the user')
        return None
    else:
        add_page.add_button.click()
        add_page.flash.assert_no_error()
        add_page.flash.assert_message('Zone "{}" was added'.format(name))
    return self.instantiate(
        region=self.region, name=name, description=description, smartproxy_ip=smartproxy_ip,
        ntp_servers=ntp_servers, max_scans=max_scans, user=user
    )


# AUTOMATE
class AutomateSimulationView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == automate_menu_name(
                self.context['object'].appliance) + ['Simulation'])

    instance = BootstrapSelect('instance_name')
    message = Input(name='object_message')
    request = Input(name='object_request')
    target_type = BootstrapSelect('target_class')
    target_object = BootstrapSelect('target_id')
    execute_methods = Checkbox(name='readonly')
    avp = AttributeValueForm('attribute_', 'value_')

    submit_button = Button(title='Submit Automation Simulation with the specified options')

    result_tree = ManageIQTree(tree_id='ae_simulation_treebox')


@navigator.register(Server)
class AutomateSimulation(CFMENavigateStep):
    VIEW = AutomateSimulationView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select(
            *automate_menu_name(self.obj.appliance) + ['Simulation'])


class AutomateImportExportBaseView(BaseLoggedInPage):
    flash = FlashMessages('div.import-flash-message')
    title = Text('.//div[@id="main-content"]//h1')

    @property
    def in_import_export(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == automate_menu_name(
                self.context['object'].appliance) + ['Import / Export'] and
            self.title.text == 'Import / Export')

    @property
    def is_displayed(self):
        return self.in_import_export


class AutomateImportExportView(AutomateImportExportBaseView):
    class import_file(View):    # noqa
        file = FileInput(name='upload_file')
        upload = Button('Upload')

    class import_git(View):     # noqa
        ROOT = './/form[@id="retrieve-git-datastore-form"]'

        url = Input(name='git_url')
        username = Input(name='git_username')
        password = Input(name='git_password')
        verify_ssl = Checkbox(name='git_verify_ssl')
        submit = Button(id='git-url-import')

    export_all = Image('.//input[@title="Export all classes and instances"]')
    reset_all = Image('.//img[starts-with(@alt, "Reset all components in the following domains:")]')

    @property
    def is_displayed(self):
        return self.in_import_export and self.export_all.is_displayed


@navigator.register(Server)
class AutomateImportExport(CFMENavigateStep):
    VIEW = AutomateImportExportView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select(
            *automate_menu_name(self.obj.appliance) + ['Import / Export'])
