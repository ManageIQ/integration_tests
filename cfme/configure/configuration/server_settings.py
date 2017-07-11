
from cfme.base.ui import Server,  ConfigurationView
from fixtures.pytest_store import store
from navmazing import NavigateToAttribute, NavigateToSibling
from utils.appliance import Navigatable, current_appliance
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.pretty import Pretty
from utils.update import Updateable
from widgetastic_patternfly import Tab, Input, BootstrapSelect, Button
from widgetastic.widget import View, Text


class ServerSettingsView(ConfigurationView):
    """
        Represents Server Settings page in CFME UI
    """
    title = Text('explorer_title_text')
    save_button = Button('Save')
    reset_button = Button('Reset')

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
    class custom_logos(Tab):  # noqa
        TAB_NAME = "Custom Logos"

    @View.nested
    class advanced(Tab):  # noqa
        TAB_NAME = "Advanced"

    @property
    def is_displayed(self):
        return (
            self.accordions.settings.is_displayed and
            self.accordions.accesscontrol.is_displayed and
            self.accordions.diagnostics.is_displayed and
            self.accordions.database.is_displayed and
            self.server.is_displayed
        )

@navigator.register(Server, 'Server Settings')
class ServerSettings(CFMENavigateStep):
    VIEW = ServerSettingsView
    prerequisite = NavigateToAttribute('appliance.server', 'Configuration')

    def step(self):
        server_region = store.current_appliance.server_region_string()
        self.prerequisite_view.accordions.settings.tree.click_path(server_region, 'Server')


class ServerBasicInformationform(ServerSettingsView):
    title = Text("//div[@id='settings_server']/h3[1]")

    company_name = Input(name='server_company')
    appliance_name = Input(name='server_name')
    appliance_zone = Input('server_zone')
    time_zone = BootstrapSelect(id='server_timezone')
    locale = BootstrapSelect(id='locale')


class ServerInformation(Updateable, Pretty, Navigatable):
    pretty_attrs = ['company_name', 'appliance_name', 'appliance_zone', 'time_zone', 'appliance']

    def __init__(self, company_name=None, appliance_name=None, appliance_zone=None, time_zone=None,
                 appliance=None):
        assert (
            company_name or
            appliance_name or
            appliance_zone or
            time_zone), "You must provide at least one param!"
        self.company_name = company_name
        self.appliance_name = appliance_name
        self.appliance_zone = appliance_zone
        self.time_zone = time_zone
        Navigatable.__init__(self, appliance=appliance)

    def update_basic_information(self):
        """ Navigate to a correct page, change details and save.
        """
        view = navigate_to(current_appliance.server, 'Server Settings')
        view.fill(self.basic_information)
        view.save_button.click()
        self.appliance.server_details_changed()


@navigator.register(ServerInformation, 'Details')
class ServerInformationDetails(CFMENavigateStep):
    VIEW = ServerSettingsView
    prerequisite = NavigateToSibling('Server Settings')

    def step(self):
        self.server.select()


@navigator.register(ServerInformation, 'Authentication')
class ServerInformationDetails(CFMENavigateStep):
    VIEW = ServerSettingsView
    prerequisite = NavigateToSibling('Server Settings')

    def step(self):
        self.view.authentication.select()


@navigator.register(ServerInformation, 'Workers')
class ServerInformationDetails(CFMENavigateStep):
    VIEW = ServerSettingsView
    prerequisite = NavigateToSibling('Server Settings')

    def step(self):
        self.view.workers.select()


@navigator.register(ServerInformation, 'Custom Logos')
class ServerInformationDetails(CFMENavigateStep):
    VIEW = ServerSettingsView
    prerequisite = NavigateToSibling('Server Settings')

    def step(self):
        self.view.custom_logos.select()


@navigator.register(ServerInformation, 'Advanced')
class ServerInformationDetails(CFMENavigateStep):
    VIEW = ServerSettingsView
    prerequisite = NavigateToSibling('Server Settings')

    def step(self):
        self.view.advanced.select()
