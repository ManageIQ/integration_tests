# -*- coding: utf-8 -*-
# added new list_tbl definition
from functools import partial
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View, Text
from widgetastic_manageiq import (
    BootstrapSelect, Button, Table, Accordion, ManageIQTree, PaginationPane)
from widgetastic_patternfly import Dropdown

from cfme.base.login import BaseLoggedInPage
from cfme.common import Taggable, SummaryMixin
from cfme.containers.provider import ContainersProvider
from cfme.exceptions import NodeNotFound
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb, InfoBlock, match_location
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

match_page = partial(match_location, controller='container_node', title='Nodes')

# TODO Replace with resource table widget
resource_locator = "//div[@id='records_div']/table//span[@title='{}']"


class NodeView(BaseLoggedInPage):
    title = Text('#explorer_title_text')

    monitor = Dropdown('Monitoring')
    policy = Dropdown('Policy')
    download = Dropdown('Download')

    nodes = Table(locator="//div[@id='list_grid']//table")

    @property
    def in_cloud_instance(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Containers', 'Container Nodes'] and
            match_page()  # No summary, just match controller and title
        )


class NodeCollection(Navigatable):
    """Collection object for :py:class:`Node`."""

    def instantiate(self, name, provider):
        return Node(name=name, provider=provider, appliance=self.appliance)

    def all(self):
        # container_nodes table has ems_id, join with ext_mgmgt_systems on id for provider name
        node_table = self.appliance.db['container_nodes']
        ems_table = self.appliance.db['ext_management_systems']
        node_query = self.appliance.db.session.query(node_table.name, ems_table.name)\
            .join(ems_table, node_table.ems_id == ems_table.id)
        nodes = []
        for name, provider_name in node_query.all():
            # Hopefully we can get by with just provider name?
            nodes.append(Node(name=name,
                              provider=ContainersProvider(name=provider_name,
                                                          appliance=self.appliance),
                              collection=self))
        return nodes


class NodeAllView(NodeView):
    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            match_page(summary='Nodes')
        )

    paginator = PaginationPane()


class Node(Taggable, SummaryMixin, Navigatable):
    def __init__(self, name, provider, collection=None, appliance=None):
        self.name = name
        self.provider = provider
        if not collection:
            collection = NodeCollection(appliance=appliance)
        self.collection = collection
        Navigatable.__init__(self, appliance=appliance)

    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: Table name and Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the summary's value.
        """
        self.load_details()
        return InfoBlock.text(*ident)


# Still registering Node to keep on consistency on container objects navigations
@navigator.register(Node, 'All')
@navigator.register(NodeCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NodeAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Nodes')

    def resetter(self):
        # Reset view and selection
        tb.select("List View")


class NodeDetailsView(NodeView):
    download = Button(name='download_view')

    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            match_page(summary='{} (Summary)'.format(self.context['object'].name))
        )

    @View.nested
    class properties(Accordion):  # noqa
        tree = ManageIQTree()

    @View.nested
    class relationships(Accordion):  # noqa
        tree = ManageIQTree()


@navigator.register(Node, 'Details')
class Details(CFMENavigateStep):
    VIEW = NodeDetailsView
    prerequisite = NavigateToAttribute('collection', 'All')

    def step(self, *args, **kwargs):
        # Need to account for paged view
        for _ in self.prerequisite_view.paginator.pages():
            row = self.view.nodes.row(name=self.obj.name, provider=self.obj.provider.name)
            if row:
                row.click()
                break
        else:
            raise NodeNotFound('Failed to navigate to node, could not find matching row')


class NodeEditTagsForm(NodeView):
    tag_category = BootstrapSelect('tag_cat')
    tag = BootstrapSelect('tag_add')
    # TODO: table for added tags with removal support
    # less than ideal button duplication between classes
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            match_page(summary='Tag Assignment') and
            sel.is_displayed(resource_locator.format(self.context['object'].name))
        )


@navigator.register(Node, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = NodeEditTagsForm
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy.item_select('Edit Tags')


class NodeManagePoliciesForm(NodeView):
    policy_profiles = BootstrapSelect('protectbox')
    # less than ideal button duplication between classes
    save_button = Button('Save')
    reset_button = Button('Reset')
    cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            match_page(summary='Select Policy Profiles') and
            sel.is_displayed(resource_locator.format(self.context['object'].name))
        )


@navigator.register(Node, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = NodeManagePoliciesForm
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy.item_select('Manage Policies')


class NodeUtilizationView(NodeView):
    # TODO manageIQ/patternfly C&U view/widget?

    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            match_page(summary='{} Capacity & Utilization'.format(self.context['object'].name))
        )


@navigator.register(Node, 'Utilization')
class Utilization(CFMENavigateStep):
    VIEW = NodeUtilizationView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.monitor.item_select('Utilization')


class NodeTimelinesForm(NodeView):
    # TODO PR 3710, timeline widget

    @property
    def is_displayed(self):
        return (
            self.in_cloud_instance and
            match_page(summary='Timelines'.format(self.context['object'].name)) and
            # TODO: PR 3710 adds BreadCrumb widget, replace False with breadcrumb check
            # Can't use accordion because it truncates the name
            # sel.is_displayed(details_accordion_locator.format(self.context['object'].name))
            False
        )


@navigator.register(Node, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = NodeTimelinesForm
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.monitor.item_select('Timelines')
