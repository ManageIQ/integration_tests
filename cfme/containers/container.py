import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic_patternfly import VerticalNavigation

from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.common import TagPageView
from cfme.containers.provider import ContainerObjectAllBaseView
from cfme.containers.provider import ContainerObjectDetailsBaseView
from cfme.containers.provider import GetRandomInstancesMixin
from cfme.containers.provider import Labelable
from cfme.containers.provider import LoggingableView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.providers import get_crud_by_name
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import Accordion
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import Table
from widgetastic_manageiq import View


class ContainerView(ContainerObjectAllBaseView, LoggingableView):
    """The base view for header and nav checking"""

    @property
    def in_containers(self):
        """Determine if the Containers page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Containers', 'Containers']
        )


class ContainerAllView(ContainerView):
    """Containers All view"""
    SUMMARY_TEXT = "Containers"
    containers = Table(locator="//div[@id='list_grid']//table")

    @View.nested
    class Filters(Accordion):  # noqa
        ACCORDION_NAME = VersionPicker({
            LOWEST: "Filters",
            '5.11': "Global Filters"})

        @View.nested
        class Navigation(VerticalNavigation):
            DIV_LINKS_MATCHING = './/div/ul/li/a[contains(text(), {txt})]'

            def __init__(self, parent, logger=None):
                VerticalNavigation.__init__(self, parent, '#Container_def_searches', logger=logger)

        tree = ManageIQTree()

    @property
    def is_displayed(self):
        return self.in_containers and super().is_displayed


class ContainerDetailsView(ContainerObjectDetailsBaseView):
    """Containers Detail view"""
    SUMMARY_TEXT = "Containers"


@attr.s
class Container(BaseEntity, Taggable, Labelable):
    """Container Class"""
    PLURAL = 'Containers'
    all_view = ContainerAllView
    details_view = ContainerDetailsView

    name = attr.ib()
    pod = attr.ib()
    provider = attr.ib()

    @property
    def project_name(self):
        return self.pod.project_name


@attr.s
class ContainerCollection(GetRandomInstancesMixin, BaseCollection, TaggableCollection):
    """Collection object for :py:class:`Container`."""

    ENTITY = Container

    def all(self):
        # containers table has ems_id, join with ext_mgmgt_systems on id for provider name
        # Then join with container_groups on the id for the pod
        # TODO Update to use REST API instead of DB queries
        container_table = self.appliance.db.client['containers']
        ems_table = self.appliance.db.client['ext_management_systems']
        pod_table = self.appliance.db.client['container_groups']
        container_pod_id = getattr(container_table, 'container_group_id', None)
        container_query = (
            self.appliance.db.client.session
                .query(container_table.name, pod_table.name, ems_table.name)
                .join(ems_table, container_table.ems_id == ems_table.id)
                .join(pod_table, container_pod_id == pod_table.id))
        if self.filters.get('archived'):
            container_query = container_query.filter(container_table.deleted_on.isnot(None))
        if self.filters.get('active'):
            container_query = container_query.filter(container_table.deleted_on.is_(None))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            container_query = container_query.filter(ems_table.name == provider.name)
        containers = []
        for name, pod_name, ems_name in container_query.all():
            containers.append(
                self.instantiate(name=name, pod=pod_name,
                                 provider=provider or get_crud_by_name(ems_name)))

        return containers


@navigator.register(ContainerCollection, 'All')
class ContainerAll(CFMENavigateStep):
    VIEW = ContainerAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Containers')

    def resetter(self, *args, **kwargs):
        """Reset view and selection"""
        self.view.Filters.Navigation.select('ALL (Default)')
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Container, 'Details')
class ContainerDetails(CFMENavigateStep):
    VIEW = ContainerDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   pod_name=self.obj.pod,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Container, 'EditTags')
class ContainerEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(Container, 'Timelines')
class ContainerTimeLines(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')


@navigator.register(Container, 'Utilization')
class ContainerUtilization(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')
