""" A model of an Infrastructure Cluster in CFME


:var page: A :py:class:`cfme.web_ui.Region` object describing common elements on the
           Cluster pages.
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import View
from widgetastic_manageiq import (Accordion, BreadCrumb, ItemsToolBarViewSelector, ManageIQTree,
                                  PaginationPane, Search, SummaryTable, Table, Text, TimelinesView)
from widgetastic_patternfly import Button, Dropdown, FlashMessages

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ClusterNotFound
from cfme.web_ui import match_location
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils.pretty import Pretty
from cfme.utils.wait import wait_for, TimedOutError
from cfme.utils.log import logger


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


class ClusterEntities(View):
    """A list of clusters"""
    title = Text('//div[@id="main-content"]//h1')
    table = Table('//div[@id="list_grid"]//table')
    search = View.nested(Search)
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class ClusterDetailsEntities(View):
    """A cluster properties on the details page"""
    breadcrumb = BreadCrumb()
    title = Text('//div[@id="main-content"]//h1')
    relationships = SummaryTable(title='Relationships')
    totals_for_hosts = SummaryTable(title='Totals for Hosts')
    totals_for_vms = SummaryTable(title='Totals for VMs')
    configuration = SummaryTable(title='Configuration')
    smart_management = SummaryTable(title='Smart Management')
    # element attributes changed from id to class in upstream-fine+, capture both with locator
    flash = FlashMessages('.//div[@id="flash_msg_div"]'
                          '/div[@id="flash_text_div" or contains(@class, "flash_text_div")]')


class ClusterView(BaseLoggedInPage):
    """Base view for all the cluster views"""
    @property
    def in_cluster(self):
        """Determine if the browser has navigated to the Cluster page"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Infrastructure', 'Clusters'] and
            # TODO: needs to be converted to Widgetastic once we have a replacement
            match_location(controller='ems_cluster', title='Clusters'))


class ClusterAllView(ClusterView):
    """The all view page for clusters"""
    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        return (
            self.in_cluster and
            self.entities.title.text == 'Clusters')

    toolbar = View.nested(ClusterToolbar)
    entities = View.nested(ClusterEntities)
    paginator = PaginationPane()


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
    @property
    def is_displayed(self):
        """Determine if this page is currently being displayed"""
        return (
            self.in_cluster and
            super(TimelinesView, self).is_displayed)


class ClusterCollection(Navigatable):
    """Collection object for the :py:class:`cfme.infrastructure.cluster.Cluster`."""

    def instantiate(self, name, provider):
        return Cluster(name, provider, collection=self)

    def delete(self, *clusters):
        """Delete one or more Clusters from the list of the Clusters

        Args:
            list of the `cfme.infrastructure.cluster.Cluster` objects
        """
        clusters = list(clusters)
        checked_clusters = []
        view = navigate_to(self, 'All')
        view.toolbar.view_selector.select('List View')

        if not view.entities.table.is_displayed:
            raise ValueError('No Clusters found')

        for row in view.entities.table:
            for cluster in clusters:
                if cluster.name == row.name.text:
                    checked_clusters.append(cluster)
                    row[0].check()
                    break
            if set(clusters) == set(checked_clusters):
                break
        if set(clusters) != set(checked_clusters):
            raise ValueError('Some Clusters were not found in the UI')
        view.toolbar.configuration.item_select('Remove selected items', handle_alert=True)
        view.entities.flash.assert_no_error()
        flash_msg = ('Delete initiated for {} Clusters / Deployment Roles from the CFME Database'.
            format(len(clusters)))
        view.flash.assert_message(flash_msg)
        for cluster in clusters:
            cluster.wait_for_disappear()


class Cluster(Pretty, Navigatable):
    """ Model of an infrastructure cluster in cfme

    Args:
        name: Name of the cluster.
        provider: provider this cluster is attached to.

    Note:
        If given a provider_key, it will navigate through ``Infrastructure/Providers`` instead
        of the direct path through ``Infrastructure/Clusters``.
    """
    pretty_attrs = ['name', 'provider']

    def __init__(self, name, provider, collection=None):
        self.name = name
        self.provider = provider
        self.collection = collection or ClusterCollection()
        self._short_name = self.name.split('in')[0].strip()
        self.quad_name = 'cluster'
        Navigatable.__init__(self, appliance=self.collection.appliance)

        col = self.appliance.rest_api.collections
        self._id = [
            cl.id
            for cl in col.clusters.all
            if cl.name == self._short_name and cl.ems_id == self.provider.id
        ][-1]

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
            view.entities.flash.assert_no_error()
            msg = 'The selected Clusters / Deployment Roles was deleted'
            view.entities.flash.assert_success_message(msg)

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
        view = navigate_to(self.collection, 'All')

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
        view = navigate_to(self.collection, 'All')
        try:
            view.paginator.find_row_on_pages(view.entities.table, name=self.name)
            return True
        except NoSuchElementException:
            return False

    @property
    def id(self):
        """extracts cluster id for this cluster"""
        return self._id

    @property
    def short_name(self):
        """returns only cluster's name exactly how it is stored in DB (without datacenter part)"""
        return self._short_name

    def run_smartstate_analysis(self):
        """Run SmartState analysis"""
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', invokes_alert=True)
        view.entities.flash.assert_message_contain('Cluster / Deployment Role: scan successfully '
                                                   'initiated')


@navigator.register(ClusterCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ClusterAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'Clusters')

    def resetter(self):
        """Reset the view"""
        self.view.toolbar.view_selector.select('Grid View')
        self.view.paginator.check_all()
        self.view.paginator.uncheck_all()


@navigator.register(Cluster, 'Details')
class Details(CFMENavigateStep):
    VIEW = ClusterDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.toolbar.view_selector.select('List View')
        version = self.obj.appliance.version
        if (version >= '5.7.4' and version < '5.8') or version >= '5.8.1.2':
            cluster_name = self.obj.short_name
        else:
            cluster_name = self.obj.name
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                self.prerequisite_view.entities.table,
                name=cluster_name)
        except NoSuchElementException:
            raise ClusterNotFound('Cluster {} not found'.format(cluster_name))
        row.click()


@navigator.register(Cluster, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = ClusterTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        """Navigate to the correct view"""
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


# TODO: This doesn't seem to be used, and needs to be migrated to Widgetastic
# @navigator.register(Cluster, 'DetailsFromProvider')
# class DetailsFromProvider(CFMENavigateStep):
    # def step(self, *args, **kwargs):
        # """Navigate to the correct view"""
        # navigate_to(self.obj.provider, 'Details')
        # list_acc.select('Relationships', 'Show all managed Clusters', by_title=True,
        #                 partial=False)
        # sel.click(Quadicon(self.obj.name, self.obj.quad_name))
