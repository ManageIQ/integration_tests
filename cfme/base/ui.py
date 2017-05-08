import re
from navmazing import NavigateToSibling, NavigateToAttribute

from widgetastic_manageiq import ManageIQTree, Checkbox, AttributeValueForm, SummaryFormItem
from widgetastic_patternfly import (Accordion, Input, Button, Dropdown,
    FlashMessages, BootstrapSelect, Tab)
from widgetastic.utils import Version, VersionPick
from widgetastic.widget import View, Table, Text

from cfme import BaseLoggedInPage
from cfme.configure.tasks import TasksView
from cfme.dashboard import DashboardView
from cfme.intelligence.rss import RSSView
from cfme.exceptions import ZoneNotFound, DestinationNotFound
from cfme.intelligence.chargeback import ChargebackView
from cfme.login import LoginPage

from utils.appliance.implementations.ui import navigator, CFMENavigateStep, ViaUI, navigate_to
from . import Server, Region, Zone, ZoneCollection


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
        from utils.browser import ensure_browser_open
        ensure_browser_open()

    def step(self):
        # Can be either blank or logged in
        from utils import browser
        logged_in_view = self.create_view(BaseLoggedInPage)
        if logged_in_view.logged_in:
            logged_in_view.logout()
        if not self.view.is_displayed:
            # Something is wrong
            del self.view  # In order to unbind the browser
            browser.quit()
            browser.ensure_browser_open()
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
    flash = FlashMessages('.//div[starts-with(@id, "flash_text_div")]')
    title = Text('#explorer_title_text')

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
        # TODO: We will need a better ID of this location when we have user permissions in effect
        return (
            self.accordions.settings.is_displayed and
            self.accordions.accesscontrol.is_displayed and
            self.accordions.diagnostics.is_displayed and
            self.accordions.database.is_displayed)


@navigator.register(Server)
class Configuration(CFMENavigateStep):
    VIEW = ConfigurationView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            self.prerequisite_view.settings.select_item('Configuration')
        else:
            self.prerequisite_view.navigation.select('Settings', 'Configuration')


@navigator.register(Server)
class MySettings(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_top_right
            click_top_right('My Settings')
        else:
            self.prerequisite_view.navigation.select('Settings', 'My Settings')


@navigator.register(Server)
class About(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_help
            click_help('About')
        else:
            self.prerequisite_view.navigation.select('Settings', 'About')


@navigator.register(Server)
class RSS(CFMENavigateStep):
    VIEW = RSSView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        self.view.navigation.select('Cloud Intel', 'RSS')


@navigator.register(Server)
class Documentation(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_help
            click_help('Documentation')
        else:
            self.prerequisite_view.navigation.select('Settings', 'About')


@navigator.register(Server)
class Tasks(CFMENavigateStep):
    VIEW = TasksView
    prerequisite = NavigateToSibling('LoggedIn')

    def step(self):
        if self.obj.appliance.version > '5.7':
            from cfme.dashboard import click_top_right
            click_top_right('Tasks')
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

    @View.nested
    class customlogos(Tab):  # noqa
        TAB_NAME = "Custom Logos"

    @View.nested
    class advanced(Tab):  # noqa
        TAB_NAME = "Advanced"

    @property
    def is_displayed(self):
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
            "Zone: {} (current)".format(self.obj.zone.description),
            "Server: {} [{}] (current)".format(self.obj.name,
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
    class timelines(Tab):  # noqa
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


class DiagnosticsCollectLogsView(ServerDiagnosticsView):
    title = Text('#explorer_title_text')

    edit = Button(title="Edit the Log Depot settings for the selected Server")
    collect = Dropdown(VersionPick({Version.lowest(): 'Collect Logs',
                       '5.7': 'Collect'}))

    log_depot_uri = SummaryFormItem('Basic Info', 'Log Depot URI')
    last_log_collection = SummaryFormItem('Basic Info', 'Last Log Collection')
    last_log_message = SummaryFormItem('Basic Info', 'Last Message')

    @property
    def is_displayed(self):
        return (
            super(DiagnosticsCollectLogsView, self).is_displayed and
            self.collectlogs.is_displayed and
            self.collectlogs.is_active and
            self.title.text == 'Diagnostics Server "{} [{}]" (current)'.format(
                self.context['object'].name, self.context['object'].sid))


class ZoneDiagnosticsCollectLogsView(DiagnosticsCollectLogsView):
    edit = Button(title="Edit the Log Depot settings for the selected Zone")

    @property
    def is_displayed(self):
        return (
            self.collectlogs.is_displayed and
            self.collectlogs.is_active and
            self.title.text == 'Diagnostics Zone "{}" (current)'.format(
                self.context['object'].description))


@navigator.register(Server, "DiagnosticsCollectLogs")
class DiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = DiagnosticsCollectLogsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.prerequisite_view.collectlogs.select()


@navigator.register(Server, "DiagnosticsCollectLogsSlave")
class DiagnosticsCollectLogsSlave(CFMENavigateStep):
    VIEW = DiagnosticsCollectLogsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.prerequisite_view.accordions.diagnostics.tree.click_path(
            self.appliance.server_region_string(),
            "Zone: {} (current)".format(self.appliance.zone_description),
            "Server: {} [{}]".format(self.appliance.slave_server_name(),
                                     self.appliance.slave_server_zone_id()))
        self.prerequisite_view.collectlogs.select()


class DiagnosticsCollectLogsEditView(DiagnosticsCollectLogsView):

    @property
    def is_displayed(self):
        return super(DiagnosticsCollectLogsView, self).is_displayed and self.protocol.is_displayed

    depot_type = BootstrapSelect('log_protocol')
    depot_name = Input('depot_name')
    uri = Input('uri')
    username = Input(name='log_userid')
    password = Input(name='log_password')
    confirm_password = Input(name='log_verify')
    validate = Button('Validate')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


@navigator.register(Server, "DiagnosticsCollectLogsEdit")
class DiagnosticsCollectLogsEdit(CFMENavigateStep):
    VIEW = DiagnosticsCollectLogsEditView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogs')

    def step(self):
        self.prerequisite_view.edit.click()


@navigator.register(Server, "DiagnosticsCollectLogsEditSlave")
class DiagnosticsCollectLogsEditSlave(CFMENavigateStep):
    VIEW = DiagnosticsCollectLogsEditView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogsSlave')

    def step(self):
        self.prerequisite_view.edit.click()


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
class CANDUCollection(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.canducollection.select()


@navigator.register(Region)
class RedHatUpdates(CFMENavigateStep):
    VIEW = RegionView
    prerequisite = NavigateToSibling('Details')

    def am_i_here(self):
        return False

    def step(self):
        self.prerequisite_view.redhatupdates.select()


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


@navigator.register(Zone, 'DiagnosticsCollectLogs')
class ZoneDiagnosticsCollectLogs(CFMENavigateStep):
    VIEW = ZoneDiagnosticsCollectLogsView
    prerequisite = NavigateToSibling('Diagnostics')

    def step(self):
        self.prerequisite_view.collectlogs.select()


@navigator.register(Zone, 'DiagnosticsCollectLogsEdit')
class ZoneDiagnosticsCollectLogsEdit(CFMENavigateStep):
    VIEW = DiagnosticsCollectLogsEditView
    prerequisite = NavigateToSibling('DiagnosticsCollectLogs')

    def step(self):
        self.prerequisite_view.edit.click()


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


# AUTOMATE
class AutomateSimulationView(BaseLoggedInPage):
    @property
    def is_displayed(self):
        from cfme.automate import automate_menu_name
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
        from cfme.automate import automate_menu_name
        self.prerequisite_view.navigation.select(
            *automate_menu_name(self.obj.appliance) + ['Simulation'])
