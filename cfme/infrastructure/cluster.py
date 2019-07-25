""" A model of an Infrastructure Cluster in CFME

"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapNav
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown

from cfme.base.login import BaseLoggedInPage
from cfme.common import CustomButtonEventsMixin
from cfme.common import Taggable
from cfme.common import TimelinesView
from cfme.common.candu_views import ClusterInfraUtilizationView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import ItemsToolBarViewSelector
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Search
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import Text


# TODO: since Cluster always requires provider, it will use only one way to get to Cluster Detail's
# page. But we need to fix this in the future.


class ClusterToolbar(View):
    """The toolbar on the page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    view_selector = View.nested(ItemsToolBarViewSelector)


class ClusterDetailsToolbar(View):
    """The toolbar on the detail page"""
    configuration = Dropdown('Configuration')
    policy = Dropdown('Policy')
    monitoring = Dropdown('Monitoring')
    download = Button('Print or export summary')


class ClusterDetailsAccordion(View):
    """The accordion on the details page"""
    @View.nested
    class cluster(Accordion):           # noqa
        pass

    @View.nested
    class properties(Accordion):        # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):     # noqa
        tree = ManageIQTree()


class ClusterDetailsEntities(View):
    """A cluster properties on the details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    relationships = SummaryTable(title='Relationships')
    totals_for_hosts = SummaryTable(title='Totals for Hosts')
    totals_for_vms = SummaryTable(title='Totals for VMs')
    configuration = SummaryTable(title='Configuration')
    smart_management = SummaryTable(title='Smart Management')


class ClusterView(BaseLoggedInPage):
    """Base view for all the cluster views"""
    @property
    def in_cluster(self):
        """Determine if the browser has navigated to the Cluster page"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Clusters'])


class ClusterAllView(ClusterView):
    """The all view page for clusters"""
    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        return (
            self.in_cluster and
            self.entities.title.text == 'Clusters')

    toolbar = View.nested(ClusterToolbar)
    search = View.nested(Search)
    including_entities = View.include(BaseEntitiesView, use_parent=True)

    @View.nested
    class my_filters(Accordion):  # noqa
        ACCORDION_NAME = "My Filters"

        navigation = BootstrapNav('.//div/ul')
        tree = ManageIQTree()


class ProviderAllClustersView(ClusterAllView):
    """
    This view is used in test_provider_relationships
    """

    @property
    def is_displayed(self):
        return (
            self.navigation.currently_selected == ["Compute", "Infrastructure", "Providers"] and
            self.entities.title.text == "{} (All Clusters)".format(self.context["object"].name)
        )


class ClusterDetailsView(ClusterView):
    """The details page of a cluster"""
    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        obj = self.context['object']
        return (
            self.in_cluster and
            self.entities.title.text == obj.expected_details_title and
            self.entities.breadcrumb.active_location == obj.expected_details_breadcrumb
        )

    toolbar = View.nested(ClusterDetailsToolbar)
    sidebar = View.nested(ClusterDetailsAccordion)
    entities = View.nested(ClusterDetailsEntities)


class ClusterTimelinesView(TimelinesView, ClusterView):
    """The timelines page of a cluster"""
    pass


@attr.s
class Cluster(Pretty, BaseEntity, Taggable, CustomButtonEventsMixin):
    """ Model of an infrastructure cluster in cfme

    Args:
        name: Name of the cluster.
        provider: provider this cluster is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Clusters``.
    """
    pretty_attrs = ['name', 'provider']
    quad_name = 'cluster'

    name = attr.ib()
    provider = attr.ib()  # TODO : Replace this with a walk when the provider can give us clusters

    def __attrs_post_init__(self):
        col = self.appliance.rest_api.collections
        self._id = [
            int(cl.id)
            for cl in col.clusters
            if cl.name in (self.short_name, self.name) and cl.ems_id == self.provider.id
        ][-1]  # FIXME this is raising an IndexError for being out of range, list must be empty

    @property
    def short_name(self):
        return self.name.split('in')[0].strip()

    def delete(self, cancel=True, wait=False):
        """
        Deletes a cluster from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
            wait: Whether or not to wait for the delete to complete, defaults to False
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove item from Inventory',
                                               handle_alert=not cancel)

        # cancel doesn't redirect, confirmation does
        view.flush_widget_cache()
        if cancel:
            view = self.create_view(ClusterDetailsView, wait=10)
        else:
            view = self.create_view(ClusterAllView, wait=10)

        # flash message only displayed if it was deleted
        if not cancel:
            view.flash.assert_success_message(
                'The selected Clusters / Deployment Roles was deleted'
            )

        if wait:
            self.provider.refresh_provider_relationships()
            self.wait_for_disappear()

    def wait_for_disappear(self, timeout=300):
        self.provider.refresh_provider_relationships()
        try:
            return wait_for(lambda: not self.exists,
                            timeout=timeout,
                            message='Wait for cluster to disappear',
                            delay=5,
                            fail_func=self.browser.refresh)
        except TimedOutError:
            logger.error('Timed out waiting for cluster to disappear, continuing')

    def wait_for_exists(self):
        """Wait for the cluster to be refreshed"""
        view = navigate_to(self.parent, 'All')

        def refresh():
            if self.provider:
                self.provider.refresh_provider_relationships()
            view.browser.refresh()

        wait_for(lambda: self.exists, fail_condition=False, num_sec=1000, fail_func=refresh,
                 message='Wait cluster to appear')

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        The function first ensures that we are on the detail page for the specific cluster.

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
            A string representing the contents of the InfoBlock's value.
        """
        view = navigate_to(self, 'Details')
        return getattr(view, ident[0].lower().replace(' ', '_')).get_text_of(ident[1])

    @property
    def exists(self):
        view = navigate_to(self.parent, 'All')
        try:
            view.entities.get_entity(name=self.name, surf_pages=True)
            return True
        except ItemNotFound:
            return False

    @property
    def id(self):
        """extracts cluster id for this cluster"""
        return self._id

    def run_smartstate_analysis(self, wait_for_task_result=False):
        """Run SmartState analysis"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        view.flash.assert_message(
            'Cluster / Deployment Role: scan successfully initiated'
        )
        if wait_for_task_result:
            task = self.appliance.collections.tasks.instantiate(
                name="SmartState Analysis for [{}]".format(self.name), tab='MyOtherTasks')
            task.wait_for_finished()
            return task

    def wait_candu_data_available(self, timeout=1200):
        """Waits until C&U data are available for this Cluster

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
class ClusterCollection(BaseCollection):
    """Collection object for the :py:class:`cfme.infrastructure.cluster.Cluster`."""

    ENTITY = Cluster

    def delete(self, *clusters):
        """Delete one or more Clusters from the list of the Clusters

        Args:
            list of the `cfme.infrastructure.cluster.Cluster` objects
        """
        clusters = list(clusters)
        checked_cluster_names = set()
        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('List View')

        # todo: replace with get_all later
        if not view.entities.elements.is_displayed:
            raise ValueError('No Clusters found')

        cluster_names = {cluster.name for cluster in clusters}

        for row in view.entities.elements:
            for cluster in clusters:
                if cluster.name == row.name.text:
                    checked_cluster_names.add(cluster.name)
                    row[0].check()
                    break
            if cluster_names == checked_cluster_names:
                break
        if cluster_names != checked_cluster_names:
            raise ValueError(
                'Some Clusters {!r} were not found in the UI'.format(
                    cluster_names - checked_cluster_names))
        view.toolbar.configuration.item_select('Remove selected items from Inventory',
                                               handle_alert=True)
        view.flash.assert_no_error()
        flash_msg = ('Delete initiated for {} Clusters / Deployment Roles from the CFME Database'
                     .format(len(clusters)))
        view.flash.assert_message(flash_msg)
        for cluster in clusters:
            cluster.wait_for_disappear()

    def all(self):
        """returning all cluster objects and support filtering as per provider"""
        provider = self.filters.get("provider")
        clusters = self.appliance.rest_api.collections.clusters.all
        if provider:
            cluster_obj = [
                self.instantiate(name=cluster.name, provider=provider)
                for cluster in clusters
                if provider.id == cluster.ems_id
            ]
        else:
            providers = self.appliance.rest_api.collections.providers
            providers_db = {
                prov.id: get_crud_by_name(prov.name)
                for prov in providers
                if not (
                    getattr(prov, "parent_ems_id", False)
                    or ("Manager" in prov.name or prov.name == "Embedded Ansible")
                )
            }
            cluster_obj = [
                self.instantiate(name=cluster.name, provider=providers_db[cluster.ems_id])
                for cluster in clusters
            ]
        return cluster_obj


@navigator.register(ClusterCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ClusterAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Clusters')

    def resetter(self, *args, **kwargs):
        """Reset the view"""
        self.view.entities.paginator.reset_selection()


@navigator.register(Cluster, 'Details')
class Details(CFMENavigateStep):
    VIEW = ClusterDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        # todo: figure out why the same cfme version shows clusters with short and long name
        try:
            entity = self.prerequisite_view.entities.get_entity(name=self.obj.short_name,
                                                                surf_pages=True)
        except ItemNotFound:
            entity = self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                                surf_pages=True)
        entity.click()


@navigator.register(Cluster, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = ClusterTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(Cluster, "Utilization")
class Utilization(CFMENavigateStep):
    VIEW = ClusterInfraUtilizationView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
