import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling

from cfme.common import Taggable
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


class ServiceView(ContainerObjectAllBaseView, LoggingableView):
    """Container Nodes view"""

    @property
    def in_service(self):
        """Determine if the Service page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Containers', 'Container Services']
        )


class ServiceAllView(ServiceView):
    """Container Services All view"""
    SUMMARY_TEXT = "Container Services"

    @property
    def is_displayed(self):
        return self.in_service and super(ServiceAllView, self).is_displayed


class ServiceDetailsView(ContainerObjectDetailsBaseView):
    """Container Services Details view"""
    SUMMARY_TEXT = "Container Services"


@attr.s
class Service(BaseEntity, Taggable, Labelable):

    PLURAL = 'Container Services'
    all_view = ServiceAllView
    details_view = ServiceDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()


@attr.s
class ServiceCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Service`."""

    ENTITY = Service

    def all(self):
        # container_services table has ems_id, join with ext_mgmgt_systems on id for provider name
        # Then join with container_projects on the id for the project
        service_table = self.appliance.db.client['container_services']
        ems_table = self.appliance.db.client['ext_management_systems']
        project_table = self.appliance.db.client['container_projects']
        service_query = (
            self.appliance.db.client.session
                .query(service_table.name, project_table.name, ems_table.name)
                .join(ems_table, service_table.ems_id == ems_table.id)
                .join(project_table, service_table.container_project_id == project_table.id))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            service_query = service_query.filter(ems_table.name == provider.name)
        services = []
        for name, project_name, ems_name in service_query.all():
            services.append(self.instantiate(name=name, project_name=project_name,
                                             provider=provider or get_crud_by_name(ems_name)))

        return services


@navigator.register(ServiceCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ServiceAllView

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Services')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Service, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'All')
    VIEW = ServiceDetailsView

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Service, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
