# -*- coding: utf-8 -*-
import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import VersionPick, Version

from cfme.common import Taggable, TagPageView
from cfme.containers.provider import (Labelable, ContainerObjectAllBaseView,
    ContainerObjectDetailsBaseView, GetRandomInstancesMixin)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep
from cfme.utils.providers import get_crud_by_name


class ReplicatorAllView(ContainerObjectAllBaseView):
    """Container Replicators All view"""
    SUMMARY_TEXT = VersionPick({
        Version.lowest(): 'Replicators',
        '5.9': 'Container Replicators'
    })


class ReplicatorDetailsView(ContainerObjectDetailsBaseView):
    """Container Replicators Details view"""
    SUMMARY_TEXT = VersionPick({
        Version.lowest(): 'Replicators',
        '5.9': 'Container Replicators'
    })


@attr.s
class Replicator(BaseEntity, Taggable, Labelable):

    PLURAL = 'Replicators'
    all_view = ReplicatorAllView
    details_view = ReplicatorDetailsView

    name = attr.ib()
    project_name = attr.ib()
    provider = attr.ib()


@attr.s
class ReplicatorCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Replicator`."""

    ENTITY = Replicator

    def all(self):
        # container_replicators table has ems_id,
        # join with ext_mgmgt_systems on id for provider name
        # Then join with container_projects on the id for the project
        replicator_table = self.appliance.db.client['container_replicators']
        ems_table = self.appliance.db.client['ext_management_systems']
        project_table = self.appliance.db.client['container_projects']
        replicator_query = (
            self.appliance.db.client.session
                .query(replicator_table.name, project_table.name, ems_table.name)
                .join(ems_table, replicator_table.ems_id == ems_table.id)
                .join(project_table,
                      replicator_table.container_project_id == project_table.id))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            replicator_query = replicator_query.filter(ems_table.name == provider.name)
        replicators = []
        for name, project_name, ems_name in replicator_query.all():
            replicators.append(self.instantiate(name=name, project_name=project_name,
                                                provider=provider or get_crud_by_name(ems_name)))

        return replicators


@navigator.register(ReplicatorCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = ReplicatorAllView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Replicators')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Replicator, 'Details')
class Details(CFMENavigateStep):
    VIEW = ReplicatorDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   project_name=self.obj.project_name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible).click()


@navigator.register(Replicator, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
