# -*- coding: utf-8 -*-
import attr
import random
import itertools
from cached_property import cached_property

from wrapanapi.containers.pod import Pod as ApiPod

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic_manageiq import Text, TimelinesView, BreadCrumb

from cfme.common import WidgetasticTaggable, TagPageView
from cfme.containers.provider import (ContainersProvider, Labelable,
    ContainerObjectAllBaseView, LoggingableView, ContainerObjectDetailsBaseView)
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import (CFMENavigateStep, navigator,
                                                     navigate_to)

from cfme.common.vm_views import ManagePoliciesView

class PodView(ContainerObjectAllBaseView, LoggingableView):
    SUMMARY_TEXT = "Pods"

    @property
    def pods(self):
        return self.table

    @property
    def in_pod(self):
        """Determine if the Pods page is currently open"""
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ['Compute', 'Containers', 'Pods']
        )

class PodAllView(PodView):
    @property
    def is_displayed(self):
        return self.in_pod and super(PodAllView, self).is_displayed

@attr.s
class Pod(BaseEntity, WidgetasticTaggable, Labelable):
    """Pod Class"""
    PLURAL = 'Pods'
    all_view = PodAllView
    #details_view = PodDetailsView
    details_view = ContainerObjectDetailsBaseView

    name = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiPod(self.provider.mgmt, self.name, self.project_name)

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None):
        """Generating random instances."""
        pod_list = provider.mgmt.list_container_group()
        random.shuffle(pod_list)
        return [cls(obj.name, obj.project_name, provider, appliance=appliance)
                for obj in itertools.islice(pod_list, count)]

    @property
    def exists(self):
        """Return True if the Pod exists"""
        # TODO: move this to some ContainerObjectBase so it'll be shared among all objects
        try:
            navigate_to(self, 'Details')
        except NoSuchElementException:
            return False
        else:
            return True

@attr.s
class PodCollection(BaseCollection):
    """Collection object for :py:class:`Pod`."""

    ENTITY = Pod

    def all(self):
        # container_pods table has ems_id, join with ext_mgmgt_systems on id for provider name
        pod_table = self.appliance.db.client['container_pods']
        ems_table = self.appliance.db.client['ext_management_systems']
        pod_query= self.appliance.db.client.session.query(pod_table.name, ems_table.name)\
            .join(ems_table, pod_table.ems_id == ems_table.id)
        pods = []
        for name, provider_name in pod_query.all():
            # Hopefully we can get by with just provider name?
            pods.append(self.instantiate(
                name=name, provider=ContainersProvider(
                    name=provider_name, appliance=self.appliance)))
        return pods

# Still registering Pod to keep on consistency on container objects navigations
@navigator.register(Pod, 'All')
@navigator.register(PodCollection, 'All')
class All(CFMENavigateStep):
    VIEW = PodAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')


    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Pods')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.reset_selection()


@navigator.register(Pod, 'Details')
class Details(CFMENavigateStep):
    VIEW = ContainerObjectDetailsBaseView
    #VIEW = PodDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        self.prerequisite_view.entities.get_entity(name=self.obj.name,
                                                   provider=self.obj.provider.name).click()

@navigator.register(Pod, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')

@navigator.register(Pod, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = ManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        """Navigate to the Manage Policies page"""
        self.prerequisite_view.policy.item_select('Manage Policies')

class PodUtilizationView(PodView):
    """View for utilization of a pod"""
    title = Text('//div[@id="main-content"]//h1')

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_pod and
            self.title.text == '{} Capacity & Utilization'.format(self.context['object'].name)
        )

@navigator.register(Pod, 'Utilization')
class Utilization(CFMENavigateStep):
    VIEW = PodUtilizationView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        """Navigate to the Utilization page"""
        self.prerequisite_view.toolbar.monitoring.item_select('Utilization')

class PodTimelinesView(TimelinesView, PodView):
    """Timeline page for Pods"""
    breadcrumb = BreadCrumb()

    @property
    def is_displayed(self):
        """Is this page currently being displayed"""
        return (
            self.in_pod and
            '{} (Summary)'.format(self.context['object'].name) in self.breadcrumb.locations and
            self.is_timelines)

@navigator.register(Pod, 'Timelines')
class Timelines(CFMENavigateStep):
    VIEW = PodTimelinesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        """Navigate to the Timelines page"""
        self.prerequisite_view.toolbar.monitoring.item_select('Timelines')