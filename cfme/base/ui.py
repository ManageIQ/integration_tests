import re

from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic_manageiq import ManageIQTree
from widgetastic_patternfly import (Accordion, Input, Button, Dropdown,
    FlashMessages, BootstrapSelect, Tab)
from widgetastic.widget import View, Table

from cfme import BaseLoggedInPage
from cfme.dashboard import DashboardView
from cfme.exceptions import ZoneNotFound
from cfme.login import LoginPage

from utils.appliance.implementations.ui import navigator, CFMENavigateStep, ViaUI, navigate_to

from . import Server, Region, Zone, ZoneCollection


# ######################## SERVER NAVS ################################

@navigator.register(Server)
class LoginScreen(CFMENavigateStep):
    VIEW = LoginPage

    def prerequisite(self):
        from utils.browser import ensure_browser_open
        ensure_browser_open()

    def step(self):
        # Can be either blank or logged in
        from utils.browser import ensure_browser_open
        logged_in_view = self.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in:
            logged_in_view.logout()
        if not self.view.is_displayed:
            # Something is wrong
            del self.view  # In order to unbind the browser
            quit()
            ensure_browser_open()
            if not self.view.is_displayed:
                raise Exception('Could not open the login screen')


@navigator.register(Server)
class LoggedIn(CFMENavigateStep):
    VIEW = BaseLoggedInPage
    prerequisite = NavigateToSibling('LoginScreen')

    def am_i_here(self):
        return self.view.is_displayed

    def step(self):
        login_view = self.create_view(LoginPage)
        user = self.obj.appliance.user
        login_view.log_in(user)


class ConfigurationView(BaseLoggedInPage):
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')

    @View.nested
    class accordions(View):  # noqa

        @View.nested
        class settings(Accordion):  # noqa
            ACCORDION_NAME = "Settings"
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
    def is_displayed(self):
        # TODO this needs fixing
        return False


@navigator.register(Server)
class Configuration(CFMENavigateStep):
    VIEW = ConfigurationView
    prerequisite = NavigateToSibling('LoggedIn')

    def am_i_here(self):
        # TODO move this to using match_location once it uses widgetastic
        return self.obj.appliance.browser.widgetastic.execute_script(
            'return ManageIQ.controller;') == 'ops'

    def step(self):
        if self.obj.appliance.version > '5.7':
            self.view.settings.select_item('Settings')
        else:
            self.view.navigation.select('Settings', 'Configuration')


@navigator.register(Server)
class MySettings(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_top_right
            click_top_right('My Settings')
        else:
            from cfme.web_ui.menu import nav
            nav._nav_to_fn('Settings', 'My Settings')(None)


@navigator.register(Server)
class About(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_help
            click_help('About')
        else:
            from cfme.web_ui.menu import nav
            nav._nav_to_fn('Settings', 'About')(None)


@navigator.register(Server)
class Documentation(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_help
            click_help('Documentation')
        else:
            from cfme.web_ui.menu import nav
            nav._nav_to_fn('Settings', 'About')(None)


@navigator.register(Server)
class Dashboard(CFMENavigateStep):
    VIEW = DashboardView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.view.navigation.select('Cloud Intel', 'Dashboard')


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

    @View.nested
    class customlogos(Tab):  # noqa
        TAB_NAME = "Custom Logos"

    @View.nested
    class advanced(Tab):  # noqa
        TAB_NAME = "Advanced"


@navigator.register(Server)
class Details(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Configuration')

    def step(self):
        self.view.accordions.settings.tree.click_path(
            self.obj.zone.region.settings_string,
            "Zones",
            "Zone: {} (current)".format(self.obj.zone.description),
            "Server: {} [{}] (current)".format(self.obj.name,
                self.obj.sid))


@navigator.register(Server, 'Server')
class ServerDetails(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.server.select()


@navigator.register(Server)
class Authentication(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.authentication.select()


@navigator.register(Server)
class Workers(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.workers.select()


@navigator.register(Server)
class CustomLogos(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.customlogos.select()


@navigator.register(Server)
class Advanced(CFMENavigateStep):
    VIEW = ServerView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.advanced.select()


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
    class timelines(Tab):  # noqa
        TAB_NAME = "Timelines"

    configuration = Dropdown('Configuration')


@navigator.register(Server)
class Diagnostics(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Configuration')

    def step(self):
        self.view.accordions.diagnostics.tree.click_path(
            self.obj.zone.region.settings_string,
            "Zone: {} (current)".format(self.obj.zone.description),
            "Server: {} [{}] (current)".format(
                self.obj.name, self.obj.sid))


@navigator.register(Server)
class DiagnosticsDetails(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.summary.select()


@navigator.register(Server)
class DiagnosticsWorkers(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.workers.select()


class DiagnosticsCollectLogsView(ServerDiagnosticsView):
    edit = Button(title="Edit the Log Depot settings for the selected Server")


@navigator.register(Server)
class DiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = DiagnosticsCollectLogsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.collectlogs.select()


@navigator.register(Server)
class DiagnosticsLogsSettings(CFMENavigateStep):
    VIEW = DiagnosticsCollectLogsView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogs')

    def step(self):
        self.view.edit.click()


@navigator.register(Server)
class CFMELog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.cfmelog.select()


@navigator.register(Server)
class AuditLog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.auditlog.select()


@navigator.register(Server)
class ProductionLog(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.productionlog.select()


@navigator.register(Server)
class Utilization(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.utilization.select()


@navigator.register(Server)
class Timelines(CFMENavigateStep):
    VIEW = ServerDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.timelines.select()


# ######################## REGION NAVS ################################

class RegionView(ConfigurationView):
    @View.nested
    class details(Tab):  # noqa
        TAB_NAME = "Details"

    @View.nested
    class canducollection(Tab):  # noqa
        TAB_NAME = "C & U Collection"

    @View.nested
    class redhatupdates(Tab):  # noqa
        TAB_NAME = "Red Hat Updates"

    @View.nested
    class imports(Tab):  # noqa
        TAB_NAME = "Import"

    @View.nested
    class importtags(Tab):  # noqa
        TAB_NAME = "Import Tags"


@navigator.register(Region, 'Details')
class RegionDetails(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        # TODO: This string can now probably be built up with the relevant server, zone,
        # region objects
        self.view.accordions.settings.tree.click_path(self.obj.settings_string)
        self.view.details.select()


@navigator.register(Region)
class CANDUCollection(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.canducollection.select()


@navigator.register(Region)
class RedHatUpdates(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.redhatupdates.select()


@navigator.register(Region)
class ImportTags(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.importtags.select()


@navigator.register(Region)
class Import(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.view.imports.select()


@navigator.register(Region, 'Zones')
class RegionZones(CFMENavigateStep):
    VIEW = ConfigurationView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.view.accordions.settings.tree.click_path(self.obj.settings_string, 'Zones')


class RegionDiagnosticsView(ConfigurationView):
    @View.nested
    class zones(Tab):  # noqa
        TAB_NAME = "Zones"

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
    class database(Tab):  # noqa
        TAB_NAME = "Database"

    @View.nested
    class orphaneddata(Tab):  # noqa
        TAB_NAME = "Orphaned Data"


@navigator.register(Region, 'Diagnostics')
class RegionDiagnostics(CFMENavigateStep):
    VIEW = ConfigurationView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.view.accordions.diagnostics.tree.click_path(self.obj.settings_string)


@navigator.register(Region, 'DiagnosticsZones')
class RegionDiagnosticsZones(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.zones.select()


@navigator.register(Region, 'RolesByServers')
class RegionDiagnosticsRolesByServers(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.rolesbyservers.select()


@navigator.register(Region, 'ServersByRoles')
class RegionDiagnosticsServersByRoles(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.serversbyroles.select()


@navigator.register(Region, 'Servers')
class RegionDiagnosticsServers(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.servers.select()


@navigator.register(Region, 'Database')
class RegionDiagnosticsDatabase(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.database.select()


@navigator.register(Region, 'OrphanedData')
class RegionDiagnosticsOrphanedData(CFMENavigateStep):
    VIEW = RegionDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.orphaneddata.select()


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


class ZoneListView(ConfigurationView):
    configuration = Dropdown('Configuration')
    table = Table('//div[@id="settings_list"]/table')


# Zone Details #
class ZoneDetailsView(ConfigurationView):
    configuration = Dropdown('Configuration')


@navigator.register(Zone, 'Details')
class ZoneDetails(CFMENavigateStep):
    VIEW = ZoneDetailsView

    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Zones')

    def step(self):
        view = self.create_view(ZoneListView)
        rows = view.table.rows((1, re.compile(r'Zone\s?\:\s?{}'.format(
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


@navigator.register(ZoneCollection, 'Add')
class ZoneAdd(CFMENavigateStep):
    VIEW = ZoneAddView
    prerequisite = NavigateToAttribute('appliance.server.zone.region', 'Zones')

    def step(self):
        view = self.create_view(ZoneListView)
        view.configuration.item_select("Add a new Zone")


# Zone Edit #
class ZoneEditView(ZoneForm):
    save_button = Button('Save')


@navigator.register(Zone, 'Edit')
class ZoneEdit(CFMENavigateStep):
    VIEW = ZoneEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        view = self.create_view(ZoneDetailsView)
        view.configuration.item_select("Edit this Zone")


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


@navigator.register(Zone, 'Diagnostics')
class ZoneDiagnostics(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        self.view.accordions.diagnostics.tree.click_path(
            self.obj.region.settings_string,
            "Zone: {} (current)".format(self.obj.description))


@navigator.register(Zone, 'RolesByServers')
class ZoneDiagnosticsRolesByServers(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.rolesbyservers.select()


@navigator.register(Zone, 'ServersByRoles')
class ZoneDiagnosticsServersByRoles(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.serversbyroles.select()


@navigator.register(Zone, 'Servers')
class ZoneDiagnosticsServers(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.servers.select()


@navigator.register(Zone, 'CollectLogs')
class ZoneZoneCollectLogs(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.collectlogs.select()


@navigator.register(Zone, 'CANDUGapCollection')
class ZoneCANDUGapCollection(CFMENavigateStep):
    VIEW = ZoneDiagnosticsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.view.candugapcollection.select()


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
    return Zone(appliance=self.appliance, region=self.region,
        name=name, description=description, smartproxy_ip=smartproxy_ip,
        ntp_servers=ntp_servers, max_scans=max_scans, user=user)
