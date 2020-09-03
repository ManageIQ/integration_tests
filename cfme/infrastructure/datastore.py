""" A model of an Infrastructure Datastore in CFME
"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling

from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.common.candu_views import DatastoreInfraUtilizationView
from cfme.common.datastore_views import DatastoreDetailsView
from cfme.common.datastore_views import DatastoreManagedVMsView
from cfme.common.datastore_views import DatastoresView
from cfme.common.host_views import RegisteredHostsView
from cfme.exceptions import ItemNotFound
from cfme.exceptions import MenuItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.optimize.utilization import DatastoreUtilizationTrendsView
from cfme.utils import ParamClassName
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for


@attr.s
class Datastore(Pretty, BaseEntity, Taggable, CustomButtonEventsMixin):
    """Model of an infrastructure datastore in cfme

    Args:
        name: Name of the datastore.
        provider: provider this datastore is attached to.

    """

    pretty_attrs = ['name', 'provider_key']
    _param_name = ParamClassName('name')
    name = attr.ib()
    provider = attr.ib()
    type = attr.ib(default=None)

    def __attrs_post_init__(self):
        # circular imports
        from cfme.infrastructure.host import HostsCollection
        self._collections = {'hosts': HostsCollection}

    @property
    def rest_api_entity(self):
        return self.appliance.rest_api.collections.data_stores.get(name=self.name)

    def delete(self, cancel=True):
        """
        Deletes a datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True

        Note:
            Datastore must have 0 hosts and 0 VMs for this to work.
        """
        # BZ 1467989 - this button is never getting enabled for some resources
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove Datastore from Inventory',
                                               handle_alert=(not cancel))
        view.flash.assert_success_message('Delete initiated for Datastore from the CFME Database')

    @property
    def hosts(self):
        return self.collections.hosts

    def get_hosts(self):
        """ Returns names of hosts (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no hosts found.
        """
        view = navigate_to(self, 'DetailsFromProvider')
        view.entities.relationships.click_at('Hosts')
        hosts_view = view.browser.create_view(RegisteredHostsView)
        return hosts_view.entities.get_all()

    def get_vms(self):
        """ Returns names of VMs (from quadicons) that use this datastore

        Returns: List of strings with names or `[]` if no vms found.
        """
        view = navigate_to(self, 'Details')
        if 'VMs' in view.entities.relationships.fields:
            view.entities.relationships.click_at('VMs')
        else:
            view.entities.relationships.click_at('Managed VMs')
        vms_view = view.browser.create_view(DatastoreManagedVMsView)
        return vms_view.entities.all_entity_names

    def delete_all_attached_vms(self):
        view = navigate_to(self, 'ManagedVMs')
        for entity in view.entities.get_all():
            entity.check()
        view.toolbar.configuration.item_select('Remove selected items from Inventory',
                                               handle_alert=True)

        wait_for(lambda: bool(len(view.entities.get_all())), fail_condition=True,
                 message="Wait datastore vms to disappear", num_sec=1000,
                 fail_func=self.browser.refresh)

    def delete_all_attached_hosts(self):
        view = navigate_to(self, 'Details')
        view.entities.relationships.click_at('Hosts')
        hosts_view = view.browser.create_view(RegisteredHostsView)
        for entity in hosts_view.entities.get_all():
            entity.ensure_checked()
        view.toolbar.configuration.item_select('Remove items from Inventory',
                                               handle_alert=True)

        wait_for(lambda: bool(len(hosts_view.entities.get_all())), fail_condition=True,
                 message="Wait datastore hosts to disappear", num_sec=1000,
                 fail_func=self.browser.refresh)

    @property
    def exists(self):
        try:
            navigate_to(self, 'Details')
            return True
        except ItemNotFound:
            return False

    @property
    def host_count(self):
        """ number of attached hosts.

        Returns:
            :py:class:`int` host count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.relationships.get_text_of('Hosts'))

    @property
    def vm_count(self):
        """ number of attached VMs.

        Returns:
            :py:class:`int` vm count.
        """
        view = navigate_to(self, 'Details')
        return int(view.entities.relationships.get_text_of('Managed VMs'))

    def run_smartstate_analysis(self, wait_for_task_result=False):
        """ Runs smartstate analysis on this host

        Note:
            The host must have valid credentials already set up for this to work.
        """
        view = navigate_to(self, 'DetailsFromProvider')
        try:
            wait_for(lambda: view.toolbar.configuration.item_enabled('Perform SmartState Analysis'),
                     fail_condition=False, num_sec=10)
        except TimedOutError:
            raise MenuItemNotFound('Smart State analysis is disabled for this datastore')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        view.flash.assert_success_message(f'"{self.name}": scan successfully initiated')
        if wait_for_task_result:
            task = self.appliance.collections.tasks.instantiate(
                name=f"SmartState Analysis for [{self.name}]", tab='MyOtherTasks')
            task.wait_for_finished()
            return task

    def run_smartstate_analysis_from_provider(self, wait_for_task_result=False):
        """ Runs smartstate analysis of this datastore with navigating trough the provider

        Note:
            The host must have valid credentials already set up for this to work.
        """
        view = navigate_to(self.provider, 'DatastoresOfProvider')
        try:
            view.entities.get_entity(name=self.name, surf_pages=True).ensure_checked()
        except ItemNotFound:
            raise ValueError(f'Could not find datastore {self.name} in the UI')

        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        view.flash.assert_success_message(
            f'"{self.name}": scan successfully initiated')

        if wait_for_task_result:
            task = self.appliance.collections.tasks.instantiate(
                name=f"SmartState Analysis for [{self.name}]", tab='MyOtherTasks')
            task.wait_for_finished()
            return task

    def wait_candu_data_available(self, timeout=900):
        """Waits until C&U data are available for this Datastore

        Args:
            timeout: Timeout passed to :py:func:`utils.wait.wait_for`
        """
        view = navigate_to(self, 'Details')
        wait_for(
            lambda: view.toolbar.monitoring.item_enabled("Utilization"),
            delay=10, handle_exception=True, num_sec=timeout,
            fail_func=view.browser.refresh
        )


@attr.s
class DatastoreCollection(BaseCollection):
    """Collection class for :py:class:`cfme.infrastructure.datastore.Datastore`"""
    ENTITY = Datastore

    def all(self):
        "Returning all datastore objects with filtering support as per provider"
        provider = self.filters.get("provider")
        datastores = self.appliance.rest_api.collections.data_stores.all_include_attributes(
            attributes=["hosts"]
        )
        datastore_db = {}

        for ds in datastores:
            for host in ds.hosts:
                if host.get("ems_id"):
                    datastore_db.update({ds.name: host.get("ems_id")})
                    break

        provider_db = {
            prov.id: get_crud_by_name(prov.name)
            for prov in self.appliance.rest_api.collections.providers.all
            if not (
                getattr(prov, "parent_ems_id", False)
                or ("Manager" in prov.name or prov.name == "Embedded Ansible")
            )
        }
        datastores = [
            self.instantiate(name=name, provider=provider_db[prov_id])
            for name, prov_id in datastore_db.items()
        ]
        return (
            [ds for ds in datastores if ds.provider.id == provider.id] if provider else datastores
        )

    def delete(self, *datastores):
        """
        Note:
            Datastores must have 0 hosts and 0 VMs for this to work.
        """
        datastores = list(datastores)
        checked_datastores = list()
        view = navigate_to(self, 'All')

        for datastore in datastores:
            try:
                view.entities.get_entity(name=datastore.name, surf_pages=True).ensure_checked()
                checked_datastores.append(datastore)
            except ItemNotFound:
                raise ValueError(f'Could not find datastore {datastore.name} in the UI')

        if set(datastores) == set(checked_datastores):
            view.toolbar.configuration.item_select('Remove Datastores', handle_alert=True)
            view.flash.assert_success_message(
                'Delete initiated for Datastore from the CFME Database')

            for datastore in datastores:
                wait_for(lambda: not datastore.exists, num_sec=600, delay=30,
                         message='Wait for Datastore to be deleted')

    def run_smartstate_analysis(self, *datastores):
        datastores = set(datastores)

        view = navigate_to(self, 'All')

        for datastore in datastores:
            try:
                view.entities.get_entity(name=datastore.name, surf_pages=True).ensure_checked()
            except ItemNotFound:
                raise ValueError(f'Could not find datastore {datastore.name} in the UI')

        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        for datastore in datastores:
            view.flash.assert_success_message(
                f'"{datastore.name}": scan successfully initiated')

    def run_smartstate_analysis_from_provider(self, *datastores: Datastore):
        """ Runs smartstate analysis of this datastore with navigating trough the provider """
        for datastore in datastores:
            datastore.run_smartstate_analysis_from_provider(wait_for_task_result=False)


@navigator.register(DatastoreCollection, 'All')
class All(CFMENavigateStep):
    VIEW = DatastoresView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Datastores')

    def resetter(self, *args, **kwargs):
        """
        resets page to default state when user navigates to All Datastores destination
        """
        # Reset view and selection
        self.view.sidebar.datastores.tree.click_path('All Datastores')
        self.view.toolbar.view_selector.select("Grid View")
        self.view.entities.paginator.reset_selection()


@navigator.register(Datastore, 'Details')
class Details(CFMENavigateStep):
    VIEW = DatastoreDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(Datastore, 'DetailsFromProvider')
class DetailsFromProvider(CFMENavigateStep):
    VIEW = DatastoreDetailsView

    def prerequisite(self):
        prov_view = navigate_to(self.obj.provider, 'Details')
        prov_view.entities.summary('Relationships').click_at('Datastores')
        return self.obj.create_view(DatastoresView)

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()


@navigator.register(Datastore, "Utilization")
class Utilization(CFMENavigateStep):
    VIEW = DatastoreInfraUtilizationView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select("Utilization")


@navigator.register(Datastore)
class ManagedVMs(CFMENavigateStep):
    VIEW = DatastoreManagedVMsView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.relationships.click_at('Managed VMs')


@navigator.register(Datastore, "UtilTrendSummary")
class DatastoreOptimizeUtilization(CFMENavigateStep):
    VIEW = DatastoreUtilizationTrendsView

    prerequisite = NavigateToAttribute("appliance.collections.utilization", "All")

    def step(self, *args, **kwargs):
        path = [self.appliance.region(), "Datastores", self.obj.name]
        if self.appliance.version >= "5.11":
            path.insert(0, "Enterprise")
        self.prerequisite_view.tree.click_path(*path)
