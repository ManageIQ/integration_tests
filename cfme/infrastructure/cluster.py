""" A model of an Infrastructure Cluster in CFME

"""
import attr
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.widget import View
from widgetastic_patternfly import Button, Dropdown

from cfme.base.login import BaseLoggedInPage
from cfme.common import WidgetasticTaggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for, TimedOutError
from widgetastic_manageiq import (Accordion, BreadCrumb, ItemsToolBarViewSelector, ManageIQTree,
                                  SummaryTable, Text, TimelinesView, BaseEntitiesView)


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
    download = Button('Download summary in PDF format')


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
    including_entities = View.include(BaseEntitiesView, use_parent=True)


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
        expected_title = '{} (Summary)'.format(self.context['object'].name)
        return (
            self.in_cluster and
            self.entities.title.text == expected_title and
            self.entities.breadcrumb.active_location == expected_title)

    toolbar = View.nested(ClusterDetailsToolbar)
    sidebar = View.nested(ClusterDetailsAccordion)
    entities = View.nested(ClusterDetailsEntities)


class ClusterTimelinesView(TimelinesView, ClusterView):
    """The timelines page of a cluster"""
    breadcrumb = BreadCrumb()

    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        return (
            self.in_cluster and
            '{} (Summary)'.format(self.context['object'].name) in self.breadcrumb.locations and
            self.is_timelines)


@attr.s
class Cluster(Pretty, BaseEntity, WidgetasticTaggable):
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
        ][-1]

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
        view.toolbar.configuration.item_select('Remove item', handle_alert=not cancel)

        # cancel doesn't redirect, confirmation does
        view.flush_widget_cache()
        if cancel:
            view = self.create_view(ClusterDetailsView)
        else:
            view = self.create_view(ClusterAllView)
        wait_for(lambda: view.is_displayed, fail_condition=False, num_sec=10, delay=1)

        # flash message only displayed if it was deleted
        if not cancel:
            msg = 'The selected Clusters / Deployment Roles was deleted'
            view.flash.assert_success_message(msg)

        if wait:
            self.provider.refresh_provider_relationships()
            self.wait_for_disappear()

    def wait_for_disappear(self, timeout=300):
        self.provider.refresh_provider_relationships()
        try:
            return wait_for(lambda: not self.exists,
                            timeout=timeout,
                            message='Wait for cluster to disappear',
                            delay=10,
                            fail_func=self.browser.refresh)
        except TimedOutError:
            logger.error('Timed out waiting for cluster to disappear, continuing')

    def wait_for_exists(self):
        """Wait for the cluster to be refreshed"""
        view = navigate_to(self.parent, 'All')

        def refresh():
            if self.provider:
                self.provider.refresh_provider_relationships()
            view.browser.selenium.refresh()
            view.flush_widget_cache()

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

    def run_smartstate_analysis(self):
        """Run SmartState analysis"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        view.flash.assert_message_contain(
            'Cluster / Deployment Role: scan successfully initiated'
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
        if self.appliance.version < '5.9':
            view.toolbar.configuration.item_select('Remove selected items', handle_alert=True)
        else:
            view.toolbar.configuration.item_select(
                'Remove selected items from Inventory', handle_alert=True)
        view.flash.assert_no_error()
        flash_msg = ('Delete initiated for {} Clusters / Deployment Roles from the CFME Database'.
            format(len(clusters)))
        view.flash.assert_message(flash_msg)
        for cluster in clusters:
            cluster.wait_for_disappear()


@navigator.register(ClusterCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ClusterAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Clusters')

    def resetter(self):
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
