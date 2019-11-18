import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input
from widgetastic_patternfly import Text

from cfme.common import BaseLoggedInPage
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance import NavigatableMixin
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.update import Updateable
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from widgetastic_manageiq import ConversionHost
from widgetastic_manageiq import HiddenFileInput
from widgetastic_manageiq import SearchBox
from widgetastic_manageiq import V2VBootstrapSwitch
from widgetastic_manageiq import WaitTab


class MigrationThrottling(Updateable, NavigatableMixin):
    """Migration Throttling for conversion host"""

    def __init__(self, appliance, migration_settings):
        self.appliance = appliance
        self.migration_settings = migration_settings

    def set_max_migration_per_conv_host(self, migration_per_conv_host):
        """ Set migration throttling per conversion host
        Args:
            migration_per_conv_host: Integer
        """
        view = navigate_to(self.migration_settings, 'MigrationSettings')
        view.tabs.migration_throttling.fill({'migration_per_conv_host': migration_per_conv_host})
        view.tabs.migration_throttling.apply_btn.click()

    def get_max_migration_per_conv_host(self):
        """ Get migration throttling per conversion host
        Args:
            migration_per_conv_host: Integer
        """
        view = navigate_to(self.migration_settings, 'MigrationSettings')
        return view.tabs.migration_throttling.migration_per_conv_host.read()


class MigrationSettings(Updateable, NavigatableMixin):
    """Migration Settings page that has throttling tab """

    def __init__(self, appliance):
        self.appliance = appliance

    @property
    def migration_throttling(self):
        """The 'Migration Throttling' tab """
        return MigrationThrottling(self.appliance, self)


class MigrationThrottlingForm(View):
    migration_per_conv_host = Input(id='max_concurrent_tasks_per_host')
    migration_per_provider = Input(id='max_concurrent_tasks_per_ems')
    apply_btn = Button("Apply")


class ConversionHostForm(View):
    configure_conversion_host = Text(locator='(//a|//button)[text()="Configure Conversion Host"]')
    conv_host_progress = ConversionHost()


class MigrationSettingsView(BaseLoggedInPage):

    @View.nested
    class tabs(View):  # noqa
        """The tabs on the page"""

        @View.nested
        class migration_throttling(WaitTab):  # noqa
            fill_strategy = WaitFillViewStrategy("15s")
            TAB_NAME = 'Migration Throttling'
            title = Text('.//div[contains(@class, "pull-left")]//h3')
            including_entities = View.include(MigrationThrottlingForm, use_parent=True)

            @property
            def is_displayed(self):
                return self.title.text == "Concurrent Migrations"

        @View.nested
        class conversion_hosts(WaitTab):  # noqa
            fill_strategy = WaitFillViewStrategy("20s")
            TAB_NAME = 'Conversion Hosts'
            title = Text('.//div[contains(@class, "pull-left")]//h3')
            including_entities = View.include(ConversionHostForm, use_parent=True)

            @property
            def is_displayed(self):
                return self.title.text == "Configured Conversion Host"

    @property
    def is_displayed(self):
        nav_menu = (
            ["Compute", "Migration", "Migration Settings"]
            if self.context["object"].appliance.version < "5.11"
            else ["Migration", "Migration Settings"]
        )
        return self.logged_in_as_current_user and self.navigation.currently_selected == nav_menu


class ConfigureConversionHostsView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    conv_host_progress = ConversionHost()
    fill_strategy = WaitFillViewStrategy("20s")

    next_btn = Button("Next")
    configure_btn = Button("Configure")
    close_btn = Button("Close")

    @property
    def is_displayed(self):
        return self.title.text == "Configure Conversion Host"

    @View.nested
    class location(View):  # noqa
        fill_strategy = WaitFillViewStrategy("15s")
        provider_type = BootstrapSelect("providerType")
        provider_name = BootstrapSelect("provider")
        cluster = BootstrapSelect("cluster")

        @property
        def is_displayed(self):
            return self.provider_type.is_displayed

        def after_fill(self, was_change):
            self.parent.next_btn.click()

    @View.nested
    class hosts(View):  # noqa
        fill_strategy = WaitFillViewStrategy("15s")
        hostname = SearchBox(id='host-selection')

        @property
        def is_displayed(self):
            return self.hostname.is_displayed

        def after_fill(self, was_change):
            self.parent.next_btn.click()

    @View.nested
    class authentication(View):  # noqa
        fill_strategy = WaitFillViewStrategy("15s")
        conv_host_key = HiddenFileInput(locator='.//div[@id="conversionHostSshKey"]/div/input')
        transformation_method = BootstrapSelect("transformationMethod")
        vddk_library_path = Input(id='vddk-library-path')
        vmware_ssh_key = TextInput(locator='.//textarea[@id="vmware-ssh-key-input"]')
        osp_cert_switch = V2VBootstrapSwitch(label='Verify TLS Certificates for OpenStack')
        osp_ca_cert = TextInput(locator='.//textarea[@id="openstack-ca-certs-input"]')

        @property
        def is_displayed(self):
            return self.conv_host_key.is_displayed

        def after_fill(self, was_change):
            self.parent.configure_btn.click()

    @View.nested
    class results(View):  # noqa
        msg = Text('.//h3[contains(@class,"blank-slate-pf-main-action")]')

        @property
        def is_displayed(self):
            return self.msg.is_displayed


@attr.s
class ConversionHost(BaseEntity):
    """Class representing conversion Host
        Args:
            target_provider: RHV or OSP
            cluster: Default
            hostname: host to be configured
            conv_host_key: /etc/pki/ovirt-engine/keys/engine_id_rsa on RHV-M.
            transformation_method: vddk or ssh
            vddk_library_path: url for vddk
            vmware_ssh_key: /var/lib/vdsm/.ssh/id_rsa on rhv host
            osp_ca_cert : CA cert

    """
    target_provider = attr.ib()
    cluster = attr.ib()
    hostname = attr.ib()
    conv_host_key = attr.ib()
    transformation_method = attr.ib(validator=attr.validators.in_(["VDDK", "SSH"]))
    vddk_library_path = attr.ib(default=None)
    vmware_ssh_key = attr.ib(default=None)
    osp_cert_switch = attr.ib(default=None)
    osp_ca_cert = attr.ib(default=None)

    def fill_dict(self):
        """Generate a dictionary for filling the Conversion host view
        Returns: dict
        """
        provider_type = ("Red Hat Virtualization" if self.target_provider.one_of(RHEVMProvider)
                         else "Red Hat OpenStack Platform")
        return {
            "location": {"provider_type": provider_type, "provider_name": self.target_provider.name,
                         "cluster": self.cluster},
            "hosts": {"hostname": self.hostname},
            "authentication": {"conv_host_key": self.conv_host_key,
                               "transformation_method": self.transformation_method,
                               "vddk_library_path": self.vddk_library_path,
                               "vmware_ssh_key": self.vmware_ssh_key,
                               "osp_cert_switch": self.osp_cert_switch,
                               "osp_ca_cert": self.osp_ca_cert}
        }

    @property
    def is_host_configured(self):
        """Wait for conversion host to configure and return success/failure state"""
        view = navigate_to(self.parent, "All")
        try:
            wait_for(view.tabs.conversion_hosts.conv_host_progress.in_progress,
                     func_args=[self.hostname],
                     fail_condition=True)
        except TimedOutError:
            self.logger.warning("Timed out waiting for {} to configure".format(self.hostname))
        return view.tabs.conversion_hosts.conv_host_progress.is_host_configured(self.hostname)

    def remove_conversion_host(self):
        """Remove conversion host"""
        view = navigate_to(self.parent, "All")
        view.tabs.conversion_hosts.conv_host_progress.remove_conversion_host(self.hostname)
        return wait_for(view.tabs.conversion_hosts.conv_host_progress.in_progress,
                        func_args=[self.hostname],
                        fail_condition=True)


@attr.s
class ConversionHostCollection(BaseCollection):
    """Collection object for conversion host object"""

    ENTITY = ConversionHost

    def create(self,
               target_provider,
               cluster,
               hostname,
               conv_host_key,
               transformation_method,
               vddk_library_path=None,
               vmware_ssh_key=None,
               osp_cert_switch=None,
               osp_ca_cert=None):
        """Configure new conversions host in UI
        Args:
            target_provider: RHV or OSP
            cluster: Default
            hostname: Hostname to be configured
            conv_host_key: /etc/pki/ovirt-engine/keys/engine_id_rsa on RHV-M.
            transformation_method: vddk or ssh
            vddk_library_path: url for vddk
            vmware_ssh_key: /var/lib/vdsm/.ssh/id_rsa on rhv host
            osp_cert_switch: Yes or No
            osp_ca_cert: Tls Cert

        """
        conversion_host = self.instantiate(
            target_provider=target_provider,
            cluster=cluster,
            hostname=hostname,
            conv_host_key=conv_host_key,
            transformation_method=transformation_method,
            vddk_library_path=vddk_library_path,
            vmware_ssh_key=vmware_ssh_key,
            osp_cert_switch=osp_cert_switch,
            osp_ca_cert=osp_ca_cert
        )

        view = navigate_to(self, "Configure")
        view.fill(conversion_host.fill_dict())
        return conversion_host


@navigator.register(MigrationSettings, "MigrationSettings")
class MigrationSettingsPage(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    VIEW = MigrationSettingsView

    def step(self):
        if self.obj.appliance.version < "5.11":
            self.prerequisite_view.navigation.select("Compute", "Migration", "Migration Settings")
        else:
            self.prerequisite_view.navigation.select("Migration", "Migration Settings")


@navigator.register(ConversionHostCollection, "All")
class ConversionHosts(CFMENavigateStep):
    VIEW = MigrationSettingsView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        if self.obj.appliance.version < "5.11":
            self.prerequisite_view.navigation.select("Compute", "Migration", "Migration Settings")
        else:
            self.prerequisite_view.navigation.select("Migration", "Migration Settings")
        self.view.tabs.conversion_hosts.click()
        self.view.tabs.conversion_hosts.configure_conversion_host.wait_displayed()


@navigator.register(ConversionHostCollection, "Configure")
class ConfigureConversionHost(CFMENavigateStep):
    VIEW = ConfigureConversionHostsView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.tabs.conversion_hosts.configure_conversion_host.wait_displayed()
        self.prerequisite_view.tabs.conversion_hosts.configure_conversion_host.click()
